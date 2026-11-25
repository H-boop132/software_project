"""管理端：内容处理通知作者 / 管理端筛选、统计与审核记录。"""
from sqlalchemy import select

from app.models import Notification, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class AdminModerationTests(MySQLIntegrationTestCase):
    database_tag = "adminmod"

    def setUp(self):
        with self.Session() as db:
            db.query(Notification).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=99, username="admin", nickname="微澜管理员", password_hash="unused", role="admin"),
                User(id=1, username="author", nickname="作者甲", password_hash="unused"),
                User(id=2, username="other", nickname="作者乙", password_hash="unused"),
            ])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=1, content="公开内容甲", status="published"),
                Ripple(id=2, user_id=1, content="待审核内容甲", status="pending"),
                Ripple(id=3, user_id=2, content="公开内容乙", status="published"),
                Ripple(id=4, user_id=2, content="待审核内容乙", status="pending"),
            ])
            db.commit()

    # ---------------- 辅助 ----------------
    def inbox(self, user, **params):
        response = self.client.get("/api/v1/notifications", params=params, headers=self.headers(user))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def notices_in_db(self, user_id):
        with self.Session() as db:
            return list(db.scalars(
                select(Notification).where(Notification.recipient_id == user_id)
                .order_by(Notification.id)
            ).all())

    def post(self, path, payload=None, admin=99, expect=200):
        response = self.client.post(
            "/api/v1/admin" + path, json=payload, headers=self.headers(admin)
        )
        self.assertEqual(expect, response.status_code, response.text)
        return response.json()

    # ---------------- 用户封禁 / 解封 ----------------
    def test_ban_and_unban_notify_the_target_user(self):
        self.post("/users/1/ban", {"duration_days": 3, "reason": "刷屏广告"})

        rows = self.notices_in_db(1)
        self.assertEqual(1, len(rows))
        self.assertEqual(("moderation", 99), (rows[0].kind, rows[0].actor_id))
        self.assertIsNone(rows[0].ripple_id)
        self.assertIn("刷屏广告", rows[0].note)
        self.assertIn("封禁", rows[0].note)

        # 封禁期间被禁止登录各接口
        self.assertEqual(403, self.client.get(
            "/api/v1/notifications", headers=self.headers(1)
        ).status_code)

        self.post("/users/1/unban")
        items = self.inbox(1, kind="moderation")["items"]
        self.assertEqual(2, len(items))
        self.assertIn("解除", items[0]["note"])
        self.assertEqual("微澜管理员", items[0]["actor_name"])
        self.assertEqual([], self.inbox(2)["items"])

    # ---------------- 微澜封禁 / 审核 ----------------
    def test_ban_ripple_notifies_author_with_reason(self):
        self.post("/ripples/1/ban", {"reason": "含广告导流"})

        items = self.inbox(1, kind="moderation")["items"]
        self.assertEqual(1, len(items))
        self.assertEqual(1, items[0]["ripple_id"])
        self.assertIn("含广告导流", items[0]["note"])
        self.assertIn("下架", items[0]["note"])
        self.assertEqual([], self.inbox(2)["items"])

    def test_reject_notifies_author_and_keeps_content_hidden(self):
        data = self.post("/ripples/4/reject", {"reason": "表述不清"})
        self.assertEqual("banned", data["status"])

        item = self.inbox(2, kind="moderation")["items"][0]
        self.assertEqual(4, item["ripple_id"])
        self.assertIn("表述不清", item["note"])
        self.assertIn("驳回", item["note"])

    def test_approve_notifies_author(self):
        data = self.post("/ripples/2/approve")
        self.assertEqual("published", data["status"])

        item = self.inbox(1, kind="moderation")["items"][0]
        self.assertEqual(2, item["ripple_id"])
        self.assertIn("通过", item["note"])

    def test_delete_notifies_author_and_notice_survives(self):
        response = self.client.delete("/api/v1/admin/ripples/3", headers=self.headers(99))
        self.assertEqual(200, response.status_code, response.text)
        with self.Session() as db:
            self.assertIsNone(db.get(Ripple, 3))

        item = self.inbox(2, kind="moderation")["items"][0]
        # 微澜删除后外键置空，消息本身保留
        self.assertIsNone(item["ripple_id"])
        self.assertIn("删除", item["note"])
        self.assertIn("公开内容乙", item["note"])

    # ---------------- 管理端筛选 / 统计 / 审核记录 ----------------
    def test_user_list_filters_by_keyword_and_status(self):
        self.post("/users/1/ban", {"duration_days": None, "reason": "多次违规"})

        banned = self.client.get(
            "/api/v1/admin/users", params={"status": "banned"}, headers=self.headers(99)
        ).json()
        self.assertEqual([1], [row["id"] for row in banned])
        self.assertEqual("多次违规", banned[0]["ban_reason"])

        others = self.client.get(
            "/api/v1/admin/users", params={"keyword": "作者乙"}, headers=self.headers(99)
        ).json()
        self.assertEqual([2], [row["id"] for row in others])

        active = self.client.get(
            "/api/v1/admin/users", params={"status": "active"}, headers=self.headers(99)
        ).json()
        self.assertEqual([2, 99], sorted(row["id"] for row in active))

    def test_stats_and_ripple_status_filter(self):
        stats = self.client.get("/api/v1/admin/stats", headers=self.headers(99)).json()
        self.assertEqual(2, stats["pending"])
        self.assertEqual(0, stats["banned_users"])
        self.assertEqual(0, stats["banned_ripples"])

        self.post("/ripples/1/ban", {"reason": "违规"})
        stats = self.client.get("/api/v1/admin/stats", headers=self.headers(99)).json()
        self.assertEqual(1, stats["banned_ripples"])

        pending = self.client.get(
            "/api/v1/admin/ripples", params={"status": "pending"}, headers=self.headers(99)
        ).json()
        self.assertEqual([2, 4], sorted(row["id"] for row in pending))

        banned = self.client.get(
            "/api/v1/admin/ripples", params={"status": "banned"}, headers=self.headers(99)
        ).json()
        self.assertEqual([1], [row["id"] for row in banned])

    def test_review_history_lists_latest_first(self):
        self.post("/ripples/1/ban", {"reason": "含广告"})
        self.post("/ripples/2/approve")

        logs = self.client.get(
            "/api/v1/admin/reviews/history", params={"limit": 10}, headers=self.headers(99)
        ).json()
        self.assertEqual(["approve", "ban"], [row["action"] for row in logs])
        self.assertEqual({"id", "ripple_id", "action", "reason", "reviewer_id", "reviewer_name",
                          "author_id", "author_name", "content", "created_at"}, set(logs[0]))
        self.assertEqual(("待审核内容甲", "作者甲", "微澜管理员"),
                         (logs[0]["content"], logs[0]["author_name"], logs[0]["reviewer_name"]))
        self.assertEqual("含广告", logs[1]["reason"])

    def test_history_requires_admin(self):
        response = self.client.get("/api/v1/admin/reviews/history", headers=self.headers(1))
        self.assertEqual(403, response.status_code)
