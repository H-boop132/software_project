"""提醒的归属、可见范围和生命周期。"""
from app.models import Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class NotificationTests(MySQLIntegrationTestCase):
    database_tag = "notifications"
    path = "/api/v1/notifications"

    def setUp(self):
        with self.Session() as db:
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=i, username=f"user{i}", nickname=f"用户{i}", password_hash="unused")
                for i in range(1, 4)
            ])
            db.flush()
            db.add(Ripple(id=1, user_id=1, content="原帖", status="published"))
            db.commit()

    def inbox(self, user, **params):
        response = self.client.get(self.path, params=params, headers=self.headers(user))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def post_echo(self, user, parent=None):
        response = self.client.post(
            "/api/v1/ripples/1/echoes", headers=self.headers(user),
            json={"content": "测试回复", "parent_echo_id": parent},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def test_reply_notifies_immediate_parent_and_skips_self(self):
        echo_id = self.post_echo(2)
        reply_id = self.post_echo(3, echo_id)
        self.post_echo(2, echo_id)
        self.post_echo(1)
        self.assertEqual(self.inbox(1)["unread_count"], 1)
        reply = self.inbox(2, kind="reply")["items"][0]
        self.assertEqual((reply["kind"], reply["actor_id"], reply["echo_id"], reply["ripple_id"]),
                         ("reply", 3, reply_id, 1))
        self.assertEqual(reply["preview"], "测试回复")
        self.assertEqual(self.inbox(3)["items"], [])

    def test_repeated_follow_and_unfollow_do_not_leave_duplicate_notifications(self):
        path = "/api/v1/users/1/follow"
        for _ in range(2):
            response = self.client.put(path, headers=self.headers(2))
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.inbox(1, kind="follow")["unread_count"], 1)
        self.client.delete(path, headers=self.headers(2))
        self.assertEqual(self.inbox(1)["items"], [])

    def test_read_operations_are_private_and_cursor_keeps_order(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.post_echo(2)
        self.post_echo(3)
        first = self.inbox(1, limit=1)
        earlier = self.inbox(1, limit=1, before=first["next_before"])
        self.assertEqual(earlier["items"][0]["actor_id"], 2)
        mark = f"{self.path}/{first['items'][0]['id']}/read"
        self.assertEqual(self.client.put(mark, headers=self.headers(2)).status_code, 404)
        for _ in range(2):
            result = self.client.put(mark, headers=self.headers(1))
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["unread_count"], 1)
        result = self.client.put(f"{self.path}/read-all", headers=self.headers(1))
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["unread_count"], 0)
        self.assertEqual(len(self.inbox(1)["items"]), 2)
        self.assertEqual(self.inbox(1, unread_only=True)["items"], [])

    def test_hidden_or_deleted_content_stops_appearing_in_messages(self):
        echo_id = self.post_echo(2)
        with self.Session() as db:
            db.get(Ripple, 1).status = "banned"
            db.commit()
        self.assertEqual(self.inbox(1)["unread_count"], 0)
        self.assertEqual(self.inbox(1)["items"], [])
        with self.Session() as db:
            db.get(Ripple, 1).status = "published"
            db.commit()
        self.assertEqual(self.inbox(1)["unread_count"], 1)
        result = self.client.delete(f"/api/v1/echoes/{echo_id}", headers=self.headers(2))
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.inbox(1)["unread_count"], 0)
