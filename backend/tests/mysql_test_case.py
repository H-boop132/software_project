"""共享真实 MySQL 测试库，避免对开发数据库进行测试写入。"""
import os
from pathlib import Path
import re
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app


@unittest.skipUnless(os.environ.get("WEILAN_MYSQL_TESTS") == "1", "需设置 WEILAN_MYSQL_TESTS=1")
class MySQLIntegrationTestCase(unittest.TestCase):
    database_tag = "interactions"

    @classmethod
    def setUpClass(cls):
        url = make_url(settings.database_url)
        if url.get_backend_name() != "mysql":
            raise unittest.SkipTest("这些用例需要 MySQL")
        if not re.fullmatch(r"[a-z]+", cls.database_tag):
            raise RuntimeError("非法测试库标签")
        cls.database_name = f"weilan_test_{cls.database_tag}_" + uuid4().hex
        cls.admin_engine = create_engine(url.set(database=None), isolation_level="AUTOCOMMIT")
        cls.addClassCleanup(cls.admin_engine.dispose)
        with cls.admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE `{cls.database_name}` CHARACTER SET utf8mb4"))
        cls.addClassCleanup(cls.drop_test_database)
        cls.engine = create_engine(url.set(database=cls.database_name), pool_size=12)
        cls.addClassCleanup(cls.engine.dispose)
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
        if not re.fullmatch(r"weilan_test_[a-z]+_[0-9a-f]{32}", cls.database_name):
            raise RuntimeError("拒绝清理名称不符合约定的数据库")
        with cls.admin_engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE `{cls.database_name}`"))

    @classmethod
    def restore_overrides(cls):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(cls.original_overrides)

    @staticmethod
    def headers(user_id=1):
        return {"Authorization": "Bearer " + create_access_token(str(user_id))}
