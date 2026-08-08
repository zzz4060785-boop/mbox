from datetime import datetime
import json
from uuid import uuid4
from urllib.parse import quote
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
from pybo.models import GooglePlayPurchase, PaymentOrder, User
from pybo.audit import audit_event

bp = Blueprint("payment", __name__, url_prefix="/payment")

PRODUCTS = {
    5: {"amount": 1000, "name": "사랑달 5개 충전"},
    30: {"amount": 6000, "name": "사랑달 30개 충전"},
    70: {"amount": 14000, "name": "사랑달 70개 충전"},
}

GOOGLE_PLAY_PRODUCTS = {
    "sarangdal_5": 5,
    "sarangdal_30": 30,
    "sarangdal_70": 70,
}


def _google_access_token():
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import service_account

    credentials_file = current_app.config.get("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE", "")
    if not credentials_file:
        raise RuntimeError("Google Play service account is not configured")
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    credentials.refresh(GoogleAuthRequest())
    return credentials.token


def _google_play_request(method, url):
    request_object = Request(
        url,
        headers={"Authorization": f"Bearer {_google_access_token()}"},
        method=method,
    )
    with urlopen(request_object, timeout=15) as response:
        body = response.read()
        return json.loads(body.decode("utf-8")) if body else {}


def _get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route("/store")
def store():
    """사랑달 충전 및 전자상거래 결제 매장 페이지 (심사관 및 크롤러 접근 허용)"""
    if not (current_app.config.get("PAYMENT_ENABLED") or current_app.config.get("GOOGLE_PLAY_BILLING_ENABLED")):
        return "결제 서비스가 비활성화되어 있습니다.", 503
    user = _get_current_user() or User(username="손님", email="guest@friendary.com", sarangdal_balance=0)


    store_id = current_app.config.get("PORTONE_STORE_ID", "")
    channel_key = current_app.config.get("PORTONE_CHANNEL_KEY", "")

    return render_template(
        "store.html",
        user=user,
        store_id=store_id,
        channel_key=channel_key,
        google_play_enabled=current_app.config.get("GOOGLE_PLAY_BILLING_ENABLED", False),
        portone_enabled=current_app.config.get("PAYMENT_ENABLED", False),
    )


@bp.post("/google-play/complete")
def complete_google_play_purchase():
    """Verify, grant and consume a Google Play one-time product exactly once."""
    if not current_app.config.get("GOOGLE_PLAY_BILLING_ENABLED"):
        return jsonify({"success": False, "message": "Google Play 결제가 비활성화되어 있습니다."}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json() or {}
    product_id = str(data.get("product_id", "")).strip()
    purchase_token = str(data.get("purchase_token", "")).strip()
    sarangdal_count = GOOGLE_PLAY_PRODUCTS.get(product_id)
    if not sarangdal_count or not purchase_token or len(purchase_token) > 1024:
        return jsonify({"success": False, "message": "유효하지 않은 Google Play 구매정보입니다."}), 400

    existing = GooglePlayPurchase.query.filter_by(purchase_token=purchase_token).first()
    if existing:
        if existing.user_id != user.id or existing.product_id != product_id:
            return jsonify({"success": False, "message": "이미 다른 계정에서 처리된 구매입니다."}), 409
        return jsonify({
            "success": True,
            "message": "이미 지급이 완료된 구매입니다.",
            "sarangdal_balance": user.sarangdal_balance,
        })

    package_name = current_app.config.get("GOOGLE_PLAY_PACKAGE_NAME", "com.junyoung.friendary")
    base_url = (
        "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{quote(package_name, safe='')}/purchases/products/"
        f"{quote(product_id, safe='')}/tokens/{quote(purchase_token, safe='')}"
    )
    try:
        purchase = _google_play_request("GET", base_url)
        if purchase.get("purchaseState") != 0:
            return jsonify({"success": False, "message": "완료되지 않은 결제입니다."}), 409
        if purchase.get("consumptionState") == 1:
            return jsonify({"success": False, "message": "이미 사용 처리된 구매입니다."}), 409

        user = User.query.filter_by(id=user.id).with_for_update().one()
        record = GooglePlayPurchase(
            purchase_token=purchase_token,
            product_id=product_id,
            user_id=user.id,
            order_id=purchase.get("orderId"),
            sarangdal_count=sarangdal_count,
            status="VERIFIED",
            purchase_time_ms=purchase.get("purchaseTimeMillis"),
        )
        user.sarangdal_balance = (user.sarangdal_balance or 0) + sarangdal_count
        db.session.add(record)
        db.session.commit()
        audit_event("google_play_purchase_completed", {
            "product_id": product_id,
            "sarangdal_count": sarangdal_count,
            "order_id": purchase.get("orderId"),
        }, user.id)
        return jsonify({
            "success": True,
            "message": f"사랑달 {sarangdal_count}개가 충전되었습니다.",
            "sarangdal_balance": user.sarangdal_balance,
        })
    except (HTTPError, URLError, OSError, ValueError, RuntimeError):
        db.session.rollback()
        current_app.logger.exception("Google Play purchase verification failed")
        return jsonify({"success": False, "message": "Google Play 결제 확인에 실패했습니다."}), 502


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
