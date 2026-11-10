import type {
  ApiEnvelope,
  ApiErrorEnvelope,
  ApiMeta,
  Asset,
  Approval,
  AuditEntry,
  CollectionRun,
  DashboardSummary,
  Incident,
  Integration,
  Policy,
  Principal,
  ResponseResult,
  SecurityEvent,
} from "@/types/api";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "soc_demo_token";
const ORGANIZATION_KEY = "soc_organization_id";
const LOGOUT_WARNING_KEY = "soc_logout_warning";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly details?: unknown[],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : window.sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(ORGANIZATION_KEY);
}

export function saveLogoutWarning(message: string): void {
  window.sessionStorage.setItem(LOGOUT_WARNING_KEY, message);
}

export function consumeLogoutWarning(): string | null {
  const warning = window.sessionStorage.getItem(LOGOUT_WARNING_KEY);
  window.sessionStorage.removeItem(LOGOUT_WARNING_KEY);
  return warning;
}

export function getOrganizationId(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(ORGANIZATION_KEY);
}

export function saveOrganizationId(id: string): void {
  window.localStorage.setItem(ORGANIZATION_KEY, id);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  tenantScoped = true,
): Promise<ApiEnvelope<T>> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (tenantScoped) {
    const organizationId = getOrganizationId();
    if (!organizationId) throw new ApiError("Sélectionnez une organisation pour continuer.", 400, "TENANT_REQUIRED");
    headers.set("X-Organization-ID", organizationId);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new ApiError("API indisponible. Vérifiez que le backend FastAPI est démarré.", 0, "API_UNAVAILABLE");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const errorBody = body as ApiErrorEnvelope | null;
    throw new ApiError(
      errorBody?.error?.message ?? `La requête a échoué (${response.status}).`,
      response.status,
      errorBody?.error?.code,
      errorBody?.error?.details,
    );
  }
  if (!body || typeof body !== "object" || !("data" in body) || !("meta" in body)) {
    throw new ApiError("Réponse API invalide : enveloppe data/meta absente.", response.status, "INVALID_ENVELOPE");
  }
  return body as ApiEnvelope<T>;
}

function queryString(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : "";
}

export function normalizeList<T>(data: T[] | { items?: T[]; results?: T[] }, meta: ApiMeta): ApiEnvelope<T[]> {
  const rows = Array.isArray(data) ? data : data.items ?? data.results;
  if (!Array.isArray(rows)) {
    throw new ApiError("Réponse API invalide : liste absente.", 502, "INVALID_LIST");
  }
  return { data: rows, meta };
}

export const api = {
  async login(user_key: string) {
    return request<{ access_token?: string; token?: string; token_type?: string; principal?: Principal }>(
      "/auth/mock-login",
      { method: "POST", body: JSON.stringify({ user_key }) },
      false,
    );
  },
  me: () => request<Principal>("/auth/me", {}, false),
  logout: () => request<{ status: string }>("/auth/mock-logout", { method: "POST" }, false),
  summary: () => request<DashboardSummary>("/dashboard/summary"),
  timeline: () => request<Array<Record<string, unknown>>>("/dashboard/timeline"),
  events: async (filters: Record<string, string | number | undefined>) => {
    const result = await request<SecurityEvent[] | { items?: SecurityEvent[]; results?: SecurityEvent[] }>(`/events${queryString(filters)}`);
    return normalizeList(result.data, result.meta);
  },
  event: (id: string) => request<SecurityEvent>(`/events/${encodeURIComponent(id)}`),
  incidents: async (filters: Record<string, string | number | undefined>) => {
    const result = await request<Incident[] | { items?: Incident[]; results?: Incident[] }>(`/incidents${queryString(filters)}`);
    return normalizeList(result.data, result.meta);
  },
  incident: (id: string) => request<Incident>(`/incidents/${encodeURIComponent(id)}`),
  changeIncidentStatus: (id: string, status: string, justification?: string) =>
    request<Incident>(`/incidents/${encodeURIComponent(id)}/status`, {
      method: "POST",
      body: JSON.stringify({ status, ...(justification ? { justification } : {}) }),
    }),
  addIncidentComment: (id: string, body: string) =>
    request<unknown>(`/incidents/${encodeURIComponent(id)}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
  assets: async () => {
    const result = await request<Asset[] | { items?: Asset[]; results?: Asset[] }>("/assets?limit=100");
    return normalizeList(result.data, result.meta);
  },
  integrations: async () => {
    const result = await request<Integration[] | { items?: Integration[]; results?: Integration[] }>("/integrations?limit=100");
    return normalizeList(result.data, result.meta);
  },
  collect: (id: string) =>
    request<CollectionRun>(`/integrations/${encodeURIComponent(id)}/collect`, { method: "POST", body: JSON.stringify({}) }),
  policies: async () => {
    const result = await request<Policy[] | { items?: Policy[]; results?: Policy[] }>("/policies?limit=100");
    return normalizeList(result.data, result.meta);
  },
  approvals: async () => {
    const result = await request<Approval[] | { items?: Approval[]; results?: Approval[] }>("/approvals?limit=100");
    return normalizeList(result.data, result.meta);
  },
  decideApproval: (id: string, decision: "approve" | "reject", justification: string) =>
    request<Approval>(`/approvals/${encodeURIComponent(id)}/${decision}`, {
      method: "POST",
      body: JSON.stringify({ justification }),
    }),
  responseAction: (id: string, action: "dry-run" | "execute", idempotencyKey?: string) => {
    const headers: Record<string, string> = {};
    if (action === "execute") {
      if (!idempotencyKey) {
        throw new ApiError(
          "Clé d’idempotence absente pour cette réponse.",
          400,
          "IDEMPOTENCY_KEY_REQUIRED",
        );
      }
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return request<ResponseResult>(`/responses/${encodeURIComponent(id)}/${action}`, {
      method: "POST",
      headers,
      body: JSON.stringify({}),
    });
  },
  response: (id: string) => request<ResponseResult>(`/responses/${encodeURIComponent(id)}`),
  audit: async (filters: Record<string, string | number | undefined> = {}) => {
    const result = await request<AuditEntry[] | { items?: AuditEntry[]; results?: AuditEntry[] }>(`/audit-logs${queryString(filters)}`);
    return normalizeList(result.data, result.meta);
  },
};

export type { ApiMeta };
