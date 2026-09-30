"""认证相关请求/响应"""
from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="登录名，3-50字符")
    nickname: str = Field(min_length=1, max_length=50, description="昵称")
    password: str = Field(min_length=6, max_length=64, description="密码，≥6位")

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
