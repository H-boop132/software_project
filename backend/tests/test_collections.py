"""收藏集成测试：真实 MySQL、独立账号状态与并发请求。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import unittest

from sqlalchemy import func, select

from app.models import Collection, Like, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class CollectionIntegrationTests(MySQLIntegrationTestCase):
    database_tag = "collections"

    def setUp(self):
        with self.Session() as db:
            db.query(Collection).delete()
            db.query(Like).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=1, username="alice", nickname="Alice", password_hash="unused"),
                User(id=2, username="bob", nickname="Bob", password_hash="unused"),
                User(id=3, username="carol", nickname="Carol", password_hash="unused"),
                User(id=4, username="banned", nickname="Banned", password_hash="unused", ban_status="banned"),
                User(id=5, username="expired", nickname="Expired", password_hash="unused", ban_status="banned", ban_until=datetime.now() - timedelta(days=1)),
            ])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=1, content="公开微澜", status="published"),
                Ripple(id=2, user_id=1, content="下架微澜", status="banned"),
                Ripple(id=3, user_id=1, content="待审核微澜", status="pending"),
            ])
            db.flush()
            db.add(Collection(user_id=3, ripple_id=1))
            db.add(Like(user_id=3, ripple_id=1))
            db.commit()

    def mutate(self, method, ripple_id=1, user_id=1):
        return self.client.request(
            method, f"/api/v1/interactions/ripples/{ripple_id}/collection",
            headers=self.headers(user_id),
        )

    def assert_state(self, response, collected):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"ripple_id": 1, "is_collected": collected})

    def test_repeated_collection_persists_one_record(self):
        for _ in range(2):
            self.assert_state(self.mutate("PUT"), True)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Collection.id)).where(Collection.user_id == 1)), 1)
        detail = self.client.get("/api/v1/ripples/1", headers=self.headers()).json()["ripple"]
        self.assertTrue(detail["is_collected"])

    def test_repeated_cancel_preserves_other_users_collection(self):
        self.assert_state(self.mutate("PUT"), True)
        for _ in range(2):
            self.assert_state(self.mutate("DELETE"), False)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(Collection.user_id)), 3)

    def test_reads_are_personalized_and_anonymous_is_false(self):
        self.mutate("PUT")
        for user_id, collected in ((None, False), (1, True), (2, False), (3, True)):
            headers = self.headers(user_id) if user_id else {}
            with self.subTest(user=user_id):
                listing = self.client.get("/api/v1/ripples", headers=headers)
                self.assertEqual(listing.status_code, 200, listing.text)
                self.assertEqual(len(listing.json()), 1)
                self.assertEqual(listing.json()[0]["is_collected"], collected)
                detail = self.client.get("/api/v1/ripples/1", headers=headers).json()
                self.assertEqual(detail["ripple"]["is_collected"], collected)
        own = self.client.get("/api/v1/ripples/mine", headers=self.headers()).json()
        self.assertTrue(next(item for item in own if item["id"] == 1)["is_collected"])

    def test_requires_login_and_rejects_banned_user(self):
        for method in ("PUT", "DELETE"):
            response = self.client.request(method, "/api/v1/interactions/ripples/1/collection")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(self.mutate(method, user_id=4).status_code, 403)

    def test_expired_ban_reuses_auto_unban_rule(self):
        self.assert_state(self.mutate("PUT", user_id=5), True)
        with self.Session() as db:
            self.assertEqual(db.get(User, 5).ban_status, "active")

    def test_hidden_and_missing_content_rejects_both_operations(self):
        for ripple_id in (2, 3, 999999):
            for user_id in (1, 2):
                for method in ("PUT", "DELETE"):
                    with self.subTest(ripple=ripple_id, user=user_id, method=method):
                        self.assertEqual(self.mutate(method, ripple_id, user_id).status_code, 404)

    def test_invalid_id_is_rejected(self):
        for method in ("PUT", "DELETE"):
            for ripple_id in (0, -1, "invalid"):
                self.assertEqual(self.mutate(method, ripple_id).status_code, 422)

    def test_concurrent_identical_requests_are_idempotent(self):
        for method, collected, count in (("PUT", True, 2), ("DELETE", False, 1)):
            with ThreadPoolExecutor(max_workers=8) as pool:
                responses = list(pool.map(lambda _: self.mutate(method), range(8)))
            for response in responses:
                self.assert_state(response, collected)
            with self.Session() as db:
                self.assertEqual(db.scalar(select(func.count(Collection.id))), count)

    def test_collections_and_likes_are_independent(self):
        self.mutate("PUT")
        detail = self.client.get("/api/v1/ripples/1", headers=self.headers()).json()["ripple"]
        self.assertTrue(detail["is_collected"])
        self.assertFalse(detail["is_liked"])
        self.assertEqual(detail["like_count"], 1)
        like_url = "/api/v1/interactions/ripples/1/like"
        response = self.client.put(like_url, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.mutate("DELETE")
        detail = self.client.get("/api/v1/ripples/1", headers=self.headers()).json()["ripple"]
        self.assertFalse(detail["is_collected"])
        self.assertTrue(detail["is_liked"])
        self.assertEqual(detail["like_count"], 2)


if __name__ == "__main__":
    unittest.main()
