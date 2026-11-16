import type { Role } from "@/types/api";

const ALL: Role[] = ["super_admin", "security_admin", "soc_analyst", "operator", "auditor", "observer"];
const INVESTIGATION: Role[] = ["super_admin", "security_admin", "soc_analyst"];
const INCIDENTS: Role[] = ["super_admin", "security_admin", "soc_analyst", "operator"];
const AUDIT: Role[] = ["super_admin", "security_admin", "auditor"];
const MEMBERS: Role[] = ["super_admin", "security_admin"];
const ORGANIZATIONS: Role[] = ["super_admin"];

export const PAGE_ACCESS: { href: string; roles: Role[] }[] = [
  { href: "/dashboard", roles: ALL },
  { href: "/incidents", roles: INCIDENTS },
  { href: "/events", roles: INVESTIGATION },
  { href: "/assets", roles: INVESTIGATION },
  { href: "/integrations", roles: INVESTIGATION },
  { href: "/policies", roles: INVESTIGATION },
  { href: "/approvals", roles: INVESTIGATION },
  { href: "/audit", roles: AUDIT },
  { href: "/members", roles: MEMBERS },
  { href: "/organizations", roles: ORGANIZATIONS },
];

export function canOpen(role: Role | null | undefined, pathname: string): boolean {
  const page = PAGE_ACCESS.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  if (!page || !role) return false;
  return page.roles.includes(role);
}

export function canManageIncidents(role: Role | null | undefined): boolean {
  return role === "super_admin" || role === "security_admin" || role === "soc_analyst";
}

export function canExecuteResponse(role: Role | null | undefined): boolean {
  return role === "super_admin" || role === "security_admin" || role === "operator";
}

export function canManageMembers(role: Role | null | undefined): boolean {
  return role === "super_admin" || role === "security_admin";
}
