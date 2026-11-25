"""举报与申诉：用户提交、管理员处理、结果通知形成闭环。"""
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import Appeal, Notification, Report, Ripple, RippleReview, User
from app.schemas.report import (
    AppealHandleRequest, AppealOut, AppealPage, AppealCreate, ReportCreate,
    ReportHandleRequest, ReportOut, ReportPage,
)
from app.services.notification_service import notify_author
from app.services.ripple_service import lock_ripple


def _clean_note(note: str | None, fallback: str) -> str:
    return (note or "").strip()[:200] or fallback


def _notify(
    db: Session, recipient_id: int, actor_id: int, kind: str,
    note: str, ripple_id: int | None,
) -> None:
    if recipient_id == actor_id:
        return
    db.add(Notification(
        recipient_id=recipient_id, actor_id=actor_id, kind=kind,
        ripple_id=ripple_id, note=note[:200],
    ))


def _report_query(db: Session, report_id: int) -> ReportOut:
    reporter = aliased(User)
    author = aliased(User)
    row = db.execute(
        select(Report, reporter.nickname, Ripple.content, Ripple.status, author.id, author.nickname)
        .join(reporter, reporter.id == Report.reporter_id)
        .join(Ripple, Ripple.id == Report.ripple_id)
        .join(author, author.id == Ripple.user_id)
        .where(Report.id == report_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="举报不存在")
    report, reporter_name, content, ripple_status, author_id, author_name = row
    return ReportOut(
        id=report.id, ripple_id=report.ripple_id, reporter_id=report.reporter_id,
        reporter_name=reporter_name, reason_code=report.reason_code, detail=report.detail,
        status=report.status, handle_note=report.handle_note,
        created_at=report.created_at, handled_at=report.handled_at,
        ripple_content=content, ripple_status=ripple_status,
        author_id=author_id, author_name=author_name,
    )


def _appeal_query(db: Session, appeal_id: int) -> AppealOut:
    author = aliased(User)
    row = db.execute(
        select(Appeal, author.nickname, Ripple.content, Ripple.status, author.id, author.nickname)
        .join(author, author.id == Appeal.user_id)
        .join(Ripple, Ripple.id == Appeal.ripple_id)
        .where(Appeal.id == appeal_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="申诉不存在")
    appeal, user_name, content, ripple_status, author_id, author_name = row
    return AppealOut(
        id=appeal.id, ripple_id=appeal.ripple_id, user_id=appeal.user_id,
        user_name=user_name, reason=appeal.reason, status=appeal.status,
        handle_note=appeal.handle_note, created_at=appeal.created_at,
        handled_at=appeal.handled_at, ripple_content=content,
        ripple_status=ripple_status, author_id=author_id, author_name=author_name,
    )


def create_report(db: Session, reporter: User, ripple_id: int, data: ReportCreate) -> ReportOut:
    """只能举报公开微澜，不能举报自己的内容；同一用户同一内容只保留一条待处理举报。"""
    ripple = lock_ripple(db, ripple_id)
    if ripple.status != "published":
        raise HTTPException(status_code=400, detail="只能举报公开的微澜")
    if ripple.user_id == reporter.id:
        raise HTTPException(status_code=400, detail="不能举报自己的微澜")
    existing = db.scalar(select(Report.id).where(
        Report.reporter_id == reporter.id,
        Report.ripple_id == ripple_id,
        Report.status == "pending",
    ))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="你已举报过这条微澜，正在等待处理")
    report = Report(
        reporter_id=reporter.id, ripple_id=ripple_id,
        reason_code=data.reason_code, detail=data.detail,
    )
    db.add(report)
    db.commit()
    return _report_query(db, report.id)


def create_appeal(db: Session, user: User, ripple_id: int, data: AppealCreate) -> AppealOut:
    """仅作者可申诉已下架内容；同一微澜同时只允许一条待处理申诉。"""
    ripple = lock_ripple(db, ripple_id)
    if ripple.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能申诉自己的微澜")
    if ripple.status != "banned":
        raise HTTPException(status_code=400, detail="只有已下架的微澜可以申诉")
    existing = db.scalar(select(Appeal.id).where(
        Appeal.ripple_id == ripple_id, Appeal.status == "pending",
    ))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="这条微澜已有待处理的申诉")
    appeal = Appeal(user_id=user.id, ripple_id=ripple_id, reason=data.reason)
    db.add(appeal)
    db.commit()
    return _appeal_query(db, appeal.id)


