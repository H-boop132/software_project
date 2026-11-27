"""本人统计的归属、时间边界与可见性。"""
from datetime import datetime, timedelta

from app.models import Echo, Like, Ripple, User
from app.services.activity_service import author_activity
from tests.mysql_test_case import MySQLIntegrationTestCase


class AuthorActivityTests(MySQLIntegrationTestCase):
    database_tag = "activity"

    def setUp(self):
        with self.Session() as db:
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=i, username=f"person{i}", nickname=f"用户{i}", password_hash="unused")
                for i in (1, 2)
            ])
            db.commit()

    def test_activity_is_authenticated_and_private(self):
        path = "/api/v1/users/me/activity"
        self.assertEqual(self.client.get(path).status_code, 401)
        with self.Session() as db:
            db.add(Ripple(user_id=1, content="我的记录"))
            db.commit()
        own = self.client.get(path, headers=self.headers(1))
        other = self.client.get(path, headers=self.headers(2))
        self.assertEqual(own.status_code, 200, own.text)
        self.assertEqual(own.json()["published_count"], 1)
        self.assertEqual(other.json()["published_count"], 0)
        self.assertEqual(len(own.json()["days"]), 30)

    def test_zero_filled_dates_public_status_and_received_interactions(self):
        now = datetime(2026, 11, 27, 12)
        first = datetime(2026, 10, 29)
        with self.Session() as db:
            db.add_all([
                Ripple(id=1, user_id=1, content="首日", created_at=first),
                Ripple(id=2, user_id=1, content="今天", created_at=now),
                Ripple(id=3, user_id=1, content="窗口外", created_at=first - timedelta(seconds=1)),
                Ripple(id=4, user_id=1, content="被下架", status="banned", created_at=now),
                Ripple(id=5, user_id=1, content="已删除", status="deleted", created_at=now),
                Ripple(id=6, user_id=2, content="别人的", created_at=now),
            ])
            db.flush()
            db.add_all([
                Like(user_id=2, ripple_id=1), Like(user_id=1, ripple_id=1),
                Like(user_id=2, ripple_id=4),
                Echo(user_id=2, root_ripple_id=1, content="收到回应"),
                Echo(user_id=1, root_ripple_id=1, content="自己的回应"),
                Echo(user_id=2, root_ripple_id=5, content="已删除内容的回应"),
            ])
            db.commit()
            activity = author_activity(db, db.get(User, 1), now=now)
        self.assertEqual(activity.published_count, 3)
        self.assertEqual((activity.received_likes, activity.received_echoes), (1, 1))
        self.assertEqual(str(activity.days[0].date), "2026-10-29")
        self.assertEqual(str(activity.days[-1].date), "2026-11-27")
        self.assertEqual(sum(item.count for item in activity.days), 2)
        self.assertEqual([activity.days[0].count, activity.days[1].count, activity.days[-1].count], [1, 0, 1])
