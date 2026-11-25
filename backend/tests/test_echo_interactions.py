"""回声点赞、回复对象展示与点赞/收藏通知验证。"""
import unittest

from sqlalchemy import select

from app.models import Echo, EchoLike, Emotion, Notification, Ripple, Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class EchoInteractionTests(MySQLIntegrationTestCase):
    database_tag = "echointer"

    def setUp(self):
        with self.Session() as db:
            db.query(EchoLike).delete()
            db.query(Notification).delete()
            db.query(Echo).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.query(Topic).delete()
            db.query(Emotion).delete()
            db.add_all([
                User(id=i, username=f"user{i}", nickname=f"用户{i}", password_hash="unused")
                for i in range(1, 4)
            ])
            db.add(Topic(id=1, name="测试话题", slug="test"))
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=2, content="被点赞的微澜", topic_id=1),
                Ripple(id=2, user_id=1, content="已下架微澜", status="banned"),
            ])
            db.flush()
            db.add_all([
                Echo(id=1, root_ripple_id=1, user_id=2, content="第一条回声"),
                Echo(id=2, root_ripple_id=1, parent_echo_id=1, user_id=3, content="回复第一条"),
                Echo(id=3, root_ripple_id=2, user_id=1, content="下架内容里的回声"),
            ])
            db.commit()

    def set_echo_like(self, echo_id=1, actor=1, liked=True):
        method = "put" if liked else "delete"
        return getattr(self.client, method)(
            f"/api/v1/echoes/{echo_id}/like", headers=self.headers(actor)
        )

    def detail(self, ripple_id=1, actor=1):
        response = self.client.get(f"/api/v1/ripples/{ripple_id}", headers=self.headers(actor))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def notifications(self, user_id):
        response = self.client.get("/api/v1/notifications", headers=self.headers(user_id))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_echo_like_is_idempotent_and_scoped_to_user(self):
        first = self.set_echo_like(actor=1)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json(), {"echo_id": 1, "is_liked": True, "like_count": 1})
        again = self.set_echo_like(actor=1)
        self.assertEqual(again.json()["like_count"], 1)

        tree = self.detail(actor=1)["echoes"]
        self.assertTrue(tree[0]["is_liked"])
        self.assertEqual(tree[0]["like_count"], 1)
        other = self.detail(actor=2)["echoes"][0]
        self.assertFalse(other["is_liked"])
        self.assertEqual(other["like_count"], 1)

        removed = self.set_echo_like(actor=1, liked=False)
        self.assertEqual(removed.json(), {"echo_id": 1, "is_liked": False, "like_count": 0})
        self.assertEqual(self.set_echo_like(actor=1, liked=False).json()["like_count"], 0)

    def test_echo_like_requires_published_root_and_existing_echo(self):
        self.assertEqual(self.set_echo_like(echo_id=2, actor=1).status_code, 200)
        self.assertEqual(self.set_echo_like(echo_id=3, actor=1).status_code, 404)
        self.assertEqual(self.set_echo_like(echo_id=99999, actor=1).status_code, 404)

    def test_reply_target_is_exposed_on_create_and_tree(self):
        response = self.client.post(
            "/api/v1/ripples/1/echoes", json={"content": "再回一层", "parent_echo_id": 2},
            headers=self.headers(1),
        )
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        self.assertEqual(created["reply_to_user"]["id"], 3)
        self.assertEqual(created["reply_to_user"]["nickname"], "用户3")

        tree = self.detail()["echoes"]
        self.assertIsNone(tree[0]["reply_to_user"])
        self.assertEqual(tree[0]["children"][0]["reply_to_user"]["id"], 2)
        self.assertEqual(tree[0]["children"][0]["children"][0]["reply_to_user"]["id"], 3)

    def test_like_and_collection_notify_author_once(self):
        self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(1))
        notices = self.notifications(2)["items"]
        self.assertEqual([(n["kind"], n["ripple_id"]) for n in notices], [("like", 1)])
        self.assertEqual(notices[0]["actor_id"], 1)

        self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(1))
        self.assertEqual(len(self.notifications(2)["items"]), 1)

        self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(3))
        self.assertEqual(len(self.notifications(2)["items"]), 2)

        self.client.delete("/api/v1/interactions/ripples/1/like", headers=self.headers(1))
        notices = self.notifications(2)["items"]
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["actor_id"], 3)

        self.client.put("/api/v1/interactions/ripples/1/collection", headers=self.headers(1))
        kinds = [n["kind"] for n in self.notifications(2)["items"]]
        self.assertIn("collection", kinds)
        self.client.delete("/api/v1/interactions/ripples/1/collection", headers=self.headers(1))
        self.assertNotIn("collection", [n["kind"] for n in self.notifications(2)["items"]])

    def test_self_interaction_creates_no_notification(self):
        self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(2))
        self.client.put("/api/v1/interactions/ripples/1/collection", headers=self.headers(2))
        self.assertEqual(self.notifications(2)["items"], [])

    def test_like_notification_hidden_when_ripple_unpublished(self):
        self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(1))
        self.assertEqual(self.notifications(2)["items"][0]["kind"], "like")
        with self.Session() as db:
            db.execute(Ripple.__table__.update().where(Ripple.id == 1).values(status="banned"))
            db.commit()
        self.assertEqual(self.notifications(2)["items"], [])
        self.assertEqual(self.notifications(2)["unread_count"], 0)

    def test_like_notice_survives_actor_like_count(self):
        """通知按操作人去重，不因同一用户重复点击而增长。"""
        for _ in range(3):
            self.client.put("/api/v1/interactions/ripples/1/like", headers=self.headers(1))
        with self.Session() as db:
            rows = db.scalars(select(Notification).where(Notification.kind == "like")).all()
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
