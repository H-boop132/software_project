"""潮汐接口：话题热度榜"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ripple import TideOut
from app.services import ripple_service

router = APIRouter()


@router.get("/hot", response_model=list[TideOut])
def hot_tides(db: Session = Depends(get_db)):
    return ripple_service.list_tides(db)
