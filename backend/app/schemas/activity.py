from datetime import date

from pydantic import BaseModel


class ActivityDay(BaseModel):
    date: date
    count: int


class AuthorActivity(BaseModel):
    start_date: date
    end_date: date
    published_count: int
    received_echoes: int
    received_likes: int
    days: list[ActivityDay]
