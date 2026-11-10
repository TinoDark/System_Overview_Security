"""Use-case layer. HTTP adapters call these services; no business rules live in routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.connectors.fixtures import CONNECTORS
from app.core.auth import MOCK_CATALOG, TenantContext, issue_token, permissions_for_role
from app.core.errors import APIError
from app.db.models import (
    Approval,
    Asset,
    Event,
    Incident,
    IncidentComment,
    IncidentEvent,
    Integration,
    Membership,
    Organization,
    Policy,
    Response,
    User,
    utcnow,
)
from app.db.repositories import TenantRepository
from app.modules.audit.repository import AuditRepository
from app.modules.correlation.scope import event_scope, matches_scope
from app.modules.detection.scoring import SEVERITY_ORDER, SEVERITY_SCORE, score_correlated
from app.modules.events.repository import EventRepository
from app.modules.responses.executor import simulate_containment
from app.schemas import NormalizedEventDTO

INCIDENT_SEVERITIES = {"high", "critical"}
event_repository = EventRepository()
audit_repository = AuditRepository()
ALLOWED_ROLES = {
    "super_admin": "super_admin",
    "security_admin": "security_admin",
    "admin": "security_admin",
    "analyst": "soc_analyst",
    "operator": "operator",
    "auditor": "auditor",
    "observer": "observer",
}


def audit(
    db: Session,
    tenant: TenantContext | None,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None,
    outcome: str = "success",
    metadata: dict | None = None,
) -> None:
    audit_repository.append(
        db,
        organization_id=tenant.organization_id if tenant else None,
        actor_user_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        metadata=metadata,
        correlation_id=uuid4(),
    )


def fixture_seed(db: Session) -> None:
    """Reproducible, idempotent demo data. No credentials or password material are stored."""
    org_a = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    org_b = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    if db.get(Organization, org_a) is None:
        db.add_all(
            [
                Organization(id=org_a, name="Demo Organization A", slug="demo-a", status="active"),
                Organization(id=org_b, name="Demo Organization B", slug="demo-b", status="active"),
            ]
        )
        db.flush()
    for user_key, (user_id_text, name, role_code) in __import__(
        "app.core.auth", fromlist=["MOCK_CATALOG"]
    ).MOCK_CATALOG.items():
        user_id = UUID(user_id_text)
        if db.get(User, user_id) is None:
            db.add(User(id=user_id, user_key=user_key, display_name=name, status="active"))
        db.flush()
        org_ids = (
            (org_a, org_b)
            if user_key == "super-admin"
            else (org_b if user_key.endswith("-b") else org_a,)
        )
        role = ALLOWED_ROLES[role_code]
        for org_id in org_ids:
            if db.get(Membership, (org_id, user_id)) is None:
                db.add(Membership(organization_id=org_id, user_id=user_id, role=role))
    for org_id, suffix, host, ip in (
        (org_a, "a", "srv-a.example.test", "192.0.2.10"),
        (org_b, "b", "srv-b.example.test", "198.51.100.10"),
    ):
        for provider in CONNECTORS:
            integ_id = UUID(
                f"{'a' if suffix == 'a' else 'b'}0000000-0000-4000-8000-00000000000{list(CONNECTORS).index(provider) + 1}"
            )
            if db.get(Integration, integ_id) is None:
                db.add(
                    Integration(
                        id=integ_id,
                        organization_id=org_id,
                        name=f"Mock {provider.title()} {suffix.upper()}",
                        integration_type=f"mock_{provider}",
                        configuration={},
                        status="active",
                    )
                )
        db.flush()
        asset_id = UUID(f"{'a' if suffix == 'a' else 'b'}0000000-0000-4000-8000-000000000099")
        if db.get(Asset, asset_id) is None:
            db.add(
                Asset(
                    id=asset_id,
                    organization_id=org_id,
                    name=f"Demo server {suffix.upper()}",
                    asset_type="server",
                    hostname=host,
                    ip_address=ip,
                    status="active",
                )
            )
    db.commit()


def login_demo_user(db: Session, user_key: str, enabled: bool, app_env: str) -> dict:
    if not enabled or app_env not in ("development", "test"):
        raise APIError(404, "NOT_FOUND", "Mock authentication is disabled")
    if user_key not in MOCK_CATALOG:
        raise APIError(401, "INVALID_DEMO_USER", "Unknown demo user")
    user = db.scalar(select(User).where(User.user_key == user_key, User.status == "active"))
    if user is None:
        raise APIError(
            503, "DEMO_FIXTURES_NOT_SEEDED", "Run the demo seed command before logging in"
        )
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user.id, Organization.status == "active")
    ).all()
    token = issue_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 28800,
        "is_simulated": True,
        "principal": {
            "user_id": str(user.id),
            "user_key": user.user_key,
            "display_name": user.display_name,
            "memberships": [
                {
                    "organization_id": str(m.organization_id),
                    "organization_name": org.name,
                    "role": m.role,
                    "permissions": permissions_for_role(m.role),
                }
                for m, org in memberships
            ],
            "permissions": sorted(
                {
                    permission
                    for membership, _ in memberships
                    for permission in permissions_for_role(membership.role)
                }
            ),
        },
    }


def tenant_organizations(db: Session, user_id: UUID) -> list[Organization]:
    return list(
        db.scalars(
            select(Organization)
            .join(Membership)
            .where(Membership.user_id == user_id, Organization.status == "active")
            .order_by(Organization.name)
        )
    )


def organization_details(db: Session, user_id: UUID, organization_id: UUID) -> Organization:
    row = db.scalar(
        select(Organization)
        .join(Membership)
        .where(
            Organization.id == organization_id,
            Membership.user_id == user_id,
            Organization.status == "active",
        )
    )
    if row is None:
        raise APIError(404, "NOT_FOUND", "Organization not found")
    return row


def create_asset(db: Session, tenant: TenantContext, values: dict) -> Asset:
    row = Asset(id=uuid4(), organization_id=tenant.organization_id, status="active", **values)
    db.add(row)
    audit(db, tenant, tenant.principal.id, "asset.created", "asset", row.id)
    db.commit()
    db.refresh(row)
    return row


def update_asset(db: Session, tenant: TenantContext, asset_id: UUID, values: dict) -> Asset:
    row = get_resource(db, Asset, asset_id, tenant)
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = utcnow()
    audit(db, tenant, tenant.principal.id, "asset.updated", "asset", row.id)
    db.commit()
    return row


def get_resource(db: Session, model, resource_id: UUID, tenant: TenantContext):
    row = TenantRepository(model).get(db, tenant.organization_id, resource_id)
    if row is None:
        raise APIError(404, "NOT_FOUND", "Resource not found")
    return row


def create_integration(
    db: Session, tenant: TenantContext, name: str, provider: str, configuration: dict
):
    # Fixture providers are not configurable by URL, secret, or other runtime option.
    if configuration:
        raise APIError(
            422, "INVALID_CONFIGURATION", "Fixture-only integrations accept no configuration"
        )
    row = Integration(
        id=uuid4(),
        organization_id=tenant.organization_id,
        name=name,
        integration_type=provider,
        configuration=configuration,
        status="active",
    )
    db.add(row)
    audit(db, tenant, tenant.principal.id, "integration.created", "integration", row.id)
    db.commit()
    db.refresh(row)
    return row


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _make_proposal(
    db: Session,
    tenant: TenantContext,
    incident: Incident,
    policy: Policy,
    idempotency_key: str | None = None,
) -> Response | None:
    key = (
        idempotency_key
        or f"{tenant.organization_id}:{incident.id}:{policy.id}:simulate_containment"
    )
    existing = db.scalar(select(Response).where(Response.idempotency_key == key))
    if existing:
        return existing
    response = Response(
        id=uuid4(),
        organization_id=tenant.organization_id,
        incident_id=incident.id,
        policy_id=policy.id,
        requested_by=tenant.principal.id,
        action_type="simulate_containment",
        status="proposed",
        idempotency_key=key,
        simulated=True,
        created_at=utcnow(),
    )
    db.add(response)
    db.flush()
    approval = Approval(
        id=uuid4(),
        organization_id=tenant.organization_id,
        incident_id=incident.id,
        response_id=response.id,
        requested_by=tenant.principal.id,
        status="pending",
        expires_at=utcnow() + timedelta(hours=24),
    )
    db.add(approval)
    db.flush()
    response.approval_id = approval.id
    audit(
        db,
        tenant,
        tenant.principal.id,
        "response.proposed",
        "response",
        response.id,
        metadata={"action_type": "simulate_containment", "simulated": True},
    )
    return response


def collect_integration(
    db: Session, tenant: TenantContext, integration_id: UUID, limit: int = 100
) -> dict:
    integration = get_resource(db, Integration, integration_id, tenant)
    if integration.status != "active":
        raise APIError(409, "INTEGRATION_DISABLED", "Integration is not active")
    provider = integration.integration_type.removeprefix("mock_")
    connector = CONNECTORS.get(provider)
    if connector is None:
        raise APIError(422, "UNSUPPORTED_CONNECTOR", "Only fixture connectors are supported")
    batch = connector.collect(limit=min(limit, 100))
    received, inserted, duplicates, incidents_created = len(batch["items"]), 0, 0, 0
    for raw in batch["items"]:
        normalized = connector.normalize(raw)
        connector.validate(normalized)
        normalized.update(
            {
                "event_id": uuid4(),
                "organization_id": tenant.organization_id,
                "integration_id": integration.id,
            }
        )
        dto = NormalizedEventDTO.model_validate(normalized)
        scope = event_scope(dto.model_dump(mode="json"))
        base = SEVERITY_SCORE[dto.severity]
        score = min(100, base)
        factors = [
            {
                "code": f"severity_{dto.severity}",
                "contribution": base,
                "explanation": f"Base severity score for {dto.severity}",
            }
        ]
        event = Event(
            id=dto.event_id,
            organization_id=tenant.organization_id,
            integration_id=integration.id,
            source=provider,
            external_event_id=dto.external_event_id,
            event_type=dto.event_type,
            occurred_at=dto.occurred_at,
            observed_at=dto.observed_at,
            severity=dto.severity,
            asset=dto.asset.model_dump(mode="json"),
            actor=dto.actor,
            message=dto.message,
            indicators=[item.model_dump() for item in dto.indicators],
            raw_event=dto.raw_event,
            risk_factors=factors,
            is_simulated=True,
        )
        stored_event = event_repository.insert_if_new(db, event)
        if stored_event is None:
            duplicates += 1
            continue
        event = stored_event
        inserted += 1
        # Correlate only with same-tenant events inside the fixed 15-minute window.
        since = dto.occurred_at - timedelta(minutes=15)
        candidates = event_repository.related_candidates(
            db, tenant.organization_id, event.id, since, dto.occurred_at
        )
        related = [
            candidate
            for candidate in candidates
            if matches_scope(
                scope, event_scope({"asset": candidate.asset, "indicators": candidate.indicators})
            )
        ]
        correlated = related + [event]
        unique_correlated = {item.id: item for item in correlated}.values()
        top_severity, score, factors = score_correlated(
            [item.severity for item in unique_correlated]
        )
        event.risk_factors = factors
        qualifies = top_severity in INCIDENT_SEVERITIES or score >= 60
        if qualifies:
            incident = None
            for candidate in related:
                linked = db.scalar(
                    select(Incident)
                    .join(IncidentEvent, IncidentEvent.incident_id == Incident.id)
                    .where(
                        IncidentEvent.event_id == candidate.id,
                        Incident.organization_id == tenant.organization_id,
                        Incident.status.in_(("new", "in_progress")),
                    )
                    .order_by(Incident.created_at.desc())
                )
                if linked:
                    incident = linked
                    break
            if incident:
                incident.risk_score = score
                incident.severity = top_severity
                incident.risk_factors = factors
                incident.updated_at = utcnow()
            else:
                incident = Incident(
                    id=uuid4(),
                    organization_id=tenant.organization_id,
                    title=f"{top_severity.title()} {dto.event_type.replace('_', ' ')}",
                    description=dto.message,
                    severity=top_severity,
                    status="new",
                    risk_score=score,
                    risk_factors=factors,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                db.add(incident)
                db.flush()
                incidents_created += 1
            # If a low-severity cluster only crosses the threshold now, link the earlier
            # correlated events as well, preserving the complete explanation chain.
            for correlated_event in correlated:
                if db.get(
                    IncidentEvent,
                    (tenant.organization_id, incident.id, correlated_event.id),
                ) is None:
                    db.add(
                        IncidentEvent(
                            organization_id=tenant.organization_id,
                            incident_id=incident.id,
                            event_id=correlated_event.id,
                        )
                    )
            # Make the newly linked cluster visible to subsequent events in this same batch.
            db.flush()
            policies = db.scalars(
                select(Policy).where(
                    Policy.organization_id == tenant.organization_id,
                    Policy.enabled.is_(True),
                    Policy.action_type == "simulate_containment",
                )
            ).all()
            for policy in policies:
                severity_ok = not policy.trigger_min_severity or (
                    SEVERITY_ORDER[incident.severity] >= SEVERITY_ORDER[policy.trigger_min_severity]
                )
                score_ok = policy.trigger_min_score is None or score >= policy.trigger_min_score
                if severity_ok and score_ok:
                    _make_proposal(db, tenant, incident, policy)
    audit(
        db,
        tenant,
        tenant.principal.id,
        "integration.collect",
        "integration",
        integration.id,
        metadata={
            "received": received,
            "inserted": inserted,
            "duplicates": duplicates,
            "is_simulated": True,
        },
    )
    db.commit()
    return {
        "run_id": str(uuid4()),
        "status": "completed",
        "received": received,
        "inserted": inserted,
        "duplicates": duplicates,
        "incidents_created": incidents_created,
        "is_simulated": True,
    }


def decide_approval(
    db: Session, tenant: TenantContext, approval_id: UUID, decision: str, justification: str
) -> Approval:
    row = db.scalar(
        select(Approval).where(
            Approval.id == approval_id, Approval.organization_id == tenant.organization_id
        )
    )
    if row is None:
        raise APIError(404, "NOT_FOUND", "Approval not found")
    now = utcnow()
    if row.status != "pending":
        raise APIError(409, "APPROVAL_ALREADY_DECIDED", "Approval is no longer pending")
    if _as_utc(row.expires_at) <= now:
        expired = db.execute(
            update(Approval)
            .where(
                Approval.id == approval_id,
                Approval.organization_id == tenant.organization_id,
                Approval.status == "pending",
            )
            .values(status="expired", decided_at=now)
        )
        db.commit()
        if expired.rowcount == 0:
            raise APIError(409, "APPROVAL_ALREADY_DECIDED", "Approval is no longer pending")
        raise APIError(409, "APPROVAL_EXPIRED", "Approval has expired")
    if row.requested_by == tenant.principal.id:
        raise APIError(403, "SEPARATION_OF_DUTIES", "Requester cannot decide their own approval")
    decision_result = db.execute(
        update(Approval)
        .where(
            Approval.id == approval_id,
            Approval.organization_id == tenant.organization_id,
            Approval.status == "pending",
            Approval.expires_at > now,
        )
        .values(
            status=decision,
            decided_by=tenant.principal.id,
            justification=justification,
            decided_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if decision_result.rowcount == 0:
        db.expire_all()
        current = db.scalar(
            select(Approval).where(
                Approval.id == approval_id,
                Approval.organization_id == tenant.organization_id,
            )
        )
        if current is None or current.status != "pending":
            raise APIError(409, "APPROVAL_ALREADY_DECIDED", "Approval is no longer pending")
        if _as_utc(current.expires_at) <= now:
            current.status = "expired"
            current.decided_at = now
            db.commit()
            raise APIError(409, "APPROVAL_EXPIRED", "Approval has expired")
        raise APIError(409, "APPROVAL_ALREADY_DECIDED", "Approval is no longer pending")
    response = db.scalar(
        select(Response).where(
            Response.id == row.response_id, Response.organization_id == tenant.organization_id
        )
    )
    if response:
        response.status = "approved" if decision == "approved" else "rejected"
    audit(db, tenant, tenant.principal.id, f"approval.{decision}", "approval", row.id)
    db.commit()
    db.refresh(row)
    return row


def execute_response(
    db: Session,
    tenant: TenantContext,
    response_id: UUID,
    responses_enabled: bool,
    idempotency_key: str,
) -> Response:
    response = db.scalar(
        select(Response).where(
            Response.id == response_id, Response.organization_id == tenant.organization_id
        )
    )
    if response is None:
        raise APIError(404, "NOT_FOUND", "Response not found")
    if not responses_enabled:
        raise APIError(409, "RESPONSES_DISABLED", "Response kill switch is off")
    if tenant.role not in ("operator", "security_admin", "super_admin"):
        raise APIError(403, "FORBIDDEN", "Role is not permitted to execute responses")
    if response.idempotency_key != idempotency_key:
        raise APIError(
            409, "IDEMPOTENCY_KEY_MISMATCH", "Idempotency key does not match the proposal"
        )
    if response.status == "simulated":
        return response
    policy = db.scalar(
        select(Policy).where(
            Policy.id == response.policy_id, Policy.organization_id == tenant.organization_id
        )
    )
    approval = db.scalar(
        select(Approval).where(
            Approval.id == response.approval_id, Approval.organization_id == tenant.organization_id
        )
    )
    if not policy or not policy.enabled or policy.action_type != "simulate_containment":
        raise APIError(409, "POLICY_NOT_ACTIVE", "An enabled simulation policy is required")
    if not approval or approval.status != "approved" or _as_utc(approval.expires_at) <= utcnow():
        raise APIError(409, "APPROVAL_REQUIRED", "A valid, approved decision is required")
    # This executor intentionally has no network, shell, or asset mutation capability.
    response.status = "simulated"
    response.result = simulate_containment()
    audit(
        db,
        tenant,
        tenant.principal.id,
        "response.executed",
        "response",
        response.id,
        metadata={"simulated": True, "verified": True, "action_type": "simulate_containment"},
    )
    db.commit()
    db.refresh(response)
    return response


def serialize(row) -> dict:
    from sqlalchemy.inspection import inspect

    values = {}
    for column in inspect(row).mapper.column_attrs:
        key = column.key
        value = getattr(row, key)
        if key == "metadata_json":
            key = "metadata"
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            value = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        values[key] = value
    return values


def list_rows(db: Session, model, tenant: TenantContext, limit: int, cursor: str | None):
    offset = 0
    if cursor:
        try:
            if len(cursor) > 128:
                raise ValueError()
            offset = int(cursor)
            if offset < 0:
                raise ValueError()
        except ValueError as exc:
            raise APIError(422, "INVALID_CURSOR", "Cursor is invalid") from exc
    rows = TenantRepository(model).list(db, tenant.organization_id, limit + 1, offset)
    has_more = len(rows) > limit
    rows = rows[:limit]
    return [serialize(row) for row in rows], str(offset + limit) if has_more else None


def search_events(
    db: Session,
    tenant: TenantContext,
    limit: int,
    cursor: str | None,
    source: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    asset_id: UUID | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
):
    offset = 0
    try:
        if cursor and len(cursor) > 128:
            raise ValueError()
        offset = int(cursor or 0)
    except ValueError as exc:
        raise APIError(422, "INVALID_CURSOR", "Cursor is invalid") from exc
    if offset < 0:
        raise APIError(422, "INVALID_CURSOR", "Cursor is invalid")
    if source and source not in CONNECTORS:
        raise APIError(422, "INVALID_SOURCE", "Unsupported event source")
    if from_time and to_time and from_time > to_time:
        raise APIError(422, "INVALID_TIME_RANGE", "from must be earlier than or equal to to")
    stmt = select(Event).where(Event.organization_id == tenant.organization_id)
    if source:
        stmt = stmt.where(Event.source == source)
    if severity:
        if severity not in SEVERITY_ORDER:
            raise APIError(422, "INVALID_SEVERITY", "Unsupported event severity")
        stmt = stmt.where(Event.severity == severity)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if from_time:
        stmt = stmt.where(Event.occurred_at >= from_time)
    if to_time:
        stmt = stmt.where(Event.occurred_at <= to_time)
    if asset_id:
        stmt = stmt.where(Event.asset["asset_id"].as_string() == str(asset_id))
    rows = db.scalars(stmt.order_by(Event.occurred_at.desc()).offset(offset).limit(limit + 1)).all()
    has_more = len(rows) > limit
    return rows[:limit], str(offset + limit) if has_more else None


def incident_details(db: Session, tenant: TenantContext, incident_id: UUID) -> dict:
    incident = get_resource(db, Incident, incident_id, tenant)
    event_ids = db.scalars(
        select(IncidentEvent.event_id).where(IncidentEvent.incident_id == incident.id)
    ).all()
    result = serialize(incident)
    result["event_ids"] = [str(event_id) for event_id in event_ids]
    comment_rows = db.execute(
        select(IncidentComment, User.display_name)
        .join(User, User.id == IncidentComment.actor_user_id)
        .where(
            IncidentComment.organization_id == tenant.organization_id,
            IncidentComment.incident_id == incident.id,
        )
        .order_by(IncidentComment.created_at)
    ).all()
    result["comments"] = [
        {**serialize(comment), "author": author} for comment, author in comment_rows
    ]
    response = db.scalar(
        select(Response)
        .where(
            Response.organization_id == tenant.organization_id,
            Response.incident_id == incident.id,
        )
        .order_by(Response.created_at.desc())
    )
    result["response_id"] = str(response.id) if response else None
    approval = None
    if response is not None:
        approval = db.scalar(
            select(Approval)
            .where(
                Approval.organization_id == tenant.organization_id,
                Approval.incident_id == incident.id,
                Approval.response_id == response.id,
            )
            .order_by(Approval.expires_at.desc())
        )
    result["approval"] = serialize(approval) if approval else None
    return result


def event_details(db: Session, tenant: TenantContext, event_id: UUID) -> Event:
    row = db.scalar(
        select(Event).where(Event.id == event_id, Event.organization_id == tenant.organization_id)
    )
    if row is None:
        raise APIError(404, "NOT_FOUND", "Event not found")
    return row


def change_incident_status(
    db: Session, tenant: TenantContext, incident_id: UUID, status: str, justification: str | None
) -> Incident:
    incident = get_resource(db, Incident, incident_id, tenant)
    transitions = {"new": "in_progress", "in_progress": "resolved", "resolved": "closed"}
    if transitions.get(incident.status) != status:
        raise APIError(
            409, "INVALID_STATUS_TRANSITION", "Incident status transition is not allowed"
        )
    incident.status = status
    incident.updated_at = utcnow()
    audit(
        db,
        tenant,
        tenant.principal.id,
        "incident.status_changed",
        "incident",
        incident.id,
        metadata={"status": status, "justification": justification},
    )
    db.commit()
    return incident


def add_incident_comment(
    db: Session, tenant: TenantContext, incident_id: UUID, body: str
) -> IncidentComment:
    incident = get_resource(db, Incident, incident_id, tenant)
    comment = IncidentComment(
        id=uuid4(),
        organization_id=tenant.organization_id,
        incident_id=incident.id,
        actor_user_id=tenant.principal.id,
        body=body,
        created_at=utcnow(),
    )
    db.add(comment)
    audit(
        db,
        tenant,
        tenant.principal.id,
        "incident.comment_added",
        "incident",
        incident.id,
        metadata={"comment_id": str(comment.id)},
    )
    db.commit()
    return comment


def create_policy(db: Session, tenant: TenantContext, values: dict) -> Policy:
    policy = Policy(id=uuid4(), organization_id=tenant.organization_id, **values)
    db.add(policy)
    audit(db, tenant, tenant.principal.id, "policy.created", "policy", policy.id)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(db: Session, tenant: TenantContext, policy_id: UUID, values: dict) -> Policy:
    policy = get_resource(db, Policy, policy_id, tenant)
    for key, value in values.items():
        setattr(policy, key, value)
    audit(db, tenant, tenant.principal.id, "policy.updated", "policy", policy.id)
    db.commit()
    return policy


def propose_response(
    db: Session, tenant: TenantContext, incident_id: UUID, policy_id: UUID, idempotency_key: str
) -> Response:
    incident = get_resource(db, Incident, incident_id, tenant)
    policy = db.scalar(
        select(Policy).where(
            Policy.id == policy_id, Policy.organization_id == tenant.organization_id
        )
    )
    if policy is None:
        raise APIError(404, "NOT_FOUND", "Policy not found")
    if not policy.enabled or policy.action_type != "simulate_containment":
        raise APIError(409, "POLICY_NOT_ACTIVE", "Enabled simulate_containment policy is required")
    prior = db.scalar(select(Response).where(Response.idempotency_key == idempotency_key))
    if prior:
        if prior.organization_id != tenant.organization_id:
            raise APIError(404, "NOT_FOUND", "Response not found")
        raise APIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key already used")
    response = _make_proposal(db, tenant, incident, policy, idempotency_key)
    if response is None:
        raise APIError(500, "PROPOSAL_FAILED", "Unable to propose response")
    db.commit()
    db.refresh(response)
    return response


def dry_run_response(db: Session, tenant: TenantContext, response_id: UUID) -> dict:
    response = db.scalar(
        select(Response).where(
            Response.id == response_id, Response.organization_id == tenant.organization_id
        )
    )
    if response is None:
        raise APIError(404, "NOT_FOUND", "Response not found")
    return {
        "response_id": str(response.id),
        "action_type": response.action_type,
        "status": "dry_run",
        "simulated": True,
        "external_effect": False,
    }


def dashboard_summary(db: Session, tenant: TenantContext) -> dict:
    organization_id = tenant.organization_id
    count = lambda model, *filters: (
        db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.organization_id == organization_id, *filters)
        )
        or 0
    )
    return {
        "events_total": count(Event),
        "events_24h": count(Event, Event.occurred_at >= utcnow() - timedelta(hours=24)),
        "incidents_open": count(Incident, Incident.status.in_(("new", "in_progress"))),
        "incidents_critical": count(Incident, Incident.severity == "critical"),
        "incidents_resolved": count(Incident, Incident.status.in_(("resolved", "closed"))),
        "approvals_pending": count(Approval, Approval.status == "pending"),
        "responses_simulated": count(Response, Response.status == "simulated"),
        "active_integrations": count(Integration, Integration.status == "active"),
        "total_assets": count(Asset, Asset.status == "active"),
        "is_simulated": True,
    }


def dashboard_timeline(db: Session, tenant: TenantContext, limit: int = 50) -> list[dict]:
    events = db.scalars(
        select(Event)
        .where(
            Event.organization_id == tenant.organization_id,
            Event.occurred_at >= utcnow() - timedelta(hours=24),
        )
        .order_by(Event.occurred_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(event.id),
            "label": event.event_type.replace("_", " "),
            "event_type": event.event_type,
            "timestamp": serialize(event)["occurred_at"],
            "severity": event.severity,
            "count": 1,
        }
        for event in events
    ]
