"""应用配置：从 .env / 环境变量读取"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "微澜 Microripple"
    debug: bool = True

    database_url: str = (
        "mysql+pymysql://root:你的密码@127.0.0.1:3306/weilan?charset=utf8mb4"
    )

    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    # 配图上传目录（相对 backend 运行目录）与访问前缀
    upload_dir: str = "uploads"
    upload_url_prefix: str = "/uploads"
    upload_max_size_mb: int = 5

    # 允许跨域的前端地址
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
