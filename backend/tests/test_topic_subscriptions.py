"""话题订阅与专属时间线的 MySQL 集成测试。"""
from app.models import Ripple, Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class TopicSubscriptionTests(MySQLIntegrationTestCase):
    database_tag = "topics"
    detail = "/api/v1/topics/1"
    subscription = f"{detail}/subscription"
    mine = "/api/v1/topics/subscribed"
    feed = "/api/v1/ripples/subscribed-topics"

    def setUp(self):
        with self.Session() as db:
            db.query(Ripple).delete()
            db.query(Topic).delete()
            db.query(User).delete()
            db.add_all([
                User(id=i, username=f"user{i}", nickname=f"用户{i}", password_hash="unused")
                for i in range(1, 3)
            ])
            db.add_all([Topic(id=i, slug=f"topic{i}", name=f"话题{i}") for i in range(1, 3)])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=2, topic_id=1, content="第一条想法"),
                Ripple(id=2, user_id=1, topic_id=1, content="第二条想法"),
                Ripple(id=3, user_id=1, topic_id=1, content="违规想法", status="banned"),
                Ripple(id=4, user_id=2, topic_id=2, content="其他话题"),
                Ripple(id=5, user_id=2, content="没有话题"),
            ])
            db.commit()

    def get_json(self, path, user=1, **params):
        response = self.client.get(path, headers=self.headers(user), params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_subscription_is_private_and_idempotent(self):
        self.assertEqual(self.client.put(self.subscription).status_code, 401)
        self.assertFalse(self.get_json(self.detail)["is_subscribed"])
        for _ in range(2):
            self.assertEqual(self.client.put(self.subscription, headers=self.headers(1)).status_code, 204)
        self.assertTrue(self.get_json(self.detail)["is_subscribed"])
        self.assertFalse(self.get_json(self.detail, user=2)["is_subscribed"])
        self.assertEqual([item["id"] for item in self.get_json(self.mine)], [1])
        self.assertEqual(self.get_json(self.mine, user=2), [])
        for _ in range(2):
            self.assertEqual(self.client.delete(self.subscription, headers=self.headers(1)).status_code, 204)
        self.assertFalse(self.get_json(self.detail)["is_subscribed"])
        self.assertEqual(self.get_json(self.mine), [])

    def test_feed_filters_paginates_and_omits_nonpublic_posts(self):
        self.assertEqual(self.client.get(self.feed).status_code, 401)
        self.assertEqual(self.get_json(self.feed), [])
        self.assertEqual(self.client.put(self.subscription, headers=self.headers(1)).status_code, 204)
        self.assertEqual([item["id"] for item in self.get_json(self.feed)], [2, 1])
        self.assertEqual(self.get_json(self.feed, topic_id=2), [])
        self.assertEqual(self.get_json(self.feed, user=2), [])
        self.assertEqual([item["id"] for item in self.get_json(self.feed, keyword="第一条")], [1])
        self.assertEqual([item["id"] for item in self.get_json(self.feed, limit=1, offset=1)], [1])
        self.client.delete(self.subscription, headers=self.headers(1))
        self.assertEqual(self.get_json(self.feed), [])

    def test_missing_topics_return_not_found(self):
        headers = self.headers(1)
        self.assertEqual(self.client.get("/api/v1/topics/100", headers=headers).status_code, 404)
        self.assertEqual(self.client.put("/api/v1/topics/100/subscription", headers=headers).status_code, 404)
