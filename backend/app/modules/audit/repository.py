from app.db.models import AuditLog, utcnow


class AuditRepository:
    def append(
        self,
        db,
        *,
        organization_id,
        actor_user_id,
        action,
        resource_type,
        resource_id,
        outcome,
        metadata,
        correlation_id,
    ):
        row = AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            outcome=outcome,
            metadata_json=metadata or {},
            correlation_id=correlation_id,
            created_at=utcnow(),
        )
        db.add(row)
        return row
