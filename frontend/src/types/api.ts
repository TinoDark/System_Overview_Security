export type Role =
  | "super_admin"
  | "security_admin"
  | "soc_analyst"
  | "operator"
  | "auditor"
  | "observer";

export interface Membership {
  organization_id: string;
  organization_name: string;
  role: Role;
}

export interface Principal {
  user_id: string;
  user_key: string;
  display_name: string;
  memberships: Membership[];
  permissions?: string[];
}

export interface ApiMeta {
  request_id?: string;
  next_cursor?: string | null;
  [key: string]: unknown;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMeta;
}

export interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown[];
  };
  meta?: ApiMeta;
}

export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type IncidentStatus = "new" | "in_progress" | "resolved" | "closed";
export type EventSource = "wazuh" | "rspamd" | "clamav" | "misp";

export interface AssetSummary {
  asset_id?: string;
  id?: string;
  hostname?: string;
  ip_address?: string;
  type?: string;
}

export interface SecurityEvent {
  event_id: string;
  organization_id: string;
  source: EventSource;
  integration_id: string;
  external_event_id: string;
  event_type: string;
  occurred_at: string;
  observed_at: string;
  severity: Severity;
  asset?: AssetSummary;
  actor?: { username?: string };
  message: string;
  indicators?: Array<{ type: string; value: string; confidence?: number }>;
  raw_event?: Record<string, unknown>;
  schema_version?: string;
  is_simulated: boolean;
}

export interface RiskFactor {
  code: string;
  contribution: number;
  explanation: string;
}

export interface Incident {
  id: string;
  organization_id: string;
  title: string;
  description?: string | null;
  severity: Severity;
  status: IncidentStatus;
  risk_score: number;
  risk_factors?: RiskFactor[];
  assigned_to?: string | null;
  event_ids: string[];
  created_at: string;
  updated_at: string;
  comments?: IncidentComment[];
  response_id?: string | null;
  approval?: Approval | null;
}

export interface IncidentComment {
  id: string;
  author?: string;
  body: string;
  created_at: string;
}

export interface Integration {
  id: string;
  organization_id: string;
  name: string;
  integration_type: string;
  provider?: string;
  type?: string;
  status?: string;
  enabled?: boolean;
  is_simulated: boolean;
  last_collected_at?: string | null;
  events_received?: number;
}

export interface Asset {
  id: string;
  organization_id: string;
  name: string;
  asset_type: string;
  hostname?: string | null;
  ip_address?: string;
  status?: string;
  updated_at?: string;
}

export interface Policy {
  id: string;
  organization_id: string;
  name: string;
  enabled: boolean;
  trigger_min_severity?: Severity;
  trigger_min_score?: number;
  action_type: "simulate_containment";
  approval_required: true;
}

export interface Approval {
  id: string;
  organization_id: string;
  incident_id: string;
  response_id: string;
  status: "pending" | "approved" | "rejected" | "expired";
  requested_by: string;
  decided_by?: string | null;
  justification?: string | null;
  expires_at: string;
  decided_at?: string | null;
}

export interface ResponseResult {
  id: string;
  organization_id: string;
  incident_id: string;
  policy_id: string;
  approval_id: string;
  action_type: "simulate_containment";
  status: "proposed" | "approved" | "rejected" | "simulated" | "failed";
  idempotency_key: string;
  simulated: true;
  result?: { outcome: "simulated" | "failed"; verified: boolean; message: string };
}

export interface AuditEntry {
  id: string;
  organization_id?: string | null;
  actor_user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  outcome: string;
  metadata?: Record<string, unknown>;
  correlation_id?: string | null;
  created_at: string;
}

export interface DashboardSummary {
  events_total?: number;
  events_24h?: number;
  incidents_open?: number;
  incidents_critical?: number;
  incidents_resolved?: number;
  approvals_pending?: number;
  responses_simulated?: number;
  active_integrations?: number;
  total_assets?: number;
  is_simulated?: boolean;
  [key: string]: boolean | number | string | undefined;
}

export interface CollectionRun {
  run_id: string;
  status: string;
  received: number;
  inserted: number;
  duplicates: number;
  incidents_created: number;
  is_simulated?: boolean;
}
