from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.notification import NotificationKind, NotificationPage, UnreadCount
from app.services import notification_service

router = APIRouter()


@router.get("", response_model=NotificationPage)
def list_notifications(
    unread_only: bool = False, kind: NotificationKind | None = None,
    before: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return notification_service.list_messages(db, user.id, unread_only=unread_only,
                                              kind=kind, before=before, limit=limit)


@router.get("/unread-count", response_model=UnreadCount)
def unread_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UnreadCount(unread_count=notification_service.unread_count(db, user.id))


@router.put("/read-all", response_model=UnreadCount)
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UnreadCount(unread_count=notification_service.mark_read(db, user.id))


@router.put("/{message_id}/read", response_model=UnreadCount)
def read_notification(
    message_id: int = Path(gt=0), user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UnreadCount(unread_count=notification_service.mark_read(db, user.id, message_id))
