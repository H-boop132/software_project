"""账号安全（改密码 / 注销）与上传文件清理。"""
import shutil
import tempfile
from pathlib import Path

from app.core.config import settings
from app.core.security import hash_password
from app.models import Ripple, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class AccountSecurityTests(MySQLIntegrationTestCase):
    database_tag = "account"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_tmp = tempfile.mkdtemp(prefix="weilan_uploads_")
        cls.original_upload_dir = settings.upload_dir
        settings.upload_dir = cls.upload_tmp
        cls.addClassCleanup(cls.restore_upload_dir)

    @classmethod
    def restore_upload_dir(cls):
        settings.upload_dir = cls.original_upload_dir
        shutil.rmtree(cls.upload_tmp, ignore_errors=True)

    def setUp(self):
        with self.Session() as db:
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=1, username="owner", nickname="一号", password_hash=hash_password("oldpass123")),
                User(id=2, username="peer", nickname="二号", password_hash="unused"),
                User(id=99, username="rootadmin", nickname="管理员", password_hash=hash_password("adminpass123"), role="admin"),
            ])
            db.commit()

    # ---------------- 辅助 ----------------
    def make_file(self, name: str) -> str:
        path = Path(settings.upload_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"img")
        return f"{settings.upload_url_prefix}/{name}"

    def file_exists(self, url: str) -> bool:
        return (Path(settings.upload_dir) / url.rsplit("/", 1)[-1]).exists()

    def login(self, username: str, password: str) -> int:
        return self.client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        ).status_code

    def add_ripple(self, ripple_id: int, user_id: int, images: list[str] | None = None, status="published"):
        with self.Session() as db:
            db.add(Ripple(id=ripple_id, user_id=user_id, content=f"内容{ripple_id}",
                          images=images or None, status=status))
            db.commit()

    # ---------------- 修改密码 ----------------
    def test_change_password_validates_and_switches_credential(self):
        path = "/api/v1/users/me/password"
        headers = self.headers(1)
        wrong = self.client.put(path, headers=headers,
                                json={"old_password": "nope", "new_password": "newpass123"})
        self.assertEqual(400, wrong.status_code)

        same = self.client.put(path, headers=headers,
                               json={"old_password": "oldpass123", "new_password": "oldpass123"})
        self.assertEqual(400, same.status_code)

        too_short = self.client.put(path, headers=headers,
                                    json={"old_password": "oldpass123", "new_password": "abc"})
        self.assertEqual(422, too_short.status_code)

        ok = self.client.put(path, headers=headers,
                             json={"old_password": "oldpass123", "new_password": "newpass123"})
        self.assertEqual(200, ok.status_code, ok.text)
        self.assertEqual(401, self.login("owner", "oldpass123"))
        self.assertEqual(200, self.login("owner", "newpass123"))
        # 改密码后用旧 token 仍可访问（JWT 不强制下线）
        self.assertEqual(200, self.client.get("/api/v1/users/me", headers=headers).status_code)

    # ---------------- 注销账号 ----------------
    def test_delete_account_requires_password_and_blocks_admin(self):
        path = "/api/v1/users/me/delete"
        self.assertEqual(400, self.client.post(path, headers=self.headers(1),
                                               json={"password": "wrong"}).status_code)
        with self.Session() as db:
            self.assertIsNotNone(db.get(User, 1))

        self.assertEqual(400, self.client.post(path, headers=self.headers(99),
                                               json={"password": "adminpass123"}).status_code)

    def test_delete_account_removes_content_and_avatar_files(self):
        avatar = self.make_file("avatar.png")
        img_a = self.make_file("a.png")
        img_b = self.make_file("b.png")
        shared = self.make_file("shared.png")
        with self.Session() as db:
            user = db.get(User, 1)
            user.avatar_url = avatar
            db.commit()
        self.add_ripple(1, 1, [img_a, img_b])
        self.add_ripple(2, 2, [shared])

        response = self.client.post("/api/v1/users/me/delete", headers=self.headers(1),
                                    json={"password": "oldpass123"})
        self.assertEqual(200, response.status_code, response.text)

        with self.Session() as db:
            self.assertIsNone(db.get(User, 1))
            self.assertIsNone(db.get(Ripple, 1))
            self.assertIsNotNone(db.get(Ripple, 2))

        self.assertEqual(401, self.client.get("/api/v1/users/me", headers=self.headers(1)).status_code)
        for url in (avatar, img_a, img_b):
            self.assertFalse(self.file_exists(url), url)
        self.assertTrue(self.file_exists(shared))

    # ---------------- 头像 / 配图清理 ----------------
    def test_replacing_avatar_deletes_old_file_unless_still_referenced(self):
        old = self.make_file("old-avatar.png")
        new = self.make_file("new-avatar.png")
        with self.Session() as db:
            db.get(User, 1).avatar_url = old
            db.commit()

        response = self.client.put("/api/v1/users/me", headers=self.headers(1),
                                   json={"avatar_url": new})
        self.assertEqual(200, response.status_code, response.text)
        self.assertFalse(self.file_exists(old))
        self.assertTrue(self.file_exists(new))

        # 同一张图仍被别人的微澜引用时不得删除
        old2 = self.make_file("old-avatar-2.png")
        self.add_ripple(3, 2, [old2])
        with self.Session() as db:
            db.get(User, 1).avatar_url = old2
            db.commit()
        self.client.put("/api/v1/users/me", headers=self.headers(1), json={"avatar_url": None})
        self.assertTrue(self.file_exists(old2))

    def test_editing_ripple_deletes_only_dropped_images(self):
        kept = self.make_file("keep.png")
        dropped = self.make_file("dropped.png")
        self.add_ripple(1, 1, [kept, dropped])

        response = self.client.put("/api/v1/ripples/1", headers=self.headers(1),
                                   json={"content": "改过的内容", "images": [kept]})
        self.assertEqual(200, response.status_code, response.text)
        self.assertFalse(self.file_exists(dropped))
        self.assertTrue(self.file_exists(kept))

    def test_deleting_content_cleans_images_but_keeps_shared_ones(self):
        own = self.make_file("own.png")
        shared = self.make_file("shared-content.png")
        self.add_ripple(1, 1, [own, shared])
        self.add_ripple(2, 2, [shared])

        self.assertEqual(204, self.client.delete("/api/v1/ripples/1", headers=self.headers(1)).status_code)
        self.assertFalse(self.file_exists(own))
        self.assertTrue(self.file_exists(shared))

    def test_admin_delete_also_cleans_files(self):
        image = self.make_file("admin-del.png")
        self.add_ripple(5, 2, [image])
        response = self.client.delete("/api/v1/admin/ripples/5", headers=self.headers(99))
        self.assertEqual(200, response.status_code, response.text)
        self.assertFalse(self.file_exists(image))

    # ---------------- 显式清理上传 ----------------
    def test_cleanup_endpoint_refuses_referenced_or_foreign_urls(self):
        orphan = self.make_file("orphan.png")
        used = self.make_file("used.png")
        self.add_ripple(4, 2, [used])

        ok = self.client.post("/api/v1/upload/cleanup", headers=self.headers(1),
                              json={"url": orphan})
        self.assertEqual(200, ok.status_code, ok.text)
        self.assertTrue(ok.json()["deleted"])
        self.assertFalse(self.file_exists(orphan))

        kept = self.client.post("/api/v1/upload/cleanup", headers=self.headers(1),
                                json={"url": used})
        self.assertEqual(200, kept.status_code)
        self.assertFalse(kept.json()["deleted"])
        self.assertTrue(self.file_exists(used))

        bad = self.client.post("/api/v1/upload/cleanup", headers=self.headers(1),
                               json={"url": "https://evil.example.com/x.png"})
        self.assertEqual(400, bad.status_code)
