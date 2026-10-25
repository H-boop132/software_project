"""用固定时钟验证时间衰减与真正基于时间窗口的趋势。"""
from datetime import datetime, timedelta
import unittest

from app.models import Echo, Like, Ripple, Topic, User
from app.services.ripple_service import list_tides
from tests.mysql_test_case import MySQLIntegrationTestCase


class TideTests(MySQLIntegrationTestCase):
    database_tag = "tides"

    def setUp(self):
        self.now = datetime(2026, 10, 25, 12)
        with self.Session() as db:
            db.query(Echo).delete()
            db.query(Like).delete()
            db.query(Ripple).delete()
            db.query(Topic).delete()
            db.query(User).delete()
            db.add(User(id=1, username="tideuser", nickname="潮汐用户", password_hash="unused"))
            db.add_all([Topic(id=i, name=f"话题{i}", slug=f"topic{i}") for i in range(1, 4)])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=1, topic_id=1, content="现在", created_at=self.now),
                Ripple(id=2, user_id=1, topic_id=2, content="三天前", created_at=self.now - timedelta(hours=72)),
                Ripple(id=3, user_id=1, topic_id=3, content="前天", created_at=self.now - timedelta(hours=36)),
                Ripple(id=4, user_id=1, topic_id=1, content="下架", status="banned", created_at=self.now),
            ])
            db.commit()

    def items(self):
        with self.Session() as db:
            return {item.topic.id: item for item in list_tides(db, now=self.now)}

    def test_half_life_reduces_three_day_old_activity_by_half(self):
        items = self.items()
        self.assertEqual(items[1].heat, 10)
        self.assertEqual(items[2].heat, 5)
        self.assertEqual(items[1].ripple_count, 1)

    def test_trend_compares_previous_window_instead_of_other_topics(self):
        items = self.items()
        self.assertEqual((items[1].trend, items[1].recent_activity, items[1].previous_activity), ("↑", 10, 0))
        self.assertEqual((items[3].trend, items[3].recent_activity, items[3].previous_activity), ("↓", 0, 10))
        self.assertEqual(items[2].trend, "→")

    def test_new_reply_and_like_have_their_own_event_times(self):
        with self.Session() as db:
            db.add(Echo(root_ripple_id=2, user_id=1, content="老内容的新回复", created_at=self.now))
            db.add(Like(ripple_id=2, user_id=1, created_at=self.now))
            db.commit()
        item = self.items()[2]
        self.assertEqual((item.heat, item.recent_activity, item.trend), (12, 7, "↑"))


if __name__ == "__main__":
    unittest.main()
