import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.connectors.fixtures import CONNECTORS, RESOURCE_FOR_PROVIDER
from app.core.auth import (
    Principal,
    TenantContext,
    get_principal,
    get_tenant,
    invalidate_token,
    require_roles,
)
from app.core.errors import APIError
from app.db.models import (
    Approval,
    Asset,
    AuditLog,
    Event,
    Incident,
    Integration,
    Policy,
    Response,
)
from app.db.session import get_db as default_get_db
from app.schemas import (
    APIEnvelope,
    ApprovalDecision,
    ApprovalDTO,
    AssetCreate,
    AssetPatch,
    CommentCreate,
    IncidentDTO,
    IncidentStatusChange,
    IntegrationCreate,
    MockLogin,
    PolicyCreate,
    PolicyDTO,
    PolicyPatch,
    ResponseCreate,
    ResponseDTO,
)
from app.services import (
    add_incident_comment,
    change_incident_status,
    collect_integration,
    create_asset,
    create_integration,
    create_policy,
    decide_approval,
    dry_run_response,
    event_details,
    execute_response,
    get_resource,
    incident_details,
    list_rows,
    login_demo_user,
    organization_details,
    propose_response,
    search_events,
    serialize,
    tenant_organizations,
    update_asset,
    update_policy,
)
from app.services import (
    dashboard_summary as get_dashboard_summary,
)
from app.services import (
    dashboard_timeline as get_dashboard_timeline,
)

router = APIRouter()


def success(request: Request, data, **meta):
    values = {"request_id": str(getattr(request.state, "request_id", uuid4()))}
    values.update(meta)
    return {"data": data, "meta": values}


def role_any(*roles: str):
    return require_roles(*roles)


def _event_dict(row: Event):
    return {
        "event_id": str(row.id),
        "organization_id": str(row.organization_id),
        "source": row.source,
        "integration_id": str(row.integration_id),
        "external_event_id": row.external_event_id,
        "event_type": row.event_type,
        "occurred_at": serialize(row)["occurred_at"],
        "observed_at": serialize(row)["observed_at"],
        "severity": row.severity,
        "asset": row.asset,
        "actor": row.actor,
        "message": row.message,
        "indicators": row.indicators,
        "raw_event": row.raw_event,
        "risk_factors": row.risk_factors,
        "schema_version": "1.0",
        "is_simulated": row.is_simulated,
    }


def _integration_dict(values: dict) -> dict:
    return {**values, "is_simulated": True}


@router.post("/auth/mock-login")
def mock_login(body: MockLogin, request: Request, db: Session = Depends(default_get_db)):
    config = request.app.state.config
    return success(
        request, login_demo_user(db, body.user_key, config.mock_auth_enabled, config.app_env)
    )


@router.get("/auth/me")
def auth_me(request: Request, principal: Principal = Depends(get_principal)):
    return success(
        request,
        {
            "user_id": str(principal.id),
            "user_key": principal.user_key,
            "display_name": principal.display_name,
            "memberships": list(principal.memberships),
            "permissions": sorted(
                {
                    permission
                    for membership in principal.memberships
                    for permission in membership["permissions"]
                }
            ),
        },
    )


@router.post("/auth/mock-logout")
def mock_logout(
    request: Request,
    authorization: str = Header(alias="Authorization"),
    principal: Principal = Depends(get_principal),
):
    invalidate_token(authorization.removeprefix("Bearer ").strip())
    return success(request, {"status": "logged_out"})


@router.get("/organizations")
def organizations(
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(default_get_db),
):
    return success(request, [serialize(row) for row in tenant_organizations(db, principal.id)])


@router.get("/organizations/{organization_id}")
def organization_detail(
    organization_id: UUID,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(default_get_db),
):
    return success(request, serialize(organization_details(db, principal.id, organization_id)))


@router.get("/assets")
def assets(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, Asset, tenant, limit, cursor)
    return success(request, rows, next_cursor=next_cursor)


@router.post("/assets", status_code=201)
def asset_create(
    body: AssetCreate,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "super_admin")),
    db: Session = Depends(default_get_db),
):
    return success(request, serialize(create_asset(db, tenant, body.model_dump())))


