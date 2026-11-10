from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_key: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(30))


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    asset_type: Mapped[str] = mapped_column(String(50))
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_integration_org_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    integration_type: Mapped[str] = mapped_column(String(50))
    configuration: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "source", "external_event_id", name="uq_event_source_external"
        ),
        UniqueConstraint("organization_id", "id", name="uq_event_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "integration_id"],
            ["integrations.organization_id", "integrations.id"],
            name="fk_event_integration_same_org",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    integration_id: Mapped[UUID] = mapped_column()
    source: Mapped[str] = mapped_column(String(30))
    external_event_id: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String(20))
    asset: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    actor: Mapped[dict | None] = mapped_column(JSON_VALUE, nullable=True)
    message: Mapped[str] = mapped_column(String(2000))
    indicators: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    raw_event: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    risk_factors: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_incident_org_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="new")
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_factors: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_incident_event_incident_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "event_id"],
            ["events.organization_id", "events.id"],
            name="fk_incident_event_event_same_org",
        ),
    )
    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(primary_key=True)


class IncidentComment(Base):
    __tablename__ = "incident_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_incident_comment_incident_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_incident_comment_actor_member",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    incident_id: Mapped[UUID] = mapped_column()
    actor_user_id: Mapped[UUID] = mapped_column()
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_policy_org_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_min_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trigger_min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), default="simulate_containment")


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_response_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_response_incident_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "policy_id"],
            ["policies.organization_id", "policies.id"],
            name="fk_response_policy_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "requested_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_response_requester_member",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    incident_id: Mapped[UUID] = mapped_column()
    policy_id: Mapped[UUID] = mapped_column()
    approval_id: Mapped[UUID | None] = mapped_column(nullable=True)
    requested_by: Mapped[UUID] = mapped_column()
    action_type: Mapped[str] = mapped_column(String(50), default="simulate_containment")
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    result: Mapped[dict | None] = mapped_column(JSON_VALUE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_approval_incident_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "response_id"],
            ["responses.organization_id", "responses.id"],
            name="fk_approval_response_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "requested_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_approval_requester_member",
        ),
        ForeignKeyConstraint(
            ["organization_id", "decided_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_approval_decider_member",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    incident_id: Mapped[UUID] = mapped_column()
    response_id: Mapped[UUID] = mapped_column()
    requested_by: Mapped[UUID] = mapped_column()
    decided_by: Mapped[UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(150))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(30))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON_VALUE, default=dict)
    correlation_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
