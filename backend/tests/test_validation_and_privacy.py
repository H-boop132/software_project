"""回归测试：作者信息脱敏、发布入参校验、令牌容错、关键词转义、配图来源校验。"""
from tests.mysql_test_case import MySQLIntegrationTestCase
from app.models import Echo, Emotion, Ripple, Topic, User

HASH = "pbkdf2_sha256$100000$674401762d8344795b1e6bb590976cfc$a1197f14de6f0f9ba1ef3c405769a9bc7391b94c03b3b70bc8c16dffd49b62aa"


class ValidationPrivacyTests(MySQLIntegrationTestCase):
    database_tag = "validation"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.Session() as db:
            db.add_all([
                User(id=1, username="author", nickname="作者", password_hash=HASH),
                User(id=2, username="silent", nickname="夜行", password_hash=HASH,
                     ban_status="banned", ban_reason="涉嫌违规交易"),
                User(id=5, username="admin", nickname="管理员", password_hash=HASH, role="admin"),
                Topic(id=1, name="创意", slug="ideas"),
                Emotion(code="joy", name="喜悦", color="#F5A623"),
            ])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=1, topic_id=1, emotion_code="joy", content="湖边的想法"),
                Ripple(id=3, user_id=2, topic_id=1, emotion_code="joy", content="夜里的碎碎念"),
            ])
            db.flush()
            db.add(Echo(id=1, root_ripple_id=3, user_id=1, content="我也这么想"))
            db.commit()

    def test_public_payload_hides_ban_fields(self):
        response = self.client.get("/api/v1/ripples")
        self.assertEqual(response.status_code, 200, response.text)
        allowed = {"id", "nickname", "avatar_url", "bio", "mood_tone"}
        for item in response.json():
            self.assertLessEqual(set(item["user"]), allowed, item["user"])

        detail = self.client.get("/api/v1/ripples/3")
        self.assertEqual(detail.status_code, 200, detail.text)
        body = detail.json()
        self.assertLessEqual(set(body["ripple"]["user"]), allowed)
        for echo in body["echoes"]:
            self.assertLessEqual(set(echo["user"]), allowed)

    def test_create_rejects_unknown_topic_and_emotion(self):
        bad_topic = self.client.post("/api/v1/ripples", json={"content": "测试", "topic_id": 999},
                                     headers=self.headers(1))
        self.assertEqual(bad_topic.status_code, 400, bad_topic.text)

        bad_emotion = self.client.post("/api/v1/ripples", json={"content": "测试", "emotion_code": "nope"},
                                       headers=self.headers(1))
        self.assertEqual(bad_emotion.status_code, 400, bad_emotion.text)

    def test_create_rejects_blank_content_and_external_image(self):
        blank = self.client.post("/api/v1/ripples", json={"content": "   "}, headers=self.headers(1))
        self.assertEqual(blank.status_code, 422, blank.text)

        external = self.client.post(
            "/api/v1/ripples", json={"content": "外链", "images": ["https://evil.example/x.png"]},
            headers=self.headers(1),
        )
        self.assertEqual(external.status_code, 422, external.text)

        traversal = self.client.post(
            "/api/v1/ripples", json={"content": "穿越", "images": ["/uploads/../secret.png"]},
            headers=self.headers(1),
        )
        self.assertEqual(traversal.status_code, 422, traversal.text)

        ok = self.client.post(
            "/api/v1/ripples", json={"content": "  正文  ", "images": ["/uploads/a1b2c3.jpeg"]},
            headers=self.headers(1),
        )
        self.assertEqual(ok.status_code, 201, ok.text)
        self.assertEqual(ok.json()["content"], "正文")

    def test_register_requires_real_nickname(self):
        blank = self.client.post("/api/v1/auth/register",
                                 json={"username": "newbie", "nickname": "  ", "password": "123456"})
        self.assertEqual(blank.status_code, 422, blank.text)

        ok = self.client.post("/api/v1/auth/register",
                              json={"username": "newbie", "nickname": "  新人  ", "password": "123456"})
        self.assertEqual(ok.status_code, 201, ok.text)
        self.assertEqual(ok.json()["user"]["nickname"], "新人")

        login = self.client.post("/api/v1/auth/login", json={"username": "newbie", "password": "123456"})
        self.assertEqual(login.status_code, 200, login.text)

    def test_non_numeric_token_subject_is_unauthorized(self):
        for path in ("/api/v1/users/me", "/api/v1/notifications/unread-count"):
            response = self.client.get(path, headers=self.headers("abc"))
            self.assertEqual(response.status_code, 401, f"{path} -> {response.text}")

    def test_keyword_wildcards_are_escaped(self):
        def ids(keyword):
            response = self.client.get("/api/v1/ripples", params={"keyword": keyword})
            self.assertEqual(response.status_code, 200, response.text)
            return [item["id"] for item in response.json()]

        self.assertEqual(ids("%"), [])
        self.assertEqual(ids("_"), [])
        self.assertEqual(ids("湖边"), [1])
