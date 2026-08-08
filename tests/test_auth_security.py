import io
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

from config import Config
from pybo import create_app, db
from pybo.models import (
    BoardAttachment,
    ClassroomParticipant,
    DirectMessage,
    Friendship,
    Notification,
    User,
    UserSchool,
    VerificationChallenge,
)


class AuthSecurityIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_uri = Config.SQLALCHEMY_DATABASE_URI
        self.original_engine_options = Config.SQLALCHEMY_ENGINE_OPTIONS
        self.original_upload_folder = Config.UPLOAD_FOLDER
        Config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(Path(self.tempdir.name) / "test.db")
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        Config.UPLOAD_FOLDER = str(Path(self.tempdir.name) / "uploads")
        self.app = create_app()
        self.app.config.update(TESTING=True, AUTH_TEST_MODE=True)
        with self.app.app_context():
            db.create_all()
            user = User(username="tester", email="tester@example.com", password=generate_password_hash("old-password"))
            db.session.add(user)
            db.session.flush()
            user.school_name = "Test School"
            db.session.add(UserSchool(
                user_id=user.id,
                school_name="Test School",
                school_type="고등학교",
                school_year="2020",
                is_primary=True,
            ))
            db.session.commit()
            self.user_id = user.id
        self.client = self.app.test_client()
        html = self.client.get("/").get_data(as_text=True)
        self.csrf = re.search(r'name="csrf-token" content="([^"]+)', html).group(1)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        Config.SQLALCHEMY_DATABASE_URI = self.original_uri
        Config.SQLALCHEMY_ENGINE_OPTIONS = self.original_engine_options
        Config.UPLOAD_FOLDER = self.original_upload_folder
        self.tempdir.cleanup()

    def test_board_photo_is_saved_to_protected_media_route(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1
            session["active_board_school"] = "Test School"
        response = self.client.post(
            "/board/write",
            data={
                "title": "Photo post",
                "content": "Photo upload test",
                "file1": (io.BytesIO(b"\x89PNG\r\n\x1a\nrest"), "photo.png"),
            },
            headers={"X-CSRF-Token": self.csrf},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            attachment = BoardAttachment.query.one()
            self.assertTrue(attachment.file_url.startswith("/media/board_"))
            media_url = attachment.file_url
        media_response = self.client.get(media_url)
        self.assertEqual(media_response.status_code, 200)
        self.assertTrue(media_response.data.startswith(b"\x89PNG"))

    def test_school_posts_and_direct_messages_create_database_notifications(self):
        with self.app.app_context():
            recipient = User(
                username="recipient",
                email="recipient@example.com",
                password=generate_password_hash("password"),
            )
            recipient.school_name = "Test School"
            db.session.add(recipient)
            db.session.flush()
            db.session.add(UserSchool(
                user_id=recipient.id,
                school_name="Test School",
                school_type="high",
                school_year="2020",
                is_primary=True,
            ))
            db.session.add(Friendship(
                requester_id=self.user_id,
                receiver_id=recipient.id,
                status="accepted",
            ))
            db.session.commit()
            recipient_id = recipient.id

        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1
            session["active_board_school"] = "Test School"

        board_response = self.client.post(
            "/board/write",
            data={"title": "School update", "content": "New school post"},
            headers={"X-CSRF-Token": self.csrf},
        )
        message_response = self.client.post(
            "/api/social/messages",
            json={"receiver_id": recipient_id, "content": "Hello friend"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(board_response.status_code, 302)
        self.assertEqual(message_response.status_code, 201)

        with self.app.app_context():
            kinds = {
                item.kind
                for item in Notification.query.filter_by(user_id=recipient_id).all()
            }
        self.assertIn("new_post", kinds)
        self.assertIn("direct_message", kinds)

        # Simulate activity written before notification rows existed. The
        # polling endpoint must rebuild both sources directly from the DB.
        with self.app.app_context():
            Notification.query.filter_by(user_id=recipient_id).delete()
            db.session.commit()

        with self.client.session_transaction() as session:
            session["user_id"] = recipient_id
            session["session_version"] = 1
        notifications_response = self.client.get("/api/notifications")
        self.assertEqual(notifications_response.status_code, 200)
        self.assertIn("no-store", notifications_response.headers["Cache-Control"])
        self.assertEqual(notifications_response.get_json()["unread_count"], 2)

    def test_reset_code_is_hashed_server_side_and_absent_from_cookie(self):
        response = self.client.post(
            "/api/auth/forgot-password/check",
            json={"login_id": "tester@example.com"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 200)
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"])
        session_data = self.app.session_interface.get_signing_serializer(self.app).loads(cookie.value)
        self.assertNotIn("123456", repr(session_data))
        self.assertIn("verification_password_reset", session_data)
        with self.app.app_context():
            challenge = VerificationChallenge.query.one()
            self.assertNotIn("123456", challenge.code_hash)

    def test_password_reset_invalidates_existing_session_versions(self):
        self.client.post(
            "/api/auth/forgot-password/check",
            json={"login_id": "tester@example.com"},
            headers={"X-CSRF-Token": self.csrf},
        )
        response = self.client.post(
            "/api/auth/forgot-password/reset",
            json={"code": "123456", "new_password": "new-password"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.get(User, self.user_id).session_version, 2)

    def test_stale_login_session_is_rejected(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            user.session_version = 2
            db.session.commit()
        response = self.client.get("/api/my-schools")
        self.assertEqual(response.status_code, 401)

    def test_admin_quick_access_is_not_rendered_for_regular_users(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1

        self.app.config["EXECUTIVE_USER_IDS"] = []
        self.app.config["GMAIL_ADMIN_EMAIL"] = "admin@example.invalid"
        regular_html = self.client.get("/main-album").get_data(as_text=True)
        self.assertNotIn('id="adminQuickAccessButton"', regular_html)

        self.app.config["EXECUTIVE_USER_IDS"] = [self.user_id]
        admin_html = self.client.get("/main-album").get_data(as_text=True)
        self.assertIn('id="adminQuickAccessButton"', admin_html)

    def test_classroom_summon_requires_online_friend(self):
        with self.app.app_context():
            friend = User(
                username="offline-friend",
                email="offline-friend@example.com",
                password=generate_password_hash("password"),
            )
            db.session.add(friend)
            db.session.flush()
            db.session.add(Friendship(
                requester_id=self.user_id,
                receiver_id=friend.id,
                status="accepted",
            ))
            db.session.commit()
            friend_id = friend.id

        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1

        offline = self.client.post(
            "/api/social/classroom/invite",
            json={"target_id": friend_id},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(offline.status_code, 409)
        self.assertEqual(offline.get_json()["code"], "TARGET_OFFLINE")

        with self.app.app_context():
            db.session.get(User, friend_id).last_active_at = datetime.utcnow()
            db.session.commit()

        online = self.client.post(
            "/api/social/classroom/invite",
            json={"target_id": friend_id},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(online.status_code, 200)

    def test_monthly_sarangdal_is_added_once_to_existing_balance(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            user.sarangdal_balance = 10
            user.last_sarangdal_month = "2020-01"
            db.session.commit()
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1

        first = self.client.get("/api/sarangdal/status")
        second = self.client.get("/api/sarangdal/status")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["current_balance"], 11)
        self.assertEqual(second.get_json()["current_balance"], 11)
        self.assertTrue(second.get_json()["purchased_balance_carries_over"])

    def test_classroom_capacity_and_nonparticipant_access(self):
        with self.app.app_context():
            friends = []
            for index in range(8):
                friend = User(
                    username=f"friend-{index}",
                    email=f"friend-{index}@example.com",
                    password=generate_password_hash("password"),
                )
                db.session.add(friend)
                friends.append(friend)
            db.session.flush()
            for friend in friends:
                db.session.add(Friendship(
                    requester_id=self.user_id,
                    receiver_id=friend.id,
                    status="accepted",
                ))
            db.session.commit()
            friend_ids = [friend.id for friend in friends]

        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1
        start = self.client.post(
            "/api/social/classroom/start",
            json={"target_id": friend_ids[0]},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(start.status_code, 200)
        room_id = start.get_json()["room_id"]
        for friend_id in friend_ids[1:7]:
            response = self.client.post(
                f"/api/social/classroom/{room_id}/invite",
                json={"target_id": friend_id},
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(response.status_code, 200)
        full = self.client.post(
            f"/api/social/classroom/{room_id}/invite",
            json={"target_id": friend_ids[7]},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(full.status_code, 409)
        with self.app.app_context():
            self.assertEqual(
                ClassroomParticipant.query.filter_by(room_id=room_id).count(),
                8,
            )

        outsider = self.app.test_client()
        with outsider.session_transaction() as session:
            session["user_id"] = friend_ids[7]
            session["session_version"] = 1
        denied = outsider.get(f"/api/social/classroom/{room_id}/messages")
        self.assertEqual(denied.status_code, 403)

    def test_classroom_invitee_can_join_and_exchange_messages(self):
        with self.app.app_context():
            friend = User(
                username="classmate",
                email="classmate@example.com",
                password=generate_password_hash("password"),
            )
            db.session.add(friend)
            db.session.flush()
            db.session.add(Friendship(
                requester_id=self.user_id,
                receiver_id=friend.id,
                status="accepted",
            ))
            db.session.commit()
            friend_id = friend.id

        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1
        start = self.client.post(
            "/api/social/classroom/start",
            json={"target_id": friend_id},
            headers={"X-CSRF-Token": self.csrf},
        )
        room_id = start.get_json()["room_id"]

        friend_client = self.app.test_client()
        friend_html = friend_client.get("/").get_data(as_text=True)
        friend_csrf = re.search(
            r'name="csrf-token" content="([^"]+)', friend_html
        ).group(1)
        with friend_client.session_transaction() as session:
            session["user_id"] = friend_id
            session["session_version"] = 1
        joined = friend_client.post(
            f"/api/social/classroom/{room_id}/join",
            headers={"X-CSRF-Token": friend_csrf},
        )
        self.assertEqual(joined.status_code, 200)

        sent = friend_client.post(
            f"/api/social/classroom/{room_id}/messages",
            json={"content": "안녕하세요"},
            headers={"X-CSRF-Token": friend_csrf},
        )
        self.assertEqual(sent.status_code, 201)
        received = self.client.get(f"/api/social/classroom/{room_id}/messages")
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.get_json()["messages"][0]["content"], "안녕하세요")

    def test_admin_dashboard_broadcast_and_reply_flow(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["session_version"] = 1

        self.assertEqual(self.client.get("/admin/online-users").status_code, 403)
        self.app.config["GMAIL_ADMIN_EMAIL"] = "tester@example.com"

        with self.app.app_context():
            recipient = User(
                username="recipient",
                email="recipient@example.com",
                password=generate_password_hash("password"),
                last_active_at=datetime.utcnow(),
                last_login_at=datetime.utcnow(),
            )
            db.session.add(recipient)
            db.session.commit()
            recipient_id = recipient.id

        self.assertEqual(self.client.get("/admin/online-users").status_code, 200)
        online = self.client.get("/api/admin/online-users").get_json()
        self.assertTrue(online["success"])
        self.assertIn(
            "recipient@example.com",
            [user["email"] for user in online["users"]],
        )

        broadcast = self.client.post(
            "/api/admin/messages/broadcast",
            json={"content": "전체 공지 테스트"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(broadcast.status_code, 201)
        self.assertEqual(broadcast.get_json()["sent_count"], 1)
        with self.app.app_context():
            sent = DirectMessage.query.filter_by(
                sender_id=self.user_id,
                receiver_id=recipient_id,
            ).one()
            self.assertEqual(sent.content, "전체 공지 테스트")
            db.session.add(DirectMessage(
                sender_id=recipient_id,
                receiver_id=self.user_id,
                content="관리자님께 답변드립니다.",
            ))
            db.session.commit()

        replies = self.client.get("/api/admin/messages/replies").get_json()
        self.assertEqual(replies["messages"][0]["sender_id"], recipient_id)
        self.assertEqual(replies["unread_count"], 1)

        reply = self.client.post(
            "/api/admin/messages/reply",
            json={"receiver_id": recipient_id, "content": "답변 확인했습니다."},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(reply.status_code, 201)
        with self.app.app_context():
            self.assertIsNotNone(DirectMessage.query.filter_by(
                sender_id=self.user_id,
                receiver_id=recipient_id,
                content="답변 확인했습니다.",
            ).first())

    def test_verification_challenge_locks_after_five_failures(self):
        self.client.post(
            "/api/auth/forgot-password/check",
            json={"login_id": "tester@example.com"},
            headers={"X-CSRF-Token": self.csrf},
        )
        for _ in range(5):
            response = self.client.post(
                "/api/auth/forgot-password/reset",
                json={"code": "000000", "new_password": "new-password"},
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/auth/forgot-password/reset",
            json={"code": "123456", "new_password": "new-password"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
