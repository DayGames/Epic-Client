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
class MediaOut(BaseModel):
    id: int
    kind: str  # "image" or "video"

    class Config:
        from_attributes = True


class DlcOut(BaseModel):
    id: int
    name: str
    size_bytes: int

    class Config:
        from_attributes = True


class AppOut(BaseModel):
    id: int
    name: str
    description: str
    version: str
    size_bytes: int
    uploaded_at: datetime
    has_icon: bool = False
    owner_username: str = "unknown"
    media: list[MediaOut] = []
    dlc: list[DlcOut] = []

    class Config:
        from_attributes = True