@router.get("/assets/{asset_id}")
def asset_detail(
    asset_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(request, serialize(get_resource(db, Asset, asset_id, tenant)))


@router.patch("/assets/{asset_id}")
def asset_patch(
    asset_id: UUID,
    body: AssetPatch,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "super_admin")),
    db: Session = Depends(default_get_db),
):
    row = update_asset(db, tenant, asset_id, body.model_dump(exclude_unset=True))
    return success(request, serialize(row))


@router.get("/integrations")
def integrations(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, Integration, tenant, limit, cursor)
    return success(request, [_integration_dict(row) for row in rows], next_cursor=next_cursor)


@router.get("/integrations/{integration_id}")
def integration_detail(
    integration_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(
        request, _integration_dict(serialize(get_resource(db, Integration, integration_id, tenant)))
    )


@router.post("/integrations", status_code=201)
def integration_create(
    body: IntegrationCreate,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "super_admin")),
    db: Session = Depends(default_get_db),
):
    return success(
        request,
        _integration_dict(
            serialize(
                create_integration(db, tenant, body.name, body.integration_type, body.configuration)
            )
        ),
    )


@router.post("/integrations/{integration_id}/test")
def integration_test(
    integration_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    row = get_resource(db, Integration, integration_id, tenant)
    provider = row.integration_type.removeprefix("mock_")
    connector = CONNECTORS.get(provider)
    if not connector:
        raise APIError(422, "UNSUPPORTED_CONNECTOR", "Only fixture connectors are supported")
    return success(request, connector.health_check())


@router.post("/integrations/{integration_id}/collect")
def integration_collect(
    integration_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "soc_analyst")),
    db: Session = Depends(default_get_db),
    limit: int = Query(100, ge=1, le=100),
):
    return success(request, collect_integration(db, tenant, integration_id, limit))


@router.get("/mock/{provider}/health")
def mock_health(provider: str, request: Request, principal: Principal = Depends(get_principal)):
    connector = CONNECTORS.get(provider)
    if not connector:
        raise APIError(404, "NOT_FOUND", "Mock provider not found")
    return success(request, connector.health_check())


