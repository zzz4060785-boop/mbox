from datetime import datetime
import json
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from pybo import db
from pybo.models import PaymentOrder, User
from pybo.audit import audit_event

bp = Blueprint("payment", __name__, url_prefix="/payment")

PRODUCTS = {
    5: {"amount": 1000, "name": "사랑달 5개 충전"},
    30: {"amount": 5000, "name": "사랑달 30개 충전"},
    70: {"amount": 10000, "name": "사랑달 70개 충전"},
}


def _get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route("/store")
def store():
    """사랑달 충전 및 전자상거래 결제 매장 페이지 (심사관 및 크롤러 접근 허용)"""
    if not current_app.config.get("PAYMENT_ENABLED"):
        return "결제 서비스가 비활성화되어 있습니다.", 503
    user = _get_current_user() or User(username="손님", email="guest@friendary.com", sarangdal_balance=0)


    store_id = current_app.config.get("PORTONE_STORE_ID", "")
    channel_key = current_app.config.get("PORTONE_CHANNEL_KEY", "")

    return render_template(
        "store.html",
        user=user,
        store_id=store_id,
        channel_key=channel_key,
    )


@bp.route("/prepare", methods=["POST"])
def prepare_payment():
    """결제 요청 전 DB에 사전 주문(READY) 생성"""
    if not current_app.config.get("PAYMENT_ENABLED"):
        return jsonify({"success": False, "message": "결제 서비스가 비활성화되어 있습니다."}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json() or {}
    try:
        sarangdal_count = int(data.get("sarangdal_count", 0))
    except (ValueError, TypeError):
        sarangdal_count = 0

    product = PRODUCTS.get(sarangdal_count)
    if not product:
        return jsonify({"success": False, "message": "유효하지 않은 상품입니다."}), 400
    amount = product["amount"]
    order_name = product["name"]

    # 고유 주문 결제 ID 생성
    payment_id = f"pay-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

    order = PaymentOrder(
        payment_id=payment_id,
        user_id=user.id,
        order_name=order_name,
        amount=amount,
        sarangdal_count=sarangdal_count,
        status="READY",
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        "success": True,
        "payment_id": payment_id,
        "order_name": order_name,
        "amount": amount,
        "store_id": current_app.config.get("PORTONE_STORE_ID"),
    })


@bp.route("/complete", methods=["POST"])
def complete_payment():
    """결제 완료 후 포트원 V2 REST API로 결제 무변조 검증"""
    if not current_app.config.get("PAYMENT_ENABLED"):
        return jsonify({"success": False, "message": "결제 서비스가 비활성화되어 있습니다."}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json() or {}
    payment_id = data.get("payment_id")

    if not payment_id:
        return jsonify({"success": False, "message": "결제 ID가 누락되었습니다."}), 400

    api_secret = current_app.config.get("PORTONE_API_SECRET", "")
    if not api_secret:
        return jsonify({"success": False, "message": "결제 검증 설정이 완료되지 않았습니다."}), 503

    # Serialize completion for this order. Concurrent callbacks cannot both credit it.
    order = PaymentOrder.query.filter_by(
        payment_id=payment_id, user_id=user.id
    ).with_for_update().first()
    if not order:
        return jsonify({"success": False, "message": "해당 주문을 찾을 수 없습니다."}), 404

    if order.status == "PAID":
        return jsonify({
            "success": True,
            "message": "이미 처리된 결제입니다.",
            "sarangdal_balance": user.sarangdal_balance,
        })
    if order.status != "READY":
        return jsonify({"success": False, "message": "처리할 수 없는 주문 상태입니다."}), 409

    # 포트원 V2 REST API 단건 결제 조회 (무변조 검증)
    url = f"https://api.portone.io/payments/{payment_id}"
    req = Request(
        url,
        headers={
            "Authorization": f"PortOne {api_secret}",
            "Content-Type": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))

        status = res_data.get("status")
        total_amount = res_data.get("amount", {}).get("total")
        tx_id = res_data.get("id") or res_data.get("transactionId")

        # 결제 상태 및 금액 일치 검증
        if status == "PAID" and total_amount == order.amount:
            # Lock the balance row in the same transaction as the order transition.
            user = User.query.filter_by(id=user.id).with_for_update().one()
            order.status = "PAID"
            order.paid_at = datetime.utcnow()
            order.tx_id = tx_id
            order.pay_method = res_data.get("method", {}).get("type", "UNKNOWN")

            # 사랑달 포인트 충전 반영
            if order.sarangdal_count > 0:
                user.sarangdal_balance = (user.sarangdal_balance or 0) + order.sarangdal_count

            db.session.commit()
            audit_event("payment_completed", {"payment_id": payment_id, "amount": order.amount}, user.id)
            return jsonify({
                "success": True,
                "message": f"결제가 성사되었습니다! ({order.order_name})",
                "sarangdal_balance": user.sarangdal_balance,
            })
        else:
            order.status = "FAILED"
            db.session.commit()
            return jsonify({
                "success": False,
                "message": f"결제 검증 실패 (상태: {status}, 금액: {total_amount}원)",
            }), 400

    except Exception as e:
        current_app.logger.warning(f"PortOne API verification note: {e}")
        audit_event("payment_verification_failed", {"payment_id": payment_id}, user.id)

        return jsonify({
            "success": False,
            "message": "결제 확인에 실패했습니다. 잠시 후 다시 확인해 주세요.",
        }), 502
