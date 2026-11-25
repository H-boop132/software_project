"""话题列表接口：GET /topics（全部话题，供发布页下拉等使用）"""
import unittest

from sqlalchemy import delete

from app.models import Topic, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class TopicListTest(MySQLIntegrationTestCase):
    database_tag = "topics"

    def setUp(self):
        with self.Session() as db:
            db.execute(delete(Topic))
            db.execute(delete(User))
            db.commit()
            db.add(User(id=1, username="tester", nickname="测试用户", password_hash="unused"))
            db.add_all([
                Topic(id=1, name="编程与灵感", slug="coding", description="代码里的顿悟时刻", heat_base=120),
                Topic(id=2, name="校园生活", slug="campus", description="图书馆、食堂与晚风", heat_base=80),
                Topic(id=3, name="读书偶得", slug="reading", description=None, heat_base=90),
            ])
            db.commit()

    def test_list_topics_is_public_and_ordered_by_id(self):
        """不登录也能拿到全部话题，按 id 升序，字段与 TopicOut 一致"""
        response = self.client.get("/api/v1/topics")
        self.assertEqual(200, response.status_code, response.text)
        data = response.json()
        self.assertEqual([1, 2, 3], [item["id"] for item in data])
        self.assertEqual(
            {"id", "name", "slug", "description"}, set(data[0])
        )
        self.assertEqual("编程与灵感", data[0]["name"])
        self.assertEqual("coding", data[0]["slug"])
        self.assertEqual("代码里的顿悟时刻", data[0]["description"])
        self.assertIsNone(data[2]["description"])

    def test_list_topics_empty(self):
        """没有任何话题时返回空数组而不是报错"""
        with self.Session() as db:
            db.execute(delete(Topic))
            db.execute(delete(User))
            db.commit()
        response = self.client.get("/api/v1/topics")
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual([], response.json())

    def test_topic_detail_route_not_shadowed(self):
        """新增列表路由后，/topics/{id} 详情与订阅路由仍需正常工作"""
        detail = self.client.get("/api/v1/topics/1", headers=self.headers())
        self.assertEqual(200, detail.status_code, detail.text)
        self.assertEqual("编程与灵感", detail.json()["name"])
        self.assertFalse(detail.json()["is_subscribed"])

        # 未登录仍应被订阅相关接口拦截
        self.assertEqual(401, self.client.get("/api/v1/topics/subscribed").status_code)


if __name__ == "__main__":
    unittest.main()
