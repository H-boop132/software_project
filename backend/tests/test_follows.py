"""关注、互关、关系分页及关注时间线的真实 MySQL 验证。"""
from concurrent.futures import ThreadPoolExecutor
import unittest

from sqlalchemy import func, select

from app.models import Follow, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class FollowTests(MySQLIntegrationTestCase):
    database_tag = "follows"

    def setUp(self):
        with self.Session() as db:
            db.query(Follow).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=i, username=f"user{i}", nickname=f"用户{i}", password_hash="unused",
                     ban_status="banned" if i == 4 else "active")
                for i in range(1, 5)
            ])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=2, content="作者二的公开内容", status="published"),
                Ripple(id=2, user_id=2, content="下架内容", status="banned"),
                Ripple(id=3, user_id=2, content="审核中", status="pending"),
                Ripple(id=4, user_id=3, content="作者三的公开内容", status="published"),
            ])
            db.commit()

    def mutate(self, method="PUT", target=2, actor=1):
        return self.client.request(method, f"/api/v1/users/{target}/follow", headers=self.headers(actor))

    def get_profile(self, target=2, viewer=1):
        response = self.client.get(f"/api/v1/users/{target}", headers=self.headers(viewer) if viewer else {})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_repeated_follow_and_unfollow_are_persistent(self):
        for _ in range(2):
            response = self.mutate()
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["is_following"])
            self.assertEqual(response.json()["follower_count"], 1)
        self.assertEqual(self.get_profile(target=1)["following_count"], 1)
        for _ in range(2):
            response = self.mutate("DELETE")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["is_following"])
            self.assertEqual(response.json()["follower_count"], 0)

    def test_mutual_follow_flags_and_cancel_preserves_reverse_edge(self):
        self.mutate()
        response = self.mutate(target=1, actor=2)
        self.assertTrue(response.json()["is_following"])
        self.assertTrue(response.json()["follows_you"])
        self.assertTrue(self.get_profile()["follows_you"])
        self.mutate("DELETE")
        profile = self.get_profile()
        self.assertFalse(profile["is_following"])
        self.assertTrue(profile["follows_you"])
        self.assertEqual(self.get_profile(target=1)["follower_count"], 1)

    def test_relation_pagination_counts_and_viewer_state(self):
        self.mutate(target=2)
        self.mutate(target=3)
        response = self.client.get("/api/v1/users/1/following?limit=1&offset=0", headers=self.headers())
        page = response.json()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(page["total"], 2)
        self.assertEqual(page["items"][0]["id"], 3)
        self.assertTrue(page["items"][0]["is_following"])
        second = self.client.get("/api/v1/users/1/following?limit=1&offset=1").json()
        self.assertEqual(second["items"][0]["id"], 2)
        self.assertFalse(second["items"][0]["is_following"])
        fans = self.client.get("/api/v1/users/2/followers", headers=self.headers(2)).json()
        self.assertEqual(fans["total"], 1)
        self.assertEqual(fans["items"][0]["id"], 1)
        self.assertTrue(fans["items"][0]["follows_you"])

    def test_self_missing_login_and_banned_actor(self):
        self.assertEqual(self.mutate(target=1).status_code, 400)
        self.assertEqual(self.mutate(target=9999).status_code, 404)
        self.assertEqual(self.mutate(actor=4).status_code, 403)
        self.assertEqual(self.client.put("/api/v1/users/2/follow").status_code, 401)
        self.assertEqual(self.client.delete("/api/v1/users/2/follow").status_code, 401)

    def test_following_feed_filters_visibility_and_updates_after_unfollow(self):
        url = "/api/v1/ripples/following"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers=self.headers()).json(), [])
        self.mutate()
        response = self.client.get(url, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()], [1])
        self.assertEqual(self.client.get(url, params={"keyword": "no-match"}, headers=self.headers()).json(), [])
        self.mutate("DELETE")
        self.assertEqual(self.client.get(url, headers=self.headers()).json(), [])

    def test_user_posts_hide_nonpublic_content(self):
        response = self.client.get("/api/v1/users/2/ripples", headers=self.headers(2))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()], [1])
        self.assertEqual(self.client.get("/api/v1/users/9999/ripples").status_code, 404)

    def test_concurrent_duplicate_and_mutual_requests(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: self.mutate(), range(8)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Follow.id))), 1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.mutate, "PUT", 1, 2)
            b = pool.submit(self.mutate, "PUT", 2, 1)
            self.assertEqual(a.result().status_code, 200)
            self.assertEqual(b.result().status_code, 200)
        self.assertTrue(self.get_profile()["follows_you"])

    def test_public_profile_excludes_admin_fields_and_anonymous_relation(self):
        self.mutate()
        profile = self.get_profile(viewer=None)
        for field in ("password_hash", "ban_reason", "ban_until"):
            self.assertNotIn(field, profile)
        self.assertFalse(profile["is_following"])
        self.assertEqual(profile["follower_count"], 1)

    def test_invalid_pagination_and_missing_relation_owner(self):
        for path in ("following", "followers"):
            self.assertEqual(self.client.get(f"/api/v1/users/9999/{path}").status_code, 404)
            for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
                self.assertEqual(self.client.get(f"/api/v1/users/1/{path}", params=params).status_code, 422)
        self.assertEqual(self.mutate(target=0).status_code, 422)


if __name__ == "__main__":
    unittest.main()
