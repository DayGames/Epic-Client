"""Database tables (SQLAlchemy models)."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Integer, default=0)  # 1 = can upload apps
    created_at = Column(DateTime, default=datetime.utcnow)


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, default="")
    version = Column(String, default="1.0.0")
    # Filename stored on disk inside settings.files_dir (not the full path).
    filename = Column(String, nullable=False)
    # Optional icon image stored the same way; None if the app has no icon.
    icon_filename = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

    media = relationship("Media", cascade="all, delete-orphan", back_populates="app")
    dlc = relationship("Dlc", cascade="all, delete-orphan", back_populates="app")

    @property
    def has_icon(self) -> bool:
        """Convenience flag the API exposes so clients know whether to fetch an icon."""
        return bool(self.icon_filename)

    @property
    def owner_username(self) -> str:
        return self.owner.username if self.owner else "unknown"


class Media(Base):
    """A screenshot (image) or trailer (video) belonging to an app."""
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"))
    filename = Column(String, nullable=False)
    kind = Column(String, default="image")  # "image" or "video"

    app = relationship("App", back_populates="media")


class Dlc(Base):
    """Downloadable content for an app — just another .zip."""
    __tablename__ = "dlc"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"))
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    app = relationship("App", back_populates="dlc")
