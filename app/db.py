"""
SQLAlchemy 2.0 models and session management. Matches the schema in
the PRD (section 5).

Tables are auto-created on startup via init_db() -- fine for an MVP.
Switch to Alembic migrations once the schema needs to change without
risking the data already in it.
"""
from datetime import datetime, timezone

from sqlalchemy import Float, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class CheckRecord(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_phone_hash: Mapped[str] = mapped_column(String(64), index=True)
    input_type: Mapped[str] = mapped_column(String(10))  # 'text' | 'image'
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str] = mapped_column(String(10))  # 'scam' | 'safe' | 'unsure'
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
