"""举报 + 申诉闭环：提交、权限、管理员处理、通知与审计。"""
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.models import Appeal, Notification, Report, Ripple, RippleReview, User
from tests.mysql_test_case import MySQLIntegrationTestCase


class ReportAppealTests(MySQLIntegrationTestCase):
    database_tag = "reports"

    def setUp(self):
        with self.Session() as db:
            db.query(Notification).delete()
            db.query(Report).delete()
            db.query(Appeal).delete()
            db.query(RippleReview).delete()
            db.query(Ripple).delete()
            db.query(User).delete()
            db.add_all([
                User(id=1, username="admin", nickname="管理员", password_hash="unused", role="admin"),
                User(id=2, username="alice", nickname="Alice", password_hash="unused"),
                User(id=3, username="bob", nickname="Bob", password_hash="unused"),
                User(id=4, username="carol", nickname="Carol", password_hash="unused"),
            ])
            db.flush()
            db.add_all([
                Ripple(id=1, user_id=2, content="Alice 的公开微澜", status="published"),
                Ripple(id=2, user_id=3, content="Bob 的被下架微澜", status="banned"),
                Ripple(id=3, user_id=3, content="Bob 的审核中微澜", status="pending"),
                Ripple(id=4, user_id=2, content="Alice 的另一条被下架微澜", status="banned"),
            ])
            db.commit()

    def post(self, path, user_id, payload=None):
        return self.client.post(
            path, json=payload or {}, headers=self.headers(user_id)
        )

    def notifications(self, user_id):
        with self.Session() as db:
            return db.query(Notification).filter(Notification.recipient_id == user_id).all()

    def report_count(self, ripple_id=1):
        with self.Session() as db:
            return db.query(Report).filter(Report.ripple_id == ripple_id).count()

    def test_my_history_is_private_filterable_and_hides_unavailable_content(self):
        first = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "abuse", "detail": "补充说明"}).json()
        self.post("/api/v1/ripples/1/report", 4, {"reason_code": "spam"})
        path = "/api/v1/users/me/reports"
        self.assertEqual(self.client.get(path).status_code, 401)
        mine = self.client.get(path, headers=self.headers(3)).json()
        self.assertEqual((mine["total"], mine["items"][0]["id"]), (1, first["id"]))
        self.assertNotIn("reporter_name", mine["items"][0])
        self.post(f"/api/v1/admin/reports/{first['id']}/handle", 1, {"action": "uphold"})
        hidden = self.client.get(path, headers=self.headers(3), params={"status": "uphold"}).json()
        self.assertIsNone(hidden["items"][0]["ripple_preview"])
        self.assertFalse(hidden["items"][0]["can_open"])
        self.assertEqual(self.client.get(path, headers=self.headers(2)).json()["total"], 0)
        self.assertEqual(self.client.get(path, headers=self.headers(3), params={"status": "pending"}).json()["items"], [])

    def test_my_appeals_preserve_own_reason_and_handle_result(self):
        appeal = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "申请复核"}).json()
        path = "/api/v1/users/me/appeals"
        own = self.client.get(path, headers=self.headers(3)).json()
        self.assertEqual((own["total"], own["items"][0]["reason"]), (1, "申请复核"))
        self.assertTrue(own["items"][0]["can_open"])
        self.assertEqual(self.client.get(path, headers=self.headers(2)).json()["items"], [])
        self.post(f"/api/v1/admin/appeals/{appeal['id']}/handle", 1, {"action": "reject", "note": "请补充信息"})
        history = self.client.get(path, headers=self.headers(3), params={"status": "rejected", "limit": 1}).json()
        self.assertEqual(history["items"][0]["handle_note"], "请补充信息")

    def test_my_records_paginate_after_multiple_submissions(self):
        first = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "abuse"}).json()
        self.post(f"/api/v1/admin/reports/{first['id']}/handle", 1, {"action": "dismiss"})
        second = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "other"}).json()
        path = "/api/v1/users/me/reports"
        current = self.client.get(path, headers=self.headers(3), params={"limit": 1}).json()
        previous = self.client.get(path, headers=self.headers(3), params={"limit": 1, "offset": 1}).json()
        self.assertEqual(current["total"], 2)
        self.assertEqual([item["id"] for item in current["items"]], [second["id"]])
        self.assertEqual([item["id"] for item in previous["items"]], [first["id"]])

    def test_concurrent_report_and_appeal_handling_notifies_once(self):
        report = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "abuse"}).json()
        appeal = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "申请复核"}).json()
        for path, payload, recipient, kind in [
            (f"/api/v1/admin/reports/{report['id']}/handle", {"action": "dismiss"}, 3, "report"),
            (f"/api/v1/admin/appeals/{appeal['id']}/handle", {"action": "reject"}, 3, "appeal"),
        ]:
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(lambda _: self.post(path, 1, payload), range(4)))
            self.assertEqual(sorted(item.status_code for item in responses), [200, 409, 409, 409])
            self.assertEqual(len([item for item in self.notifications(recipient) if item.kind == kind]), 1)

    def test_deleted_content_can_be_closed_without_restoring_it(self):
        report = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "abuse"}).json()
        appeal = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "申请复核"}).json()
        self.client.delete("/api/v1/ripples/1", headers=self.headers(2))
        self.client.delete("/api/v1/ripples/2", headers=self.headers(3))
        close_report = self.post(f"/api/v1/admin/reports/{report['id']}/handle", 1, {"action": "dismiss"})
        close_appeal = self.post(f"/api/v1/admin/appeals/{appeal['id']}/handle", 1, {"action": "reject"})
        self.assertEqual(close_report.status_code, 200, close_report.text)
        self.assertEqual(close_appeal.status_code, 200, close_appeal.text)
        with self.Session() as db:
            self.assertEqual(db.get(Ripple, 1).status, "deleted")
            self.assertEqual(db.get(Ripple, 2).status, "deleted")

    # ---------- 举报 ----------
    def test_only_published_and_not_own_can_be_reported(self):
        own = self.post("/api/v1/ripples/1/report", 2, {"reason_code": "spam"})
        self.assertEqual(own.status_code, 400, own.text)
        pending = self.post("/api/v1/ripples/3/report", 2, {"reason_code": "spam"})
        self.assertEqual(pending.status_code, 400, pending.text)
        banned = self.post("/api/v1/ripples/2/report", 2, {"reason_code": "spam"})
        self.assertEqual(banned.status_code, 400, banned.text)

    def test_duplicate_pending_report_is_rejected_but_dismissed_can_report_again(self):
        first = self.post("/api/v1/ripples/1/report", 3, {
            "reason_code": "abuse", "detail": "带攻击性的表达",
        })
        self.assertEqual(first.status_code, 201, first.text)
        duplicate = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "spam"})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        other = self.post("/api/v1/ripples/1/report", 4, {"reason_code": "other"})
        self.assertEqual(other.status_code, 201, other.text)
        self.assertEqual(self.report_count(), 2)

    def test_invalid_reason_is_422(self):
        response = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "unknown"})
        self.assertEqual(response.status_code, 422, response.text)

    def test_uphold_bans_content_closes_all_reports_and_notifies_both_sides(self):
        first = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "abuse"}).json()
        second = self.post("/api/v1/ripples/1/report", 4, {"reason_code": "spam"}).json()
        response = self.post(f"/api/v1/admin/reports/{first['id']}/handle", 1, {
            "action": "uphold", "note": "内容确有攻击性",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "uphold")
        self.assertEqual(body["handle_note"], "内容确有攻击性")
        with self.Session() as db:
            ripple = db.get(Ripple, 1)
            self.assertEqual(ripple.status, "banned")
            reports = db.query(Report).filter(Report.ripple_id == 1).all()
            self.assertEqual({item.status for item in reports}, {"uphold"})
            review = db.query(RippleReview).filter(RippleReview.ripple_id == 1).one()
            self.assertEqual(review.action, "ban")
            self.assertEqual(review.reason, "内容确有攻击性")
        reporter_messages = [item for item in self.notifications(3) if item.kind == "report"]
        self.assertEqual(len(reporter_messages), 1)
        self.assertIn("举报", reporter_messages[0].note)
        author_messages = [item for item in self.notifications(2) if item.kind == "moderation"]
        self.assertEqual(len(author_messages), 1)
        self.assertIn("举报", author_messages[0].note)
        self.assertEqual(second["status"], "pending")

    def test_dismiss_keeps_content_and_notifies_reporter_only(self):
        report = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "misinformation"}).json()
        response = self.post(f"/api/v1/admin/reports/{report['id']}/handle", 1, {
            "action": "dismiss", "note": "未发现不实信息",
        })
        self.assertEqual(response.status_code, 200, response.text)
        with self.Session() as db:
            self.assertEqual(db.get(Ripple, 1).status, "published")
            self.assertEqual(db.get(Report, report["id"]).status, "dismissed")
            self.assertEqual(db.query(RippleReview).count(), 0)
        messages = [item for item in self.notifications(3) if item.kind == "report"]
        self.assertEqual(len(messages), 1)
        self.assertIn("未发现违规", messages[0].note)
        self.assertEqual(self.notifications(2), [])

    def test_handled_report_cannot_be_handled_twice(self):
        report = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "spam"}).json()
        self.post(f"/api/v1/admin/reports/{report['id']}/handle", 1, {"action": "dismiss"})
        again = self.post(f"/api/v1/admin/reports/{report['id']}/handle", 1, {"action": "uphold"})
        self.assertEqual(again.status_code, 409, again.text)

    # ---------- 申诉 ----------
    def test_only_author_of_banned_ripple_can_appeal(self):
        not_author = self.post("/api/v1/ripples/2/appeal", 2, {"reason": "我觉得没问题"})
        self.assertEqual(not_author.status_code, 403, not_author.text)
        published = self.post("/api/v1/ripples/1/appeal", 2, {"reason": "测试"})
        self.assertEqual(published.status_code, 400, published.text)
        pending = self.post("/api/v1/ripples/3/appeal", 3, {"reason": "测试"})
        self.assertEqual(pending.status_code, 400, pending.text)
        empty = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "   "})
        self.assertEqual(empty.status_code, 422, empty.text)

    def test_duplicate_pending_appeal_and_reappeal_after_reject(self):
        first = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "引用来源已标注"})
        self.assertEqual(first.status_code, 201, first.text)
        duplicate = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "再试一次"})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        handled = self.post(f"/api/v1/admin/appeals/{first.json()['id']}/handle", 1, {
            "action": "reject", "note": "仍不符合社区规范",
        })
        self.assertEqual(handled.status_code, 200, handled.text)
        again = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "补充了来源"})
        self.assertEqual(again.status_code, 201, again.text)

    def test_approve_restores_public_and_writes_audit_and_notice(self):
        appeal = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "这是正常讨论"}).json()
        response = self.post(f"/api/v1/admin/appeals/{appeal['id']}/handle", 1, {
            "action": "approve", "note": "复核后恢复",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "approved")
        with self.Session() as db:
            self.assertEqual(db.get(Ripple, 2).status, "published")
            review = db.query(RippleReview).filter(RippleReview.ripple_id == 2).one()
            self.assertEqual(review.action, "appeal_approve")
            self.assertEqual(review.reason, "复核后恢复")
        messages = [item for item in self.notifications(3) if item.kind == "appeal"]
        self.assertEqual(len(messages), 1)
        self.assertIn("恢复公开", messages[0].note)
        # 申诉理由只对作者可见，公开后的普通访客不应读到处理详情。
        visitor = self.client.get("/api/v1/ripples/2", headers=self.headers(4))
        self.assertEqual(visitor.status_code, 200, visitor.text)
        self.assertIsNone(visitor.json()["latest_appeal"])
        author = self.client.get("/api/v1/ripples/2", headers=self.headers(3))
        self.assertEqual(author.json()["latest_appeal"]["status"], "approved")

    def test_reject_keeps_banned_and_notifies_author(self):
        appeal = self.post("/api/v1/ripples/4/appeal", 2, {"reason": "我认为可以恢复"}).json()
        response = self.post(f"/api/v1/admin/appeals/{appeal['id']}/handle", 1, {
            "action": "reject", "note": "维持下架",
        })
        self.assertEqual(response.status_code, 200, response.text)
        with self.Session() as db:
            self.assertEqual(db.get(Ripple, 4).status, "banned")
            review = db.query(RippleReview).filter(RippleReview.ripple_id == 4).one()
            self.assertEqual(review.action, "appeal_reject")
        messages = [item for item in self.notifications(2) if item.kind == "appeal"]
        self.assertEqual(len(messages), 1)
        self.assertIn("维持下架", messages[0].note)

    # ---------- 详情与统计 ----------
    def test_detail_exposes_report_and_appeal_state(self):
        self.post("/api/v1/ripples/1/report", 3, {"reason_code": "other"})
        detail = self.client.get("/api/v1/ripples/1", headers=self.headers(3))
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["report_status"], "pending")
        self.post("/api/v1/ripples/2/appeal", 3, {"reason": "申请复核"})
        own_detail = self.client.get("/api/v1/ripples/2", headers=self.headers(3))
        self.assertEqual(own_detail.status_code, 200, own_detail.text)
        self.assertEqual(own_detail.json()["latest_appeal"]["status"], "pending")
        mine = self.client.get("/api/v1/ripples/mine", headers=self.headers(3))
        self.assertEqual(mine.status_code, 200, mine.text)
        row = next(item for item in mine.json() if item["id"] == 2)
        self.assertEqual(row["latest_appeal"]["status"], "pending")

    def test_admin_stats_include_pending_counts(self):
        report = self.post("/api/v1/ripples/1/report", 3, {"reason_code": "spam"}).json()
        appeal = self.post("/api/v1/ripples/2/appeal", 3, {"reason": "申请复核"}).json()
        self.assertIsInstance(report["id"], int)
        self.assertIsInstance(appeal["id"], int)
        stats = self.client.get("/api/v1/admin/stats", headers=self.headers(1)).json()
        self.assertEqual(stats["pending_reports"], 1)
        self.assertEqual(stats["pending_appeals"], 1)

    def test_normal_user_cannot_read_admin_queues(self):
        response = self.client.get("/api/v1/admin/reports", headers=self.headers(2))
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
