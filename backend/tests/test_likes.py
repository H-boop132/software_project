"""MySQL 集成测试：WEILAN_MYSQL_TESTS=1 时创建独立的临时数据库。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Like, Ripple, User


@unittest.skipUnless(os.environ.get("WEILAN_MYSQL_TESTS") == "1", "需设置 WEILAN_MYSQL_TESTS=1")
class LikeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(settings.database_url)
        if url.get_backend_name() != "mysql":
            raise unittest.SkipTest("这些用例需要 MySQL")
        cls.database_name = "weilan_test_likes_" + uuid4().hex
        cls.admin_engine = create_engine(url.set(database=None), isolation_level="AUTOCOMMIT")
        cls.addClassCleanup(cls.admin_engine.dispose)
        with cls.admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE `{cls.database_name}` CHARACTER SET utf8mb4"))
        cls.addClassCleanup(cls.drop_test_database)
        cls.engine = create_engine(url.set(database=cls.database_name), pool_size=12)
        cls.addClassCleanup(cls.engine.dispose)
        # 使用项目真实 MySQL DDL，不对开发数据库运行重建脚本。
        schema = (Path(__file__).resolve().parents[2] / "sql" / "02_schema.sql").read_text(encoding="utf-8-sig")
        schema = schema.replace("USE `weilan`;", f"USE `{cls.database_name}`;")
        schema = "\n".join(line for line in schema.splitlines() if not line.lstrip().upper().startswith("DROP TABLE"))
        raw = cls.engine.raw_connection()
        try:
            with raw.cursor() as cursor:
                for statement in schema.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
            raw.commit()
        finally:
            raw.close()
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)

        def test_db():
            with cls.Session() as db:
                yield db

        cls.original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = test_db
        cls.addClassCleanup(cls.restore_overrides)
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    @classmethod
    def drop_test_database(cls):
        if not re.fullmatch(r"weilan_test_likes_[0-9a-f]{32}", cls.database_name):
            raise RuntimeError("拒绝清理名称不符合约定的数据库")
        with cls.admin_engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE `{cls.database_name}`"))

    @classmethod
    def restore_overrides(cls):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(cls.original_overrides)

    def setUp(self):
        with self.Session() as db:
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
            db.add(Like(user_id=3, ripple_id=1))
            db.commit()

    @staticmethod
    def headers(user_id=1):
        return {"Authorization": "Bearer " + create_access_token(str(user_id))}

    def mutate(self, method, ripple_id=1, user_id=1):
        return self.client.request(method, f"/api/v1/interactions/ripples/{ripple_id}/like", headers=self.headers(user_id))

    def assert_state(self, response, liked, count):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"ripple_id": 1, "is_liked": liked, "like_count": count})

    def test_repeated_like_is_persistent_and_idempotent(self):
        for _ in range(2):
            self.assert_state(self.mutate("PUT"), True, 2)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Like.id)).where(Like.user_id == 1)), 1)
        detail = self.client.get("/api/v1/ripples/1", headers=self.headers()).json()["ripple"]
        self.assertTrue(detail["is_liked"])
        self.assertEqual(detail["like_count"], 2)

    def test_repeated_unlike_preserves_other_users_likes(self):
        self.assert_state(self.mutate("PUT"), True, 2)
        for _ in range(2):
            self.assert_state(self.mutate("DELETE"), False, 1)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(Like.user_id)), 3)

    def test_reads_are_personalized_and_anonymous_is_false(self):
        self.mutate("PUT")
        for user_id, liked in ((None, False), (1, True), (2, False), (3, True)):
            headers = self.headers(user_id) if user_id else {}
            with self.subTest(user=user_id):
                listing = self.client.get("/api/v1/ripples", headers=headers)
                self.assertEqual(listing.status_code, 200, listing.text)
                self.assertEqual(len(listing.json()), 1)
                self.assertEqual(listing.json()[0]["is_liked"], liked)
                self.assertEqual(listing.json()[0]["like_count"], 2)
                detail = self.client.get("/api/v1/ripples/1", headers=headers).json()
                self.assertEqual(detail["ripple"]["is_liked"], liked)
        own = self.client.get("/api/v1/ripples/mine", headers=self.headers()).json()
        self.assertTrue(next(item for item in own if item["id"] == 1)["is_liked"])

    def test_requires_login_and_rejects_banned_user(self):
        for method in ("PUT", "DELETE"):
            response = self.client.request(method, "/api/v1/interactions/ripples/1/like")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(self.mutate(method, user_id=4).status_code, 403)

    def test_expired_ban_uses_existing_auto_unban_rule(self):
        self.assert_state(self.mutate("PUT", user_id=5), True, 2)
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

    def test_concurrent_identical_requests_do_not_duplicate_or_underflow(self):
        for method, liked, count in (("PUT", True, 2), ("DELETE", False, 1)):
            with ThreadPoolExecutor(max_workers=8) as pool:
                responses = list(pool.map(lambda _: self.mutate(method), range(8)))
            for response in responses:
                self.assert_state(response, liked, count)
            with self.Session() as db:
                self.assertEqual(db.scalar(select(func.count(Like.id))), count)


if __name__ == "__main__":
    unittest.main()
