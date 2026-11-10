import ipaddress
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["super_admin", "security_admin", "soc_analyst", "operator", "auditor", "observer"]
Severity = Literal["info", "low", "medium", "high", "critical"]
Source = Literal["wazuh", "rspamd", "clamav", "misp"]


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MockLogin(StrictDTO):
    user_key: str = Field(min_length=1, max_length=100)


class MembershipDTO(BaseModel):
    organization_id: UUID
    organization_name: str
    role: Role
    permissions: list[str] = Field(default_factory=list)


class PrincipalDTO(BaseModel):
    user_id: UUID
    user_key: str
    display_name: str
    memberships: list[MembershipDTO]
    permissions: list[str] = Field(default_factory=list)


class IndicatorDTO(BaseModel):
    type: Literal["ip", "domain", "hash"]
    value: str = Field(min_length=1, max_length=255)
    confidence: int | None = Field(default=None, ge=0, le=100)

    @field_validator("value")
    @classmethod
    def validate_indicator_value(cls, value: str, info):
        kind = info.data.get("type")
        if kind == "ip":
            try:
                ipaddress.ip_address(value)
            except ValueError as exc:
                raise ValueError("indicator must be a valid IP address") from exc
        elif kind == "domain":
            if len(value) > 253 or not re.fullmatch(
                r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}",
                value,
            ):
                raise ValueError("indicator must be a valid domain name")
        elif kind == "hash" and not re.fullmatch(
            r"(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}|[A-Fa-f0-9]{128})", value
        ):
            raise ValueError("indicator hash must be hexadecimal")
        return value


class AssetRefDTO(BaseModel):
    asset_id: UUID | None = None
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)


class NormalizedEventDTO(BaseModel):
    event_id: UUID
    organization_id: UUID
    source: Source
    integration_id: UUID
    external_event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    occurred_at: datetime
    observed_at: datetime
    severity: Severity
    asset: AssetRefDTO
    actor: dict[str, Any] | None = None
    message: str = Field(max_length=2000)
    indicators: list[IndicatorDTO]
    raw_event: dict[str, Any]
    schema_version: Literal["1.0"] = "1.0"
    is_simulated: Literal[True] = True

    @field_validator("occurred_at", "observed_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if (
            value.tzinfo is None
            or value.utcoffset() is None
            or value.utcoffset().total_seconds() != 0
        ):
            raise ValueError("datetime must be timezone-aware UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def bound_serialized_size(self):
        if len(self.model_dump_json().encode("utf-8")) > 65536:
            raise ValueError("event exceeds 64 KiB")
        return self


class AssetCreate(StrictDTO):
    name: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=1, max_length=50)
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    operating_system: str | None = Field(default=None, max_length=150)


class AssetPatch(StrictDTO):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: str | None = Field(default=None, min_length=1, max_length=50)
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    operating_system: str | None = Field(default=None, max_length=150)
    status: Literal["active", "inactive"] | None = None


class IntegrationCreate(StrictDTO):
    name: str = Field(min_length=1, max_length=150)
    integration_type: Literal["mock_wazuh", "mock_rspamd", "mock_clamav", "mock_misp"]
    configuration: dict[str, Any] = Field(default_factory=dict)


class PolicyCreate(StrictDTO):
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = False
    trigger_min_severity: Severity | None = None
    trigger_min_score: int | None = Field(default=None, ge=0, le=100)
    action_type: Literal["simulate_containment"] = "simulate_containment"


class PolicyPatch(StrictDTO):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    trigger_min_severity: Severity | None = None
    trigger_min_score: int | None = Field(default=None, ge=0, le=100)
    action_type: Literal["simulate_containment"] | None = None


class ApprovalDecision(StrictDTO):
    justification: str = Field(min_length=1, max_length=2000)


class IncidentStatusChange(StrictDTO):
    status: Literal["in_progress", "resolved", "closed"]
    justification: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def closed_requires_reason(self):
        if self.status == "closed" and not self.justification:
            raise ValueError("closing an incident requires justification")
        return self


class CommentCreate(StrictDTO):
    body: str = Field(min_length=1, max_length=2000)


class ResponseCreate(StrictDTO):
    policy_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=255)


class EnvelopeMeta(BaseModel):
    request_id: UUID
    model_config = ConfigDict(extra="allow")


class APIEnvelope[T](BaseModel):
    data: T
    meta: EnvelopeMeta


class RiskFactorDTO(BaseModel):
    code: str
    contribution: int = Field(ge=0, le=100)
    explanation: str


class IncidentCommentDTO(BaseModel):
    id: UUID
    body: str
    author: str | None = None
    created_at: datetime


class ApprovalDTO(BaseModel):
    id: UUID
    organization_id: UUID
    incident_id: UUID
    response_id: UUID
    requested_by: UUID
    decided_by: UUID | None = None
    status: Literal["pending", "approved", "rejected", "expired"]
    justification: str | None = None
    expires_at: datetime
    decided_at: datetime | None = None


class IncidentDTO(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    description: str | None = None
    severity: Severity
    status: Literal["new", "in_progress", "resolved", "closed"]
    risk_score: int = Field(ge=0, le=100)
    risk_factors: list[RiskFactorDTO]
    created_at: datetime
    updated_at: datetime
    event_ids: list[UUID] = Field(default_factory=list)
    comments: list[IncidentCommentDTO] = Field(default_factory=list)
    response_id: UUID | None = None
    approval: ApprovalDTO | None = None


class PolicyDTO(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    enabled: bool
    trigger_min_severity: Severity | None = None
    trigger_min_score: int | None = None
    action_type: Literal["simulate_containment"]
    approval_required: Literal[True] = True


class ResponseDTO(BaseModel):
    id: UUID
    organization_id: UUID
    incident_id: UUID
    policy_id: UUID
    approval_id: UUID | None = None
    requested_by: UUID
    action_type: Literal["simulate_containment"]
    status: Literal["proposed", "approved", "rejected", "simulated", "failed"]
    idempotency_key: str
    simulated: Literal[True]
    result: dict[str, Any] | None = None
