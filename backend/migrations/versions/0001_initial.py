"""Initial tenant-scoped MVP schema.

Revision ID: 0001_initial
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid(as_uuid=True)
    json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "organizations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_key", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(30), nullable=False),
    )
    op.create_table(
        "assets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("hostname", sa.String(255)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("operating_system", sa.String(150)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_table(
        "integrations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("configuration", json, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "id", name="uq_integration_org_id"),
    )
    op.create_table(
        "events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("integration_id", uuid, nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("external_event_id", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("asset", json, nullable=False),
        sa.Column("actor", json),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("indicators", json, nullable=False),
        sa.Column("raw_event", json, nullable=False),
        sa.Column("risk_factors", json, nullable=False),
        sa.Column("is_simulated", sa.Boolean, nullable=False),
        sa.UniqueConstraint(
            "organization_id", "source", "external_event_id", name="uq_event_source_external"
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_event_org_id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "integration_id"],
            ["integrations.organization_id", "integrations.id"],
            name="fk_event_integration_same_org",
        ),
    )
    op.create_table(
        "incidents",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("risk_score", sa.Integer, nullable=False),
        sa.Column("risk_factors", json, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "id", name="uq_incident_org_id"),
    )
    op.create_table(
        "incident_events",
        sa.Column("organization_id", uuid, primary_key=True),
        sa.Column("incident_id", uuid, primary_key=True),
        sa.Column("event_id", uuid, primary_key=True),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_incident_event_incident_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "event_id"],
            ["events.organization_id", "events.id"],
            name="fk_incident_event_event_same_org",
        ),
    )
    op.create_table(
        "incident_comments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("incident_id", uuid, nullable=False),
        sa.Column("actor_user_id", uuid, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_incident_comment_incident_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_incident_comment_actor_member",
        ),
    )
    op.create_table(
        "policies",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("trigger_min_severity", sa.String(20)),
        sa.Column("trigger_min_score", sa.Integer),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "id", name="uq_policy_org_id"),
    )
    op.create_table(
        "responses",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("incident_id", uuid, nullable=False),
        sa.Column("policy_id", uuid, nullable=False),
        sa.Column("approval_id", uuid),
        sa.Column("requested_by", uuid, nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("simulated", sa.Boolean, nullable=False),
        sa.Column("result", json),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_response_incident_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "policy_id"],
            ["policies.organization_id", "policies.id"],
            name="fk_response_policy_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "requested_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_response_requester_member",
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_response_org_id"),
    )
    op.create_table(
        "approvals",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, nullable=False),
        sa.Column("incident_id", uuid, nullable=False),
        sa.Column("response_id", uuid, nullable=False),
        sa.Column("requested_by", uuid, nullable=False),
        sa.Column("decided_by", uuid),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("justification", sa.Text),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["incidents.organization_id", "incidents.id"],
            name="fk_approval_incident_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "response_id"],
            ["responses.organization_id", "responses.id"],
            name="fk_approval_response_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "requested_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_approval_requester_member",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "decided_by"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_approval_decider_member",
        ),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id")),
        sa.Column("actor_user_id", uuid, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(150), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("metadata", json, nullable=False),
        sa.Column("correlation_id", uuid),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table in (
        "assets",
        "integrations",
        "events",
        "incidents",
        "policies",
        "responses",
        "approvals",
    ):
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])


def downgrade() -> None:
    for table in (
        "audit_logs",
        "approvals",
        "responses",
        "policies",
        "incident_comments",
        "incident_events",
        "incidents",
        "events",
        "integrations",
        "assets",
        "memberships",
        "users",
        "organizations",
    ):
        op.drop_table(table)
