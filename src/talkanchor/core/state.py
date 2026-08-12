"""Persisted state: last known IP and the history of applied changes.

Backed by SQLite via SQLModel. Deliberately small — this is not a general
event store, just enough to (a) avoid acting on an IP we already applied and
(b) show a history/health view in the dashboard.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select


class ChangeEvent(SQLModel, table=True):
    __tablename__ = "change_events"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    old_ip: str | None = None
    new_ip: str = ""
    dry_run: bool = True
    apply_success: bool = False
    apply_message: str = ""
    backup_path: str | None = None
    health_ok: bool | None = None
    health_message: str = ""
    rolled_back: bool = False
    rollback_message: str = ""


class StateStore:
    """Thin wrapper around a SQLite-backed SQLModel engine."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{self._db_path}")
        SQLModel.metadata.create_all(self._engine)

    def get_last_known_ip(self) -> str | None:
        with Session(self._engine) as session:
            statement = (
                select(ChangeEvent)
                .where(ChangeEvent.apply_success == True)  # noqa: E712
                .order_by(ChangeEvent.created_at.desc())  # type: ignore[attr-defined]
                .limit(1)
            )
            event = session.exec(statement).first()
            return event.new_ip if event else None

    def record_change(self, event: ChangeEvent) -> ChangeEvent:
        with Session(self._engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def update_event(self, event: ChangeEvent) -> ChangeEvent:
        with Session(self._engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def recent_events(self, limit: int = 20) -> list[ChangeEvent]:
        with Session(self._engine) as session:
            statement = (
                select(ChangeEvent)
                .order_by(ChangeEvent.created_at.desc())  # type: ignore[attr-defined]
                .limit(limit)
            )
            return list(session.exec(statement).all())

    def last_change_at(self) -> datetime | None:
        with Session(self._engine) as session:
            statement = (
                select(ChangeEvent)
                .where(ChangeEvent.apply_success == True)  # noqa: E712
                .order_by(ChangeEvent.created_at.desc())  # type: ignore[attr-defined]
                .limit(1)
            )
            event = session.exec(statement).first()
            if event is None:
                return None
            # SQLite drops tzinfo on round-trip; created_at was always written as UTC.
            created_at = event.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            return created_at
