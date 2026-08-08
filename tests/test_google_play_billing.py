import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from config import Config
from pybo import create_app, db
from pybo.models import GooglePlayPurchase, User


class GooglePlayBillingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_uri = Config.SQLALCHEMY_DATABASE_URI
        self.original_options = Config.SQLALCHEMY_ENGINE_OPTIONS
        Config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(Path(self.tempdir.name) / "billing.db")
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        self.app = create_app()
        self.app.config.update(TESTING=True, GOOGLE_PLAY_BILLING_ENABLED=True)
        with self.app.app_context():
            db.create_all()
            user = User(
                username="billing-user",
                email="billing@example.com",
                password=generate_password_hash("password"),
                sarangdal_balance=2,
            )
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
        self.client = self.app.test_client()
        html = self.client.get("/").get_data(as_text=True)
        self.csrf = re.search(r'name="csrf-token" content="([^"]+)', html).group(1)
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user_id
            browser_session["session_version"] = 1

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        Config.SQLALCHEMY_DATABASE_URI = self.original_uri
        Config.SQLALCHEMY_ENGINE_OPTIONS = self.original_options
        self.tempdir.cleanup()

    @patch("pybo.views.payment_views._google_play_request")
    def test_verified_purchase_is_credited_exactly_once(self, play_request):
        play_request.return_value = {
            "purchaseState": 0,
            "consumptionState": 0,
            "orderId": "GPA.test-order",
            "purchaseTimeMillis": "1786190400000",
        }
        payload = {"product_id": "sarangdal_30", "purchase_token": "unique-token"}
        headers = {"X-CSRF-Token": self.csrf}

        first = self.client.post("/payment/google-play/complete", json=payload, headers=headers)
        second = self.client.post("/payment/google-play/complete", json=payload, headers=headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.get(User, self.user_id).sarangdal_balance, 32)
            self.assertEqual(GooglePlayPurchase.query.count(), 1)
        self.assertEqual(play_request.call_count, 1)

    def test_unknown_product_is_rejected(self):
        response = self.client.post(
            "/payment/google-play/complete",
            json={"product_id": "fake_product", "purchase_token": "token"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
