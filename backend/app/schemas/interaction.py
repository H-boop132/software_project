"""互动操作返回当前状态，供列表与详情页同步。"""
from pydantic import BaseModel


class LikeOut(BaseModel):
    ripple_id: int
    is_liked: bool
    like_count: int
