"""举报与申诉的请求 / 响应模型"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ReportReason = Literal["spam", "abuse", "misinformation", "illegal", "other"]
ReportStatus = Literal["pending", "uphold", "dismissed"]
AppealStatus = Literal["pending", "approved", "rejected"]


class ReportCreate(BaseModel):
    reason_code: ReportReason
    detail: str | None = Field(default=None, max_length=200, description="补充说明")

    @field_validator("detail", mode="before")
    @classmethod
    def strip_detail(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ReportHandleRequest(BaseModel):
    action: Literal["uphold", "dismiss"]
    note: str | None = Field(default=None, max_length=200, description="处理说明，会通知举报人")


class ReportOut(BaseModel):
    id: int
    ripple_id: int
    reporter_id: int
    reporter_name: str
    reason_code: ReportReason
    detail: str | None = None
    status: ReportStatus
    handle_note: str | None = None
    created_at: datetime
    handled_at: datetime | None = None
    ripple_content: str
    ripple_status: str
    author_id: int
    author_name: str


class ReportPage(BaseModel):
    items: list[ReportOut]
    total: int
    limit: int
    offset: int


class AppealCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=200, description="申诉理由")

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class AppealHandleRequest(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=200, description="处理说明，会通知作者")


class AppealOut(BaseModel):
    id: int
    ripple_id: int
    user_id: int
    user_name: str
    reason: str
    status: AppealStatus
    handle_note: str | None = None
    created_at: datetime
    handled_at: datetime | None = None
    ripple_content: str
    ripple_status: str
    author_id: int
    author_name: str


class AppealPage(BaseModel):
    items: list[AppealOut]
    total: int
    limit: int
    offset: int


class AppealBriefOut(BaseModel):
    id: int
    status: AppealStatus
    reason: str
    handle_note: str | None = None
    created_at: datetime
    handled_at: datetime | None = None

    model_config = {"from_attributes": True}


class MyReportOut(BaseModel):
    id: int
    ripple_id: int
    reason_code: ReportReason
    detail: str | None
    status: ReportStatus
    handle_note: str | None
    created_at: datetime
    handled_at: datetime | None
    ripple_preview: str | None
    can_open: bool


class MyReportPage(BaseModel):
    items: list[MyReportOut]
    total: int
    limit: int
    offset: int


class MyAppealOut(AppealBriefOut):
    ripple_id: int
    ripple_preview: str | None
    can_open: bool


class MyAppealPage(BaseModel):
    items: list[MyAppealOut]
    total: int
    limit: int
    offset: int