def list_reports(
    db: Session, *, status_filter: str | None, limit: int, offset: int,
) -> ReportPage:
    stmt = select(Report.id).join(Ripple).join(User, User.id == Report.reporter_id)
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    ids = db.scalars(
        stmt.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit).offset(offset)
    ).all()
    return ReportPage(
        items=[_report_query(db, report_id) for report_id in ids],
        total=total, limit=limit, offset=offset,
    )


def list_appeals(
    db: Session, *, status_filter: str | None, limit: int, offset: int,
) -> AppealPage:
    stmt = select(Appeal.id).join(Ripple).join(User, User.id == Appeal.user_id)
    if status_filter:
        stmt = stmt.where(Appeal.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    ids = db.scalars(
        stmt.order_by(Appeal.created_at.desc(), Appeal.id.desc()).limit(limit).offset(offset)
    ).all()
    return AppealPage(
        items=[_appeal_query(db, appeal_id) for appeal_id in ids],
        total=total, limit=limit, offset=offset,
    )


def handle_report(
    db: Session, admin: User, report_id: int, data: ReportHandleRequest
) -> ReportOut:
    """处理举报：成立时下架内容并同步通知作者；结果通知举报人。"""
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="这条举报已处理")
    ripple = lock_ripple(db, report.ripple_id)

    now = datetime.now()
    if data.action == "uphold":
        note = _clean_note(data.note, "举报成立，内容已下架")
        newly_banned = ripple.status != "banned"
        if newly_banned:
            ripple.status = "banned"
            db.add(RippleReview(
                ripple_id=ripple.id, reviewer_id=admin.id, action="ban", reason=note
            ))
            notify_author(
                db, ripple.user_id, admin.id,
                f"你的微澜因举报被下架（仅你自己可见）。处理说明：{note}", ripple.id,
            )
        # 同一条内容的其它待处理举报一并结案，避免重复积压。
        pending = db.scalars(select(Report).where(
            Report.ripple_id == ripple.id, Report.status == "pending"
        )).all()
        for item in pending:
            item.status = "uphold"
            item.handler_id = admin.id
            item.handle_note = note
            item.handled_at = now
            _notify(
                db, item.reporter_id, admin.id, "report",
                f"你举报的微澜经核查成立，内容已下架。处理说明：{note}", ripple.id,
            )
    else:
        note = _clean_note(data.note, "经核查未发现违规")
        report.status = "dismissed"
        report.handler_id = admin.id
        report.handle_note = note
        report.handled_at = now
        _notify(
            db, report.reporter_id, admin.id, "report",
            f"你举报的微澜经核查未发现违规，举报已关闭。处理说明：{note}", ripple.id,
        )
    db.commit()
    return _report_query(db, report.id)


def handle_appeal(
    db: Session, admin: User, appeal_id: int, data: AppealHandleRequest
) -> AppealOut:
    """处理申诉：通过则恢复公开，驳回则维持下架；结果通知作者。"""
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="申诉不存在")
    if appeal.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="这条申诉已处理")
    ripple = lock_ripple(db, appeal.ripple_id)
    if ripple.status != "banned":
        raise HTTPException(status_code=400, detail="微澜当前不是已下架状态，无法处理该申诉")

    note = _clean_note(
        data.note,
        "申诉理由成立，内容恢复公开" if data.action == "approve" else "申诉理由不充分，维持下架",
    )
    if data.action == "approve":
        ripple.status = "published"
        db.add(RippleReview(
            ripple_id=ripple.id, reviewer_id=admin.id, action="appeal_approve", reason=note
        ))
        _notify(
            db, ripple.user_id, admin.id, "appeal",
            f"你的申诉已通过，微澜恢复公开。处理说明：{note}", ripple.id,
        )
        appeal.status = "approved"
    else:
        db.add(RippleReview(
            ripple_id=ripple.id, reviewer_id=admin.id, action="appeal_reject", reason=note
        ))
        _notify(
            db, ripple.user_id, admin.id, "appeal",
            f"你的申诉未通过，微澜维持下架。处理说明：{note}", ripple.id,
        )
        appeal.status = "rejected"
    appeal.handler_id = admin.id
    appeal.handle_note = note
    appeal.handled_at = datetime.now()
    db.commit()
    return _appeal_query(db, appeal.id)
