"""Thumbnail size, fallback, cache lifecycle and concurrent reads."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.core.storage import delete_upload, thumbnail_path
from app.main import app


class ThumbnailTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix="weilan_thumbnails_")
        self.addCleanup(directory.cleanup)
        previous = settings.upload_dir
        settings.upload_dir = directory.name
        self.addCleanup(setattr, settings, "upload_dir", previous)
        self.directory = Path(directory.name)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def image(self, name="sample.png", mode="RGB"):
        path = self.directory / name
        Image.new(mode, (960, 320), "#427363").save(path)
        return path

    def test_resize_preserves_original_and_reuses_cache(self):
        original = self.image()
        original_bytes = original.read_bytes()
        url = "/api/v1/upload/thumbnail/sample.png"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "image/webp")
        with Image.open(BytesIO(response.content)) as thumbnail:
            self.assertEqual(thumbnail.size, (640, 213))
        self.assertEqual(original.read_bytes(), original_bytes)
        cached = thumbnail_path(original)
        modified = cached.stat().st_mtime_ns
        again = self.client.get(url)
        self.assertEqual(again.content, response.content)
        self.assertEqual(cached.stat().st_mtime_ns, modified)

    def test_invalid_missing_and_animated_files_have_controlled_results(self):
        self.assertEqual(self.client.get("/api/v1/upload/thumbnail/missing.png").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/upload/thumbnail/..%5Csecret.png").status_code, 404)
        (self.directory / "invalid.png").write_bytes(b"invalid-image")
        response = self.client.get("/api/v1/upload/thumbnail/invalid.png", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/uploads/invalid.png")
        self.image("animated.gif")
        response = self.client.get("/api/v1/upload/thumbnail/animated.gif", follow_redirects=False)
        self.assertEqual(response.headers["location"], "/uploads/animated.gif")

    def test_concurrent_cache_builds_leave_one_complete_image(self):
        source = self.image()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.client.get("/api/v1/upload/thumbnail/sample.png"), range(4)))
        self.assertEqual([item.status_code for item in results], [200] * 4,
                         [(item.status_code, item.history) for item in results])
        self.assertTrue(all(item.content == results[0].content for item in results))
        self.assertEqual(list(thumbnail_path(source).parent.glob("*.tmp")), [])

    def test_cleanup_removes_cached_thumbnail(self):
        source = self.image()
        self.client.get("/api/v1/upload/thumbnail/sample.png")
        cache = thumbnail_path(source)
        self.assertTrue(cache.is_file())
        self.assertTrue(delete_upload("/uploads/sample.png"))
        self.assertFalse(source.exists())
        self.assertFalse(cache.exists())
        self.assertEqual(self.client.get("/api/v1/upload/thumbnail/sample.png").status_code, 404)
