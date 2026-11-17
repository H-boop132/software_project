"""我的收藏分页、可见性及状态联动的 MySQL 集成测试。"""
from datetime import datetime, timedelta
import unittest

from sqlalchemy import delete

from app.models import Collection, Echo, Like, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class CollectionListTests(MySQLIntegrationTestCase):
    database_tag = "collectionlist"

    def setUp(self):
        with self.Session() as db:
            db.query(Collection).delete()
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
                for i in range(1, 7)
            ])
            db.add_all([
                Ripple(id=7, user_id=1, content="作者自己的下架内容", status="banned"),
                Ripple(id=8, user_id=2, content="待审核内容", status="pending"),
            ])
            db.flush()
            start = datetime(2026, 1, 1)
            db.add_all([
                Collection(id=i, user_id=1, ripple_id=i, created_at=start + timedelta(minutes=i))
                for i in range(1, 9)
            ])
            db.add(Collection(id=9, user_id=2, ripple_id=1))
            db.add(Like(user_id=1, ripple_id=6))
            db.add(Like(user_id=2, ripple_id=6))
            db.add(Echo(user_id=2, root_ripple_id=6, content="回应"))
            db.commit()

    def listing(self, user_id=1, **params):
        return self.client.get(
            "/api/v1/interactions/collections", params=params, headers=self.headers(user_id)
        )

    def page(self, user_id=1, **params):
        response = self.listing(user_id, **params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_pagination_total_and_newest_collection_first(self):
        first = self.page(limit=5, offset=0)
        self.assertEqual((first["total"], first["limit"], first["offset"]), (6, 5, 0))
        self.assertEqual([item["id"] for item in first["items"]], [6, 5, 4, 3, 2])
        second = self.page(limit=5, offset=5)
        self.assertEqual([item["id"] for item in second["items"]], [1])
        self.assertEqual(second["total"], 6)

    def test_hidden_content_excluded_even_for_author_and_before_paging(self):
        page = self.page(limit=1)
        self.assertEqual(page["total"], 6)
        self.assertEqual([item["id"] for item in page["items"]], [6])
        self.assertTrue(all(item["status"] == "published" for item in self.page()["items"]))

    def test_only_current_users_records_are_visible(self):
        page = self.page(user_id=2)
        self.assertEqual(page["total"], 1)
        self.assertEqual([item["id"] for item in page["items"]], [1])

    def test_personalized_likes_counts_and_collections(self):
        ripple = self.page(limit=1)["items"][0]
        self.assertTrue(ripple["is_collected"])
        self.assertTrue(ripple["is_liked"])
        self.assertEqual((ripple["like_count"], ripple["echo_count"]), (2, 1))
        self.assertTrue(all(item["is_collected"] for item in self.page()["items"]))

    def test_cancel_last_item_on_last_page_updates_total_and_valid_page(self):
        response = self.client.delete(
            "/api/v1/interactions/ripples/1/collection", headers=self.headers()
        )
        self.assertEqual(response.status_code, 200, response.text)
        last = self.page(limit=5, offset=5)
        self.assertEqual((last["total"], last["items"]), (5, []))
        first = self.page(limit=5, offset=0)
        self.assertEqual([item["id"] for item in first["items"]], [6, 5, 4, 3, 2])
        self.assertEqual(self.page(user_id=2)["total"], 1)

    def test_empty_and_out_of_range_pages(self):
        self.assertEqual(self.page(offset=100)["items"], [])
        with self.Session() as db:
            db.execute(delete(Collection).where(Collection.user_id == 1))
            db.commit()
        page = self.page()
        self.assertEqual((page["total"], page["items"]), (0, []))

    def test_tied_timestamps_have_stable_secondary_sort(self):
        with self.Session() as db:
            db.query(Collection).filter(Collection.user_id == 1).update(
                {Collection.created_at: datetime(2026, 1, 1)}, synchronize_session=False
            )
            db.commit()
        self.assertEqual([item["id"] for item in self.page(limit=3)["items"]], [6, 5, 4])
        self.assertEqual([item["id"] for item in self.page(limit=3, offset=3)["items"]], [3, 2, 1])

    def test_authentication_and_pagination_validation(self):
        self.assertEqual(self.client.get("/api/v1/interactions/collections").status_code, 401)
        self.assertEqual(self.listing(user_id=3).status_code, 403)
        for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": "invalid"}):
            with self.subTest(params=params):
                self.assertEqual(self.listing(**params).status_code, 422)

    def test_content_removed_or_hidden_after_collection_disappears(self):
        with self.Session() as db:
            db.get(Ripple, 6).status = "banned"
            db.execute(delete(Ripple).where(Ripple.id == 5))
            db.commit()
        page = self.page()
        self.assertEqual(page["total"], 4)
        self.assertEqual([item["id"] for item in page["items"]], [4, 3, 2, 1])


if __name__ == "__main__":
    unittest.main()
