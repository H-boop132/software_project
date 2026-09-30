"""气象接口：全站情绪聚合"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ripple import MoodOut
from app.services import ripple_service

router = APIRouter()


@router.get("/summary", response_model=list[MoodOut])
def mood_summary(db: Session = Depends(get_db)):
    return ripple_service.mood_summary(db)
