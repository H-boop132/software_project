"""我的喜欢：点赞列表分页、可见性与状态验证。"""
from datetime import datetime, timedelta
import unittest

from app.models import Echo, Like, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class MyLikesTests(MySQLIntegrationTestCase):
    database_tag = "mylikes"

    def setUp(self):
        with self.Session() as db:
            db.query(Like).delete()
            db.query(Echo).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=1, username="alice", nickname="Alice", password_hash="unused"),
                User(id=2, username="bob", nickname="Bob", password_hash="unused"),
                User(id=3, username="banned", nickname="Banned", password_hash="unused", ban_status="banned"),
            ])
            db.flush()
            db.add_all([
                Ripple(id=i, user_id=2, content=f"公开微澜 {i}", status="published")
                for i in range(1, 4)
            ])
            db.add_all([
                Ripple(id=4, user_id=1, content="自己已下架的内容", status="banned"),
                Ripple(id=5, user_id=2, content="待审核内容", status="pending"),
            ])
            db.flush()
            start = datetime(2026, 1, 1)
            db.add_all([
                Like(user_id=1, ripple_id=i, created_at=start + timedelta(minutes=i))
                for i in range(1, 6)
            ])
            db.add(Like(user_id=2, ripple_id=1))
            db.add(Echo(user_id=2, root_ripple_id=1, content="回应"))
            db.commit()

    def page(self, user_id=1, **params):
        response = self.client.get(
            "/api/v1/interactions/likes", params=params, headers=self.headers(user_id)
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_only_public_liked_ripples_newest_like_first(self):
        page = self.page(limit=5)
        self.assertEqual((page["total"], page["limit"], page["offset"]), (3, 5, 0))
        self.assertEqual([item["id"] for item in page["items"]], [3, 2, 1])
        self.assertTrue(all(item["is_liked"] for item in page["items"]))
        self.assertTrue(all(item["status"] == "published" for item in page["items"]))

    def test_pagination(self):
        first = self.page(limit=2, offset=0)
        self.assertEqual([item["id"] for item in first["items"]], [3, 2])
        second = self.page(limit=2, offset=2)
        self.assertEqual([item["id"] for item in second["items"]], [1])
        self.assertEqual(second["total"], 3)

    def test_only_current_users_likes(self):
        page = self.page(user_id=2)
        self.assertEqual(page["total"], 1)
        self.assertEqual([item["id"] for item in page["items"]], [1])

    def test_like_and_echo_counts_are_personalized(self):
        ripple = next(item for item in self.page()["items"] if item["id"] == 1)
        self.assertEqual(ripple["like_count"], 2)
        self.assertEqual(ripple["echo_count"], 1)
        self.assertFalse(ripple["is_collected"])

    def test_cancel_like_removes_item_and_updates_total(self):
        response = self.client.delete(
            "/api/v1/interactions/ripples/3/like", headers=self.headers()
        )
        self.assertEqual(response.status_code, 200, response.text)
        page = self.page()
        self.assertEqual((page["total"], [item["id"] for item in page["items"]]), (2, [2, 1]))

    def test_banned_liked_content_hidden_and_like_remains_after_unban(self):
        page = self.page()
        self.assertNotIn(4, [item["id"] for item in page["items"]])
        with self.Session() as db:
            db.get(Ripple, 4).status = "published"
            db.commit()
        page = self.page()
        self.assertIn(4, [item["id"] for item in page["items"]])
        self.assertEqual(page["total"], 4)

    def test_tied_timestamps_have_stable_secondary_sort(self):
        with self.Session() as db:
            db.query(Like).filter(Like.user_id == 1).update(
                {Like.created_at: datetime(2026, 1, 1)}, synchronize_session=False
            )
            db.commit()
        self.assertEqual([item["id"] for item in self.page(limit=3)["items"]], [3, 2, 1])

    def test_empty_list_and_out_of_range_page(self):
        with self.Session() as db:
            db.query(Like).filter(Like.user_id == 1).delete()
            db.commit()
        page = self.page()
        self.assertEqual((page["total"], page["items"]), (0, []))
        self.assertEqual(self.page(offset=100)["items"], [])

    def test_authentication_and_pagination_validation(self):
        self.assertEqual(self.client.get("/api/v1/interactions/likes").status_code, 401)
        banned = self.client.get(
            "/api/v1/interactions/likes", headers=self.headers(3)
        )
        self.assertEqual(banned.status_code, 403)
        for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": "invalid"}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(
                    "/api/v1/interactions/likes", params=params, headers=self.headers()
                ).status_code, 422)


if __name__ == "__main__":
    unittest.main()
