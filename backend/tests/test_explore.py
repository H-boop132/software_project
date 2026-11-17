"""探索组合筛选、排序与分页。"""
from datetime import datetime

from app.models import Echo, Emotion, Like, Ripple, Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class ExploreTests(MySQLIntegrationTestCase):
    database_tag = "explore"

    def test_filters_apply_before_sort_and_pagination(self):
        with self.Session() as db:
            db.add_all([
                User(id=1, username="explorer", nickname="探索者", password_hash="unused"),
                Topic(id=1, name="创意", slug="ideas"),
                Topic(id=2, name="其他", slug="other"),
                Emotion(code="calm", name="平静", color="#649688"),
            ])
            db.flush()
            timestamp = datetime(2026, 11, 17, 12)
            db.add_all([
                Ripple(id=i, user_id=1, topic_id=topic, emotion_code=mood, content=content,
                       status=status, images=images, created_at=timestamp)
                for i, topic, mood, content, status, images in [
                    (1, 1, "calm", "湖边的想法", "published", ["/uploads/a.jpg"]),
                    (2, 1, "calm", "湖边的回应", "published", ["/uploads/b.jpg"]),
                    (3, 1, "calm", "湖边无配图", "published", []),
                    (4, 1, "calm", "湖边未公开", "pending", ["/uploads/c.jpg"]),
                    (5, 2, "calm", "湖边另一话题", "published", ["/uploads/d.jpg"]),
                    (6, 1, None, "湖边无情绪", "published", ["/uploads/e.jpg"]),
                    (7, 1, "calm", "城里的想法", "published", ["/uploads/f.jpg"]),
                ]
            ])
            db.flush()
            db.add_all([
                Echo(root_ripple_id=1, user_id=1, content="一起讨论"),
                Echo(root_ripple_id=4, user_id=1, content="未公开"),
                Like(ripple_id=2, user_id=1),
            ])
            db.commit()

        def ids(**params):
            response = self.client.get("/api/v1/ripples", params={
                "topic_id": 1, "keyword": "湖边", "emotion_code": "calm", "has_images": True,
                **params,
            })
            self.assertEqual(response.status_code, 200, response.text)
            return [ripple["id"] for ripple in response.json()]

        self.assertEqual(ids(sort="discussed", limit=1), [1])
        self.assertEqual(ids(sort="discussed", limit=1, offset=1), [2])
        self.assertEqual(ids(sort="discussed", limit=1, offset=2), [])
        self.assertEqual(ids(sort="liked"), [2, 1])
        self.assertEqual(ids(sort="latest"), [2, 1])
