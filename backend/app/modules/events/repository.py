from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.db.models import Event


class EventRepository:
    def insert_if_new(self, db: Session, event: Event) -> Event | None:
        values = {
            column.key: getattr(event, column.key) for column in inspect(event).mapper.column_attrs
        }
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            statement = (
                pg_insert(Event)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["organization_id", "source", "external_event_id"]
                )
            )
        elif dialect == "sqlite":
            statement = (
                sqlite_insert(Event)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["organization_id", "source", "external_event_id"]
                )
            )
        else:
            raise RuntimeError("Event idempotency is supported only on PostgreSQL and test SQLite")
        result = db.execute(statement)
        if result.rowcount == 0:
            return None
        return db.get(Event, event.id)

    def related_candidates(self, db: Session, organization_id, event_id, since, until):
        return db.scalars(
            select(Event).where(
                Event.organization_id == organization_id,
                Event.id != event_id,
                Event.occurred_at >= since,
                Event.occurred_at <= until,
            )
        ).all()
