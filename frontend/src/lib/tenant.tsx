"use client";

import { createContext, useContext } from "react";
import type { Role } from "@/types/api";

const OrganizationContext = createContext<{ organizationId: string | null; role: Role | null }>({
  organizationId: null,
  role: null,
});

export function OrganizationProvider({
  organizationId,
  role,
  children,
}: {
  organizationId: string | null;
  role: Role | null;
  children: React.ReactNode;
}) {
  return <OrganizationContext.Provider value={{ organizationId, role }}>{children}</OrganizationContext.Provider>;
}

export function useOrganizationId(): string {
  const { organizationId } = useContext(OrganizationContext);
  if (!organizationId) throw new Error("Organisation active absente");
  return organizationId;
}

export function useRole(): Role | null {
  return useContext(OrganizationContext).role;
}