@router.get("/mock/{provider}/{resource}")
def mock_fixtures(
    provider: str,
    resource: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    if provider not in CONNECTORS or RESOURCE_FOR_PROVIDER[provider] != resource:
        raise APIError(404, "NOT_FOUND", "Mock fixture route not found")
    try:
        page = CONNECTORS[provider].collect(cursor=cursor, limit=limit)
    except ValueError as exc:
        raise APIError(422, "INVALID_CURSOR", "Cursor is invalid") from exc
    return success(request, page["items"], next_cursor=page["next_cursor"], is_simulated=True)


@router.get("/events")
def events(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
    source: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    asset_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
):
    rows, next_cursor = search_events(
        db, tenant, limit, cursor, source, severity, event_type, asset_id, from_, to
    )
    return success(request, [_event_dict(row) for row in rows], next_cursor=next_cursor)


@router.get("/events/{event_id}")
def event_detail(
    event_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(request, _event_dict(event_details(db, tenant, event_id)))


@router.get("/incidents", response_model=APIEnvelope[list[IncidentDTO]])
def incidents(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, Incident, tenant, limit, cursor)
    return success(request, rows, next_cursor=next_cursor)


@router.get("/incidents/{incident_id}", response_model=APIEnvelope[IncidentDTO])
def incident_detail(
    incident_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(request, incident_details(db, tenant, incident_id))


@router.post("/incidents/{incident_id}/status")
def incident_status(
    incident_id: UUID,
    body: IncidentStatusChange,
    request: Request,
    tenant: TenantContext = Depends(role_any("soc_analyst", "security_admin")),
    db: Session = Depends(default_get_db),
):
    row = change_incident_status(db, tenant, incident_id, body.status, body.justification)
    return success(request, serialize(row))


@router.post("/incidents/{incident_id}/comments", status_code=201)
def incident_comment(
    incident_id: UUID,
    body: CommentCreate,
    request: Request,
    tenant: TenantContext = Depends(role_any("soc_analyst", "security_admin")),
    db: Session = Depends(default_get_db),
):
    return success(request, serialize(add_incident_comment(db, tenant, incident_id, body.body)))


@router.get("/policies", response_model=APIEnvelope[list[PolicyDTO]])
def policies(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, Policy, tenant, limit, cursor)
    return success(request, rows, next_cursor=next_cursor)


@router.post("/policies", status_code=201, response_model=APIEnvelope[PolicyDTO])
def policy_create(
    body: PolicyCreate,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "super_admin")),
    db: Session = Depends(default_get_db),
):
    row = create_policy(db, tenant, body.model_dump())
    return success(request, serialize(row))


@router.patch("/policies/{policy_id}", response_model=APIEnvelope[PolicyDTO])
def policy_patch(
    policy_id: UUID,
    body: PolicyPatch,
    request: Request,
    tenant: TenantContext = Depends(role_any("security_admin", "super_admin")),
    db: Session = Depends(default_get_db),
):
    row = update_policy(db, tenant, policy_id, body.model_dump(exclude_unset=True))
    return success(request, serialize(row))


@router.post("/incidents/{incident_id}/responses", status_code=201)
def response_propose(
    incident_id: UUID,
    body: ResponseCreate,
    request: Request,
    tenant: TenantContext = Depends(role_any("soc_analyst", "security_admin")),
    db: Session = Depends(default_get_db),
):
    row = propose_response(db, tenant, incident_id, body.policy_id, body.idempotency_key)
    return success(request, serialize(row))


@router.get("/approvals", response_model=APIEnvelope[list[ApprovalDTO]])
def approvals(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, Approval, tenant, limit, cursor)
    return success(request, rows, next_cursor=next_cursor)


@router.post("/approvals/{approval_id}/approve", response_model=APIEnvelope[ApprovalDTO])
def approval_approve(
    approval_id: UUID,
    body: ApprovalDecision,
    request: Request,
    tenant: TenantContext = Depends(role_any("soc_analyst", "security_admin")),
    db: Session = Depends(default_get_db),
):
    return success(
        request, serialize(decide_approval(db, tenant, approval_id, "approved", body.justification))
    )


@router.post("/approvals/{approval_id}/reject", response_model=APIEnvelope[ApprovalDTO])
def approval_reject(
    approval_id: UUID,
    body: ApprovalDecision,
    request: Request,
    tenant: TenantContext = Depends(role_any("soc_analyst", "security_admin")),
    db: Session = Depends(default_get_db),
):
    return success(
        request, serialize(decide_approval(db, tenant, approval_id, "rejected", body.justification))
    )


@router.get("/responses/{response_id}", response_model=APIEnvelope[ResponseDTO])
def response_detail(
    response_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(request, serialize(get_resource(db, Response, response_id, tenant)))


@router.post("/responses/{response_id}/dry-run")
def response_dry_run(
    response_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(role_any("operator", "security_admin")),
    db: Session = Depends(default_get_db),
):
    return success(request, dry_run_response(db, tenant, response_id))


@router.post("/responses/{response_id}/execute", response_model=APIEnvelope[ResponseDTO])
def response_execute(
    response_id: UUID,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(
        request,
        serialize(
            execute_response(
                db, tenant, response_id, request.app.state.config.responses_enabled, idempotency_key
            )
        ),
    )


@router.get("/audit-logs")
def audit_logs(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    rows, next_cursor = list_rows(db, AuditLog, tenant, limit, cursor)
    return success(request, rows, next_cursor=next_cursor)


@router.get("/dashboard/summary")
def dashboard_summary(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
):
    return success(request, get_dashboard_summary(db, tenant))


@router.get("/dashboard/timeline")
def dashboard_timeline(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(default_get_db),
    limit: int = Query(50, ge=1, le=100),
):
    return success(request, get_dashboard_timeline(db, tenant, limit))


@router.get("/health/live")
def health_live(request: Request):
    return success(request, {"status": "live"})


@router.get("/health/ready")
def health_ready(request: Request, db: Session = Depends(default_get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logging.getLogger(__name__).warning("Database readiness probe failed", exc_info=exc)
        raise APIError(503, "DATABASE_UNAVAILABLE", "Database is not ready") from exc
    return success(request, {"status": "ready", "database": "available"})
