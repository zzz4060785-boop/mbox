import io
import unittest

from flask import Flask, session

from pybo.security import init_security
from pybo.uploads import has_valid_image_signature, has_valid_media_signature
from pybo.crypto import decrypt_secret, encrypt_secret


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="test-only-secret")
        init_security(self.app)

        @self.app.get("/")
        def index():
            from pybo.security import csrf_token
            return csrf_token()

        @self.app.post("/api/change")
        def change():
            return {"success": True}

        self.client = self.app.test_client()

    def test_unsafe_request_without_token_is_rejected(self):
        response = self.client.post("/api/change", json={})
        self.assertEqual(response.status_code, 400)

    def test_unsafe_request_with_token_is_allowed(self):
        token = self.client.get("/").get_data(as_text=True)
        response = self.client.post("/api/change", json={}, headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 200)

    def test_security_headers_are_present(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn(
            "script-src 'self' https://cdn.iamport.kr https://cdn.portone.io 'nonce-",
            csp,
        )
        self.assertIn("script-src-attr 'none'", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)


class UploadTests(unittest.TestCase):
    def test_png_signature(self):
        uploaded = type("Upload", (), {"stream": io.BytesIO(b"\x89PNG\r\n\x1a\nrest")})()
        self.assertTrue(has_valid_image_signature(uploaded, "png"))

    def test_spoofed_png_is_rejected(self):
        uploaded = type("Upload", (), {"stream": io.BytesIO(b"not an image")})()
        self.assertFalse(has_valid_image_signature(uploaded, "png"))

    def test_mp4_signature(self):
        uploaded = type("Upload", (), {"stream": io.BytesIO(b"\x00\x00\x00\x18ftypisom")})()
        self.assertTrue(has_valid_media_signature(uploaded, "mp4"))

    def test_spoofed_audio_is_rejected(self):
        uploaded = type("Upload", (), {"stream": io.BytesIO(b"not really an mp3")})()
        self.assertFalse(has_valid_media_signature(uploaded, "mp3"))


class CryptoTests(unittest.TestCase):
    def test_database_secret_round_trip(self):
        config = {"TOKEN_ENCRYPTION_KEY": "unit-test-key-with-enough-entropy", "SECRET_KEY": "unused"}
        encrypted = encrypt_secret(config, "refresh-token")
        self.assertNotIn("refresh-token", encrypted)
        self.assertEqual(decrypt_secret(config, encrypted), "refresh-token")

    def test_plaintext_credential_remains_readable_for_migration(self):
        config = {"TOKEN_ENCRYPTION_KEY": "unit-test-key", "SECRET_KEY": "unused"}
        self.assertEqual(decrypt_secret(config, "legacy-token"), "legacy-token")

    def test_old_secret_remains_readable_after_dedicated_key_is_added(self):
        old = {"TOKEN_ENCRYPTION_KEY": "", "SECRET_KEY": "old-application-secret"}
        encrypted = encrypt_secret(old, "refresh-token")
        rotated = {"TOKEN_ENCRYPTION_KEY": "new-token-key", "SECRET_KEY": "old-application-secret"}
        self.assertEqual(decrypt_secret(rotated, encrypted), "refresh-token")


if __name__ == "__main__":
    unittest.main()
