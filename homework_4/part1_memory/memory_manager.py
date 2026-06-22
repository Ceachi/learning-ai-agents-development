# ─────────────────────────────────────────────────────────
# Part 1 · Memory Manager — Repository pattern + transaction
# Separates persistence (repository) from business logic (manager).
# ─────────────────────────────────────────────────────────
from contextlib import contextmanager
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession, sessionmaker
from part1_memory.schema import ChatMessage, Session


# ── Unit of Work: one transaction = one context. Commit on success, rollback on error.
@contextmanager
def unit_of_work(session_factory: sessionmaker):
    db: DBSession = session_factory()
    try:
        yield db
        db.commit()              # everything succeeded → atomic persist
    except Exception:
        db.rollback()            # something failed → cancel everything
        raise
    finally:
        db.close()


# ── Repository: session rows. chat_messages has a FK to sessions.id, so the
#    parent session must exist before any message is inserted.
class SessionRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def ensure(self, session_id: str, user_id: str | None = None) -> Session:
        """Get-or-create the session row (idempotent)."""
        existing = self.db.get(Session, session_id)
        if existing is not None:
            return existing
        # user_id is NOT NULL in the schema; default to the session_id itself
        # when the caller doesn't track a separate user.
        sess = Session(id=session_id, user_id=user_id or session_id)
        self.db.add(sess)
        return sess


# ── Repository: ALL DB logic for messages, isolated here.
#    Business logic never sees SQL/ORM directly.
class ChatMessageRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def add(self, session_id: str, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        return msg

    def latest(self, session_id: str, limit: int) -> list[ChatMessage]:
        # ORDER BY timestamp DESC + LIMIT N  → last N (window)
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            # id as tiebreaker: messages written in the same second have
            # identical timestamps; auto-increment id guarantees real order.
            .order_by(ChatMessage.timestamp.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).scalars().all()
        return list(reversed(rows))      # reverse → chronological for the LLM


# ── Manager: clean API for the rest of the app. Doesn't know about SQL.
class PersistentMemory:
    def __init__(self, session_factory: sessionmaker, window: int = 10):
        self.session_factory = session_factory
        self.window = window

    def load_messages(self, session_id: str) -> list[dict]:
        with unit_of_work(self.session_factory) as db:
            rows = ChatMessageRepository(db).latest(session_id, self.window)
            return [{"role": m.role, "content": m.content} for m in rows]

    def save_message(self, session_id: str, role: str, content: str) -> None:
        with unit_of_work(self.session_factory) as db:     # atomic transaction
            # Ensure the parent session exists first (FK: chat_messages → sessions).
            SessionRepository(db).ensure(session_id)
            ChatMessageRepository(db).add(session_id, role, content)
