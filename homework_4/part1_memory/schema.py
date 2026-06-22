# ─────────────────────────────────────────────────────────
# Part 1 · SQLAlchemy 2.0 schema (PostgreSQL)
# Three related ORM models in the modern Mapped[] / mapped_column style.
# ─────────────────────────────────────────────────────────
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, JSON, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base shared by all models."""
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # e.g. UUID
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    meta: Mapped[dict] = mapped_column(JSON, default=dict)          # 'metadata' is reserved in SQLAlchemy

    # 1:N — a session has many messages and many entities
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))                  # "user" / "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    session: Mapped["Session"] = relationship(back_populates="messages")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)     # indexed for fast lookup
    info: Mapped[dict] = mapped_column(JSON, default=dict)         # {type, facts: [...]}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    session: Mapped["Session"] = relationship(back_populates="entities")
