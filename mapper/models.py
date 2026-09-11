from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mapper.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Instrument(Base):
    __tablename__ = "instruments"
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String, index=True)
    record: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EventMapping(Base):
    __tablename__ = "event_mappings"
    pmus_event_id: Mapped[str] = mapped_column(String, primary_key=True)
    record: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Outcome(Base):
    __tablename__ = "outcomes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    fields: Mapped[list] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String, index=True)
    event_id: Mapped[str | None] = mapped_column(String)
    event_series: Mapped[str | None] = mapped_column(String)
    instrument_product: Mapped[str | None] = mapped_column(String)
    market_sport_type: Mapped[str | None] = mapped_column(String)
    event_start_time: Mapped[str | None] = mapped_column(String)
    event_stage_reason: Mapped[str | None] = mapped_column(String)
    event_rung: Mapped[str | None] = mapped_column(String)
    sportradar_event_id: Mapped[str | None] = mapped_column(String)
    resolved: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String)
    rung: Mapped[str | None] = mapped_column(String)
    kalshi_ticker: Mapped[str | None] = mapped_column(String)
    side: Mapped[str | None] = mapped_column(String)


class TeamAlias(Base):
    __tablename__ = "team_aliases"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    labels: Mapped[list] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String, default="review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlayerAlias(Base):
    __tablename__ = "player_aliases"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    labels: Mapped[list] = mapped_column(JSON)


class Override(Base):
    __tablename__ = "overrides"
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    kalshi_ticker: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ReviewLog(Base):
    __tablename__ = "review_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_key: Mapped[str] = mapped_column(Text, unique=True)
    record: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
