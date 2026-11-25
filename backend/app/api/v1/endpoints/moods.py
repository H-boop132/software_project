"""气象接口：全站情绪聚合 / 可选情绪色调。"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Emotion
from app.schemas.common import EmotionOut
from app.schemas.ripple import MoodOut
from app.services import ripple_service

router = APIRouter()


@router.get("/summary", response_model=list[MoodOut])
def mood_summary(db: Session = Depends(get_db)):
    return ripple_service.mood_summary(db)


@router.get("/tones", response_model=list[EmotionOut])
def mood_tones(db: Session = Depends(get_db)):
    """全部可选情绪色调（供资料编辑等下拉使用，不做统计）。"""
    return list(db.scalars(select(Emotion).order_by(Emotion.code)).all())
