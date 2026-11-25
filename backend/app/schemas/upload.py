"""上传接口请求/响应"""
from pydantic import BaseModel, Field


class UploadOut(BaseModel):
    url: str


class UploadCleanupIn(BaseModel):
    url: str = Field(max_length=255, description="要清理的本站上传地址")


class UploadCleanupOut(BaseModel):
    deleted: bool
