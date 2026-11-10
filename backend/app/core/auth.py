import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.db.models import Membership, Organization, User
from app.db.session import get_db

MOCK_CATALOG = {
    "analyst-a": ("10000000-0000-4000-8000-000000000001", "Ari Analyst", "analyst"),
    "admin-a": ("10000000-0000-4000-8000-000000000002", "Sam Security Admin", "admin"),
    "operator-a": ("10000000-0000-4000-8000-000000000003", "Omar Operator", "operator"),
    "analyst-b": ("20000000-0000-4000-8000-000000000001", "Bea Analyst", "analyst"),
    "admin-b": ("20000000-0000-4000-8000-000000000002", "Bo Security Admin", "admin"),
    "operator-b": ("20000000-0000-4000-8000-000000000003", "Uma Operator", "operator"),
    "auditor-a": ("10000000-0000-4000-8000-000000000004", "Ava Auditor", "auditor"),
    "observer-a": ("10000000-0000-4000-8000-000000000005", "Ollie Observer", "observer"),
    "super-admin": (
        "90000000-0000-4000-8000-000000000001",
        "Demo Super Administrator",
        "super_admin",
    ),
}
ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "security_admin": [
        "read",
        "assets:write",
        "integrations:write",
        "collect",
        "incidents:manage",
        "policies:write",
        "approvals:decide",
        "responses:execute",
        "audit:read",
    ],
    "soc_analyst": ["read", "collect", "incidents:manage", "approvals:decide", "responses:propose"],
    "operator": ["read", "responses:dry_run", "responses:execute"],
    "auditor": ["read", "audit:read"],
    "observer": ["read", "dashboard:read"],
}


def permissions_for_role(role: str) -> list[str]:
    return list(ROLE_PERMISSIONS.get(role, []))


MOCK_SESSIONS: dict[str, tuple[str, datetime]] = {}


def issue_token(user_id: str) -> str:
    now = datetime.now(UTC)
    expired_tokens = [token for token, (_, expiry) in MOCK_SESSIONS.items() if expiry <= now]
    for token in expired_tokens:
        invalidate_token(token)
    token = secrets.token_urlsafe(32)
    MOCK_SESSIONS[token] = (user_id, now + timedelta(hours=8))
    return token


def invalidate_token(token: str) -> None:
    MOCK_SESSIONS.pop(token, None)


@dataclass(frozen=True)
class Principal:
    id: UUID
    user_key: str
    display_name: str
    memberships: tuple[dict, ...]


@dataclass(frozen=True)
class TenantContext:
    organization_id: UUID
    organization_name: str
    role: str
    principal: Principal


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise APIError(401, "UNAUTHENTICATED", "Bearer token required")
    return authorization.removeprefix("Bearer ").strip()


def get_principal(
    token: str = Depends(get_bearer_token), db: Session = Depends(get_db)
) -> Principal:
    active = MOCK_SESSIONS.get(token)
    if not active or active[1] <= datetime.now(UTC):
        invalidate_token(token)
        raise APIError(401, "INVALID_TOKEN", "Token is invalid or expired")
    user_id = UUID(active[0])
    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise APIError(401, "INVALID_TOKEN", "Token is invalid or expired")
    rows = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user_id, Organization.status == "active")
    ).all()
    memberships = tuple(
        {
            "organization_id": str(m.organization_id),
            "organization_name": org.name,
            "role": m.role,
            "permissions": permissions_for_role(m.role),
        }
        for m, org in rows
    )
    return Principal(user.id, user.user_key, user.display_name, memberships)


def get_tenant(
    principal: Principal = Depends(get_principal),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
) -> TenantContext:
    if not principal.memberships:
        raise APIError(403, "ORGANIZATION_FORBIDDEN", "No active organization membership")
    if x_organization_id is None:
        if len(principal.memberships) != 1:
            raise APIError(400, "TENANT_REQUIRED", "Select an organization using X-Organization-ID")
        selected = principal.memberships[0]
    else:
        try:
            requested = str(UUID(x_organization_id))
        except ValueError as exc:
            raise APIError(
                422, "INVALID_ORGANIZATION_ID", "X-Organization-ID must be a UUID"
            ) from exc
        selected = next(
            (m for m in principal.memberships if m["organization_id"] == requested), None
        )
        if selected is None:
            raise APIError(403, "ORGANIZATION_FORBIDDEN", "Organization membership is required")
    return TenantContext(
        UUID(selected["organization_id"]),
        selected["organization_name"],
        selected["role"],
        principal,
    )


def require_roles(*roles: str):
    def dependency(tenant: TenantContext = Depends(get_tenant)) -> TenantContext:
        if tenant.role not in roles:
            raise APIError(403, "FORBIDDEN", "Role is not permitted for this operation")
        return tenant

    return dependency
