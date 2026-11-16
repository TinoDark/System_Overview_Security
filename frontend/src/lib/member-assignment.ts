import type { Membership, Role } from "@/types/api";

export const DEFAULT_MEMBER_ROLE: Role = "soc_analyst";

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super administrateur",
  security_admin: "Administrateur",
  soc_analyst: "Analyste",
  operator: "Opérateur",
  auditor: "Auditeur",
  observer: "Observateur",
};

/** Highest rank first. A caller grants their own rank and every rank below. */
export const ROLE_LADDER: Role[] = [
  "super_admin",
  "security_admin",
  "soc_analyst",
  "operator",
  "auditor",
  "observer",
];

export type RolePick = Record<string, Role>;

export function rolesFor(membership: Pick<Membership, "role">): Role[] {
  const index = ROLE_LADDER.indexOf(membership.role);
  return index < 0 ? [] : ROLE_LADDER.slice(index);
}

export function initialPick(organizationIds: string[]): RolePick {
  return organizationIds.length === 1 ? { [organizationIds[0]]: DEFAULT_MEMBER_ROLE } : {};
}

export function toggleOrganization(current: RolePick, organizationId: string): RolePick {
  if (current[organizationId]) {
    const next = { ...current };
    delete next[organizationId];
    return next;
  }
  return { ...current, [organizationId]: DEFAULT_MEMBER_ROLE };
}

export function selectEveryOrganization(current: RolePick, organizationIds: string[]): RolePick {
  const next = { ...current };
  for (const organizationId of organizationIds) {
    if (!next[organizationId]) next[organizationId] = DEFAULT_MEMBER_ROLE;
  }
  return next;
}
