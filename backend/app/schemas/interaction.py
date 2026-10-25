"""互动操作返回当前状态，供列表与详情页同步。"""
from pydantic import BaseModel

from app.schemas.ripple import RippleOut


class LikeOut(BaseModel):
    ripple_id: int
    is_liked: bool
    like_count: int


class CollectionOut(BaseModel):
    ripple_id: int
    is_collected: bool


class CollectionPage(BaseModel):
    items: list[RippleOut]
    total: int
    limit: int
    offset: int
