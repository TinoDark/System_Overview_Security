"""Tenant-filtering repositories. Repositories never issue unscoped resource reads."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


class TenantRepository[T]:
    def __init__(self, model: type[T]):
        self.model = model

    def get(self, db: Session, organization_id: UUID, resource_id: UUID) -> T | None:
        return db.scalar(
            select(self.model).where(
                self.model.id == resource_id,
                self.model.organization_id == organization_id,
            )
        )

    def list(self, db: Session, organization_id: UUID, limit: int, offset: int = 0) -> list[T]:
        return list(
            db.scalars(
                select(self.model)
                .where(self.model.organization_id == organization_id)
                .order_by(self.model.id)
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def add(self, db: Session, entity: T) -> T:
        db.add(entity)
        return entity
