"""回声发表、回复树、删除权限、并发和聚合统计验证。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import unittest

from sqlalchemy import func, select

from app.models import Echo, Emotion, Ripple, Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class EchoTests(MySQLIntegrationTestCase):
    database_tag = "echoes"

    def setUp(self):
        with self.Session() as db:
            db.query(Echo).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.query(Topic).delete()
            db.query(Emotion).delete()
            db.add_all([
                User(id=i, username=f"user{i}", nickname=f"用户{i}", password_hash="unused",
                     role="admin" if i == 3 else "user", ban_status="banned" if i == 4 else "active")
                for i in range(1, 5)
            ])
            db.add(Topic(id=1, name="测试话题", slug="test"))
            db.add(Emotion(code="calm", name="平静", color="#78909c"))
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=2, content="公开内容", topic_id=1, emotion_code="calm"),
                Ripple(id=2, user_id=1, content="下架", status="banned", topic_id=1, emotion_code="calm"),
                Ripple(id=3, user_id=1, content="待审核", status="pending", topic_id=1, emotion_code="calm"),
                Ripple(id=4, user_id=2, content="另一条公开内容"),
            ])
            db.flush()
            db.add(Echo(id=1, root_ripple_id=1, user_id=2, content="第一层", created_at=datetime(2026, 1, 1)))
            db.flush()
            db.add_all([
                Echo(id=2, root_ripple_id=1, parent_echo_id=1, user_id=1, content="第二层", created_at=datetime(2026, 1, 1)),
                Echo(id=3, root_ripple_id=4, user_id=2, content="别处的回声"),
                Echo(id=4, root_ripple_id=2, user_id=1, content="隐藏内容中的回声"),
            ])
            db.commit()

    def post(self, content="新的回声", ripple_id=1, actor=1, **extra):
        return self.client.post(
            f"/api/v1/ripples/{ripple_id}/echoes", json={"content": content, **extra},
            headers=self.headers(actor),
        )

    def detail(self, ripple_id=1, actor=1):
        response = self.client.get(f"/api/v1/ripples/{ripple_id}", headers=self.headers(actor))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_publish_trim_emotion_persistence_and_counts(self):
        response = self.post(content="  回声内容  ", emotion_code="calm")
        self.assertEqual(response.status_code, 201, response.text)
        echo = response.json()
        self.assertEqual(echo["content"], "回声内容")
        self.assertEqual(echo["emotion"]["code"], "calm")
        self.assertEqual(echo["children"], [])
        detail = self.detail()
        self.assertEqual(detail["ripple"]["echo_count"], 3)
        self.assertIn(echo["id"], [item["id"] for item in detail["echoes"]])

    def test_reply_tree_keeps_parent_order_and_user(self):
        response = self.post(parent_echo_id=2)
        self.assertEqual(response.status_code, 201, response.text)
        tree = self.detail()["echoes"]
        self.assertEqual(tree[0]["id"], 1)
        self.assertEqual(tree[0]["children"][0]["id"], 2)
        child = tree[0]["children"][0]["children"][0]
        self.assertEqual(child["id"], response.json()["id"])
        self.assertEqual(child["parent_echo_id"], 2)
        self.assertEqual(child["user"]["id"], 1)

    def test_cannot_reply_across_ripples_or_to_missing_parent(self):
        for parent_id in (3, 99999):
            self.assertEqual(self.post(parent_echo_id=parent_id).status_code, 404)
        self.assertEqual(self.detail()["ripple"]["echo_count"], 2)

    def test_content_parent_and_emotion_validation(self):
        for content in ("", "  \n\t", "字" * 201):
            self.assertEqual(self.post(content=content).status_code, 422)
        self.assertEqual(self.post(parent_echo_id=0).status_code, 422)
        self.assertEqual(self.post(emotion_code="missing").status_code, 400)

    def test_login_bans_visibility_and_invalid_ids(self):
        self.assertEqual(self.client.post("/api/v1/ripples/1/echoes", json={"content": "x"}).status_code, 401)
        self.assertEqual(self.post(actor=4).status_code, 403)
        for ripple_id in (2, 3, 99999):
            self.assertEqual(self.post(ripple_id=ripple_id).status_code, 404)
        self.assertEqual(self.post(ripple_id=0).status_code, 422)

    def test_depth_limit_is_clear_and_tree_remains_readable(self):
        parent = 2
        for level in range(3, 9):
            response = self.post(content=f"第{level}层", parent_echo_id=parent)
            self.assertEqual(response.status_code, 201, response.text)
            parent = response.json()["id"]
        response = self.post(parent_echo_id=parent)
        self.assertEqual(response.status_code, 400)
        self.assertIn("8", response.json()["detail"])
        self.assertEqual(self.detail()["ripple"]["echo_count"], 8)

    def test_author_can_delete_own_echo_but_not_others(self):
        denied = self.client.delete("/api/v1/echoes/1", headers=self.headers())
        self.assertEqual(denied.status_code, 403)
        response = self.client.delete("/api/v1/echoes/2", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["echo_count"], 1)
        self.assertEqual(self.detail()["echoes"][0]["children"], [])

    def test_admin_delete_cascades_subtree(self):
        response = self.client.delete("/api/v1/echoes/1", headers=self.headers(3))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"ripple_id": 1, "echo_count": 0})
        self.assertEqual(self.detail()["echoes"], [])
        with self.Session() as db:
            self.assertIsNone(db.get(Echo, 2))
            self.assertIsNotNone(db.get(Echo, 3))

    def test_delete_requires_login_and_valid_existing_node(self):
        self.assertEqual(self.client.delete("/api/v1/echoes/2").status_code, 401)
        self.assertEqual(self.client.delete("/api/v1/echoes/2", headers=self.headers(4)).status_code, 403)
        self.assertEqual(self.client.delete("/api/v1/echoes/9999", headers=self.headers()).status_code, 404)
        self.assertEqual(self.client.delete("/api/v1/echoes/0", headers=self.headers()).status_code, 422)

    def test_concurrent_posts_keep_tree_and_counts_consistent(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            responses = list(pool.map(lambda i: self.post(content=f"并发回声{i}", parent_echo_id=1), range(6)))
        self.assertTrue(all(response.status_code == 201 for response in responses))
        detail = self.detail()
        self.assertEqual(detail["ripple"]["echo_count"], 8)
        self.assertEqual(len(detail["echoes"][0]["children"]), 7)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Echo.id)).where(Echo.root_ripple_id == 1)), 8)

    def test_heat_and_mood_use_only_public_content_and_refresh_after_echo(self):
        tides = self.client.get("/api/v1/tides/hot").json()
        self.assertEqual((tides[0]["ripple_count"], tides[0]["echo_count"]), (1, 2))
        before = tides[0]["heat"]
        self.post()
        self.assertEqual(self.client.get("/api/v1/tides/hot").json()[0]["heat"], before + 5)
        moods = self.client.get("/api/v1/moods/summary").json()
        self.assertEqual((moods[0]["count"], moods[0]["percent"]), (1, 100.0))


if __name__ == "__main__":
    unittest.main()
