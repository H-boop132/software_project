"""作者管理、审核状态与内容删除的集成测试。"""
from datetime import datetime

from app.models import Emotion, Ripple, RippleReview, Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class AuthorRippleTests(MySQLIntegrationTestCase):
    database_tag = "authors"
    post = "/api/v1/ripples/1"
    mine = "/api/v1/ripples/mine"
    moderation = "/api/v1/admin/ripples/1"

    def setUp(self):
        with self.Session() as db:
            db.query(Ripple).delete()
            db.query(User).delete()
            db.query(Topic).delete()
            db.query(Emotion).delete()
            db.add_all([
                User(id=1, username="author", nickname="作者", password_hash="unused"),
                User(id=2, username="reader", nickname="读者", password_hash="unused"),
                User(id=3, username="admin", nickname="管理员", password_hash="unused", role="admin"),
                Topic(id=1, name="话题", slug="topic"),
                Emotion(code="calm", name="平静", color="#000000"),
            ])
            db.flush()
            db.add_all([
                Ripple(
                    id=1, user_id=1, content="旧的想法", topic_id=1, emotion_code="calm",
                    images=["/uploads/fixture.png"], created_at=datetime(2025, 7, 1),
                ),
                Ripple(id=2, user_id=1, content="另一条想法"),
                Ripple(id=3, user_id=2, content="别人的想法"),
            ])
            db.commit()

    def test_author_edit_preserves_metadata_timestamp_and_interactions(self):
        self.assertEqual(self.client.put(self.post, headers=self.headers(2), json={"content": "无权修改"}).status_code, 403)
        self.client.post(f"{self.post}/echoes", headers=self.headers(2), json={"content": "我的回应"})
        invalid = self.client.put(self.post, headers=self.headers(1), json={"content": " "})
        self.assertEqual(invalid.status_code, 422)
        result = self.client.put(self.post, headers=self.headers(1), json={
            "content": " 新的想法 ", "expected_status": "published",
        })
        self.assertEqual(result.status_code, 200, result.text)
        item = result.json()
        self.assertEqual((item["id"], item["content"], item["status"], item["echo_count"]), (1, "新的想法", "published", 1))
        self.assertEqual(item["created_at"], "2025-07-01T00:00:00")
        self.assertEqual((item["topic"]["id"], item["emotion"]["code"], item["images"]), (1, "calm", ["/uploads/fixture.png"]))
        public = self.client.get(self.post).json()
        self.assertEqual(public["ripple"]["content"], "新的想法")
        self.assertEqual(len(public["echoes"]), 1)

    def test_mine_filters_and_exposes_latest_review_to_owner(self):
        admin = self.headers(3)
        author = self.headers(1)
        self.assertEqual(self.client.post(f"{self.moderation}/ban", headers=admin, json={"reason": "原创说明不清晰"}).status_code, 200)
        conflict = self.client.put(self.post, headers=author, json={"content": "尝试修改", "expected_status": "published"})
        self.assertEqual(conflict.status_code, 409)
        banned = self.client.get(self.mine, headers=author, params={"status": "banned", "keyword": "旧"}).json()
        self.assertEqual([(r["id"], r["latest_review"]["reason"]) for r in banned], [(1, "原创说明不清晰")])
        self.assertNotIn("reviewer_id", banned[0]["latest_review"])
        other = self.client.get(self.mine, headers=self.headers(2), params={"status": "banned"}).json()
        self.assertEqual(other, [])
        pending = self.client.put(self.post, headers=author, json={"content": "已补充原创说明"})
        self.assertEqual(pending.json()["status"], "pending")
        self.assertEqual(self.client.get(self.post).status_code, 404)
        self.assertEqual(self.client.put(self.post, headers=author, json={"content": "等待审核"}).status_code, 400)
        self.assertEqual(self.client.post(f"{self.moderation}/reject", headers=admin, json={"reason": "还需补充来源"}).status_code, 200)
        latest = self.client.get(self.mine, headers=author, params={"status": "banned"}).json()[0]["latest_review"]
        self.assertEqual((latest["action"], latest["reason"]), ("reject", "还需补充来源"))

    def test_delete_hides_discussion_but_keeps_review_history(self):
        admin = self.headers(3)
        author = self.headers(1)
        reader = self.headers(2)
        echo = self.client.post(f"{self.post}/echoes", headers=reader, json={"content": "讨论"}).json()
        self.assertEqual(self.client.delete(self.post, headers=reader).status_code, 403)
        self.client.post(f"{self.moderation}/ban", headers=admin, json={"reason": "审核记录"})
        self.client.put(self.post, headers=author, json={"content": "申请复审"})
        for _ in range(2):
            self.assertEqual(self.client.delete(self.post, headers=author).status_code, 204)
        self.assertEqual(self.client.get(self.post, headers=author).status_code, 404)
        self.assertEqual(self.client.get(self.post, headers=reader).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/echoes/{echo['id']}", headers=reader).status_code, 404)
        self.assertEqual(self.client.post(f"{self.moderation}/approve", headers=admin).status_code, 404)
        self.assertEqual([item["id"] for item in self.client.get(self.mine, headers=author).json()], [2])
        self.assertEqual(self.client.get("/api/v1/notifications", headers=author).json()["items"], [])
        with self.Session() as db:
            self.assertEqual(db.get(Ripple, 1).status, "deleted")
            self.assertEqual(db.query(RippleReview).filter_by(ripple_id=1).count(), 1)

    def test_moderation_handles_posts_without_images(self):
        admin = self.headers(3)
        author = self.headers(1)
        post = "/api/v1/ripples/2"
        action = "/api/v1/admin/ripples/2"
        for step in ("ban", "reject"):
            response = self.client.post(f"{action}/{step}", headers=admin, json={"reason": "请修改"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["images"], [])
            self.assertEqual(self.client.put(post, headers=author, json={"content": "更新正文"}).status_code, 200)
        approved = self.client.post(f"{action}/approve", headers=admin)
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["images"], [])
