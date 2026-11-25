"""回声管理：点赞、删除时按既有外键一并清理子回复。"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.interaction import EchoLikeOut
from app.schemas.ripple import EchoDeleteOut
from app.services.echo_service import delete_echo
from app.services.interaction_service import set_echo_like

router = APIRouter()


@router.put("/{echo_id}/like", response_model=EchoLikeOut)
def like_echo(
    echo_id: int = Path(gt=0), user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return set_echo_like(db, user, echo_id, True)


@router.delete("/{echo_id}/like", response_model=EchoLikeOut)
def unlike_echo(
    echo_id: int = Path(gt=0), user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return set_echo_like(db, user, echo_id, False)


@router.delete("/{echo_id}", response_model=EchoDeleteOut)
def remove_echo(
    echo_id: int = Path(gt=0), user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_echo(db, user, echo_id)
