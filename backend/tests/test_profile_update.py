"""资料编辑（PUT /users/me）的接口契约测试。"""
from app.models import Emotion, User
from tests.mysql_test_case import MySQLIntegrationTestCase

HASH = "pbkdf2_sha256$100000$674401762d8344795b1e6bb590976cfc$a1197f14de6f0f9ba1ef3c405769a9bc7391b94c03b3b70bc8c16dffd49b62aa"


class ProfileUpdateTests(MySQLIntegrationTestCase):
    database_tag = "profile"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.Session() as db:
            db.add_all([
                User(id=1, username="author", nickname="原昵称", password_hash=HASH,
                     bio="原签名", mood_tone="calm"),
                User(id=2, username="silent", nickname="夜行", password_hash=HASH,
                     ban_status="banned", ban_reason="违规"),
                User(id=5, username="admin", nickname="管理员", password_hash=HASH, role="admin"),
                Emotion(code="joy", name="喜悦", color="#F5A623"),
                Emotion(code="calm", name="平静", color="#7F8C8D"),
            ])
            db.commit()

    def _update(self, payload, user_id=1):
        return self.client.put("/api/v1/users/me", json=payload, headers=self.headers(user_id))

    def test_requires_login_and_rejects_banned_user(self):
        anonymous = self.client.put("/api/v1/users/me", json={"nickname": "匿名"})
        self.assertEqual(anonymous.status_code, 401, anonymous.text)

        banned = self._update({"nickname": "夜行改名"}, user_id=2)
        self.assertEqual(banned.status_code, 403, banned.text)

    def test_full_update_is_persisted_and_trimmed(self):
        response = self._update({
            "nickname": "  新昵称  ",
            "bio": "  新的签名  ",
            "mood_tone": "joy",
            "avatar_url": "/uploads/abc123def456.png",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["nickname"], "新昵称")
        self.assertEqual(body["bio"], "新的签名")
        self.assertEqual(body["mood_tone"], "joy")
        self.assertEqual(body["avatar_url"], "/uploads/abc123def456.png")

        me = self.client.get("/api/v1/users/me", headers=self.headers(1))
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["nickname"], "新昵称")

        public = self.client.get("/api/v1/users/1")
        self.assertEqual(public.status_code, 200, public.text)
        self.assertEqual(public.json()["nickname"], "新昵称")
        self.assertEqual(public.json()["bio"], "新的签名")

    def test_partial_update_keeps_untouched_fields(self):
        before = self.client.get("/api/v1/users/me", headers=self.headers(1)).json()
        response = self._update({"bio": "只改签名"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["bio"], "只改签名")
        self.assertEqual(body["nickname"], before["nickname"])
        self.assertEqual(body["mood_tone"], before["mood_tone"])
        self.assertEqual(body["avatar_url"], before["avatar_url"])

    def test_blank_optional_fields_clear_them(self):
        self._update({"bio": "临时签名", "mood_tone": "joy", "avatar_url": "/uploads/a1.png"})
        cleared = self._update({"bio": "   ", "mood_tone": None, "avatar_url": None})
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertIsNone(cleared.json()["bio"])
        self.assertIsNone(cleared.json()["mood_tone"])
        self.assertIsNone(cleared.json()["avatar_url"])

    def test_rejects_invalid_values(self):
        blank_nickname = self._update({"nickname": "   "})
        self.assertEqual(blank_nickname.status_code, 422, blank_nickname.text)

        long_nickname = self._update({"nickname": "名" * 51})
        self.assertEqual(long_nickname.status_code, 422, long_nickname.text)

        long_bio = self._update({"bio": "字" * 201})
        self.assertEqual(long_bio.status_code, 422, long_bio.text)

        bad_mood = self._update({"mood_tone": "nope"})
        self.assertEqual(bad_mood.status_code, 400, bad_mood.text)

        external_avatar = self._update({"avatar_url": "https://evil.example/x.png"})
        self.assertEqual(external_avatar.status_code, 422, external_avatar.text)

        traversal_avatar = self._update({"avatar_url": "/uploads/../secret.png"})
        self.assertEqual(traversal_avatar.status_code, 422, traversal_avatar.text)

    def test_cannot_overwrite_identity_or_moderation_fields(self):
        response = self._update({
            "nickname": "正常改名",
            "username": "hacked",
            "role": "admin",
            "ban_status": "active",
            "ban_reason": "自己解封",
            "id": 99,
        })
        self.assertEqual(response.status_code, 200, response.text)
        with self.Session() as db:
            user = db.get(User, 1)
            self.assertEqual(user.username, "author")
            self.assertEqual(user.role, "user")
            self.assertEqual(user.ban_status, "active")
            self.assertIsNone(user.ban_reason)
        self.assertEqual(response.json()["nickname"], "正常改名")

    def test_mood_tones_expose_all_emotions(self):
        response = self.client.get("/api/v1/moods/tones")
        self.assertEqual(response.status_code, 200, response.text)
        codes = {item["code"] for item in response.json()}
        self.assertEqual(codes, {"joy", "calm"})

    def test_admin_can_update_own_profile(self):
        response = self._update({"nickname": "管理员新名"}, user_id=5)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["nickname"], "管理员新名")
        self.assertEqual(response.json()["role"], "admin")
