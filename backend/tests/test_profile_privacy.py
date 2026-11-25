"""个人主页列表隐私：设置、访客拦截与本人可见。"""
from datetime import datetime, timedelta
import unittest

from app.models import Collection, Echo, Follow, Like, Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class ProfilePrivacyTests(MySQLIntegrationTestCase):
    database_tag = "privacy"

    def setUp(self):
        with self.Session() as db:
            db.query(Follow).delete()
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
                Ripple(id=1, user_id=2, content="公开一", status="published"),
                Ripple(id=2, user_id=2, content="公开二", status="published"),
                Ripple(id=3, user_id=2, content="已下架", status="banned"),
                Ripple(id=4, user_id=1, content="审核中", status="pending"),
            ])
            db.flush()
            db.add_all([
                Follow(follower_id=1, followee_id=2, created_at=datetime(2026, 1, 1)),
                Follow(follower_id=3, followee_id=1, created_at=datetime(2026, 1, 1)),
            ])
            db.add_all([
                Like(user_id=1, ripple_id=1, created_at=datetime(2026, 1, 1)),
                Like(user_id=1, ripple_id=3, created_at=datetime(2026, 1, 2)),
                Like(user_id=1, ripple_id=4, created_at=datetime(2026, 1, 3)),
                Like(user_id=2, ripple_id=1, created_at=datetime(2026, 1, 1, 1)),
            ])
            db.add_all([
                Collection(user_id=1, ripple_id=2, created_at=datetime(2026, 1, 1)),
                Collection(user_id=1, ripple_id=3, created_at=datetime(2026, 1, 2)),
                Collection(user_id=1, ripple_id=4, created_at=datetime(2026, 1, 3)),
            ])
            db.add(Echo(user_id=2, root_ripple_id=1, content="回应"))
            db.commit()
        self.reset_privacy()

    def reset_privacy(self):
        with self.Session() as db:
            user = db.get(User, 1)
            user.hide_following = False
            user.hide_followers = False
            user.hide_likes = False
            user.hide_collections = False
            db.commit()

    def set_privacy(self, **values):
        response = self.client.put(
            "/api/v1/users/me/privacy", json=values, headers=self.headers(1)
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def get_profile(self, target=1, viewer=2):
        response = self.client.get(
            f"/api/v1/users/{target}", headers=self.headers(viewer) if viewer else {}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def get_list(self, kind, target=1, viewer=2):
        return self.client.get(
            f"/api/v1/users/{target}/{kind}",
            headers=self.headers(viewer) if viewer else {},
        )

    def test_defaults_are_public_and_payload_is_visible_on_profile(self):
        profile = self.get_profile(viewer=None)
        for flag in ("hide_following", "hide_followers", "hide_likes", "hide_collections"):
            self.assertFalse(profile[flag])
        self.assertEqual(self.get_list("following").status_code, 200)
        self.assertEqual(self.get_list("followers").status_code, 200)
        self.assertEqual(self.get_list("likes").status_code, 200)
        self.assertEqual(self.get_list("collections").status_code, 200)

    def test_privacy_update_is_partial_and_persisted(self):
        updated = self.set_privacy(hide_likes=True, hide_collections=False)
        self.assertTrue(updated["hide_likes"])
        self.assertFalse(updated["hide_collections"])
        self.assertFalse(updated["hide_following"])
        self.assertTrue(self.get_profile()["hide_likes"])
        self.assertTrue(self.client.get("/api/v1/users/me", headers=self.headers(1)).json()["hide_likes"])

    def test_hidden_likes_and_collections_block_visitors_but_not_owner(self):
        self.set_privacy(hide_likes=True, hide_collections=True)
        for kind, label in (("likes", "喜欢列表"), ("collections", "收藏列表")):
            with self.subTest(kind=kind):
                blocked = self.get_list(kind, viewer=2)
                self.assertEqual(blocked.status_code, 403, blocked.text)
                self.assertEqual(blocked.json()["detail"], f"该用户的{label}不对外开放")
                self.assertEqual(self.get_list(kind, viewer=None).status_code, 403)
                self.assertEqual(self.get_list(kind, viewer=1).status_code, 200)

    def test_each_switch_only_affects_its_own_list(self):
        self.set_privacy(hide_likes=True)
        self.assertEqual(self.get_list("likes").status_code, 403)
        self.assertEqual(self.get_list("collections").status_code, 200)
        self.assertEqual(self.get_list("following").status_code, 200)
        self.assertEqual(self.get_list("followers").status_code, 200)
        self.set_privacy(hide_following=True)
        self.assertEqual(self.get_list("following").status_code, 403)
        self.assertEqual(self.get_list("followers").status_code, 200)
        self.set_privacy(hide_followers=True)
        self.assertEqual(self.get_list("followers").status_code, 403)
        self.assertEqual(self.get_list("collections").status_code, 200)

    def test_hidden_relations_show_specific_message(self):
        self.set_privacy(hide_following=True, hide_followers=True)
        for kind, label in (("following", "关注列表"), ("followers", "粉丝列表")):
            with self.subTest(kind=kind):
                response = self.get_list(kind)
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["detail"], f"该用户的{label}不对外开放")
                self.assertEqual(self.get_list(kind, viewer=1).status_code, 200)

    def test_public_likes_and_collections_only_include_published(self):
        likes = self.get_list("likes").json()
        self.assertEqual((likes["total"], [item["id"] for item in likes["items"]]), (1, [1]))
        self.assertEqual(likes["items"][0]["like_count"], 2)
        self.assertEqual(likes["items"][0]["echo_count"], 1)
        self.assertTrue(likes["items"][0]["is_liked"])
        self.assertFalse(likes["items"][0]["is_collected"])
        collections = self.get_list("collections").json()
        self.assertEqual((collections["total"], [item["id"] for item in collections["items"]]), (1, [2]))

    def test_likes_and_collections_pagination_validation(self):
        for kind in ("likes", "collections"):
            for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
                with self.subTest(kind=kind, params=params):
                    self.assertEqual(self.client.get(
                        f"/api/v1/users/1/{kind}", params=params, headers=self.headers(2)
                    ).status_code, 422)
        self.assertEqual(self.get_list("likes", target=9999).status_code, 404)
        self.assertEqual(self.get_list("collections", target=9999).status_code, 404)

    def test_auth_required_to_change_privacy_and_invalid_payload(self):
        self.assertEqual(self.client.put("/api/v1/users/me/privacy", json={"hide_likes": True}).status_code, 401)
        with self.Session() as db:
            user = db.get(User, 3)
            user.hide_likes = True
            db.commit()
        self.assertEqual(self.client.put("/api/v1/users/me/privacy", json={"hide_likes": True}, headers=self.headers(3)).status_code, 403)
        self.assertEqual(self.client.put(
            "/api/v1/users/me/privacy", json={"hide_likes": "not-bool"}, headers=self.headers(1)
        ).status_code, 422)

    def test_privacy_does_not_break_own_personal_lists(self):
        self.set_privacy(hide_likes=True, hide_collections=True)
        likes = self.client.get("/api/v1/interactions/likes", headers=self.headers(1))
        collections = self.client.get("/api/v1/interactions/collections", headers=self.headers(1))
        self.assertEqual(likes.status_code, 200)
        self.assertEqual(likes.json()["total"], 1)
        self.assertEqual(collections.status_code, 200)
        self.assertEqual(collections.json()["total"], 1)


if __name__ == "__main__":
    unittest.main()
