"""上传接口响应"""
from pydantic import BaseModel


class UploadOut(BaseModel):
    url: str
