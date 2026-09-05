"""Pydantic schemas: the shape of data going in/out of the API."""
from datetime import datetime
from pydantic import BaseModel


# ---- Users / auth ----
class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Apps ----
class AppOut(BaseModel):
    id: int
    name: str
    description: str
    version: str
    size_bytes: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
