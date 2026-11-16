"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { MemberDialog } from "@/components/member-dialog";
import { ROLE_LABELS, rolesFor } from "@/lib/member-assignment";
import { ErrorState, LoadingState, PageHeading } from "@/components/ui";
import type { OrganizationMember, Role } from "@/types/api";

export default function OrganizationDetailPage() {
  const params = useParams<{ id: string }>();
  const organizationId = params.id;
  const queryClient = useQueryClient();
  const principal = useQuery({ queryKey: ["principal"], queryFn: () => api.me() });
  const organizations = useQuery({ queryKey: ["organizations"], queryFn: () => api.organizations() });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api.members() });
  const organization = organizations.data?.data.find((item) => item.id === organizationId);
  const users = (members.data?.data ?? []).filter((member) => member.memberships.some((membership) => membership.organization_id === organizationId));
  const caller = (principal.data?.data.memberships ?? []).find((membership) => membership.organization_id === organizationId);
  const options = caller ? rolesFor(caller) : [];
  const [opened, setOpened] = useState<OrganizationMember | null>(null);
  const changeRole = useMutation({
    mutationFn: (input: { userId: string; role: Role }) => api.updateMemberRole(input.userId, { organization_id: organizationId, role: input.role }),
    onSuccess: async () => {
      setOpened(null);
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });

  if (organizations.isLoading || members.isLoading || principal.isLoading) return <LoadingState />;
  if (organizations.isError) return <ErrorState error={organizations.error} onRetry={() => void organizations.refetch()} />;
  if (members.isError) return <ErrorState error={members.error} onRetry={() => void members.refetch()} />;
  if (!organization) return <section className="tenant-empty"><h2>Organisation introuvable</h2><p><Link href="/organizations">Retour</Link></p></section>;

  return <div className="page-stack">
    <PageHeading title={organization.name} description="Cliquez un compte pour ouvrir sa fiche." actions={<Link href="/organizations">Organisations</Link>} />
    <table className="directory">
      <thead><tr><th>Compte</th><th>Rôle</th></tr></thead>
      <tbody>{users.map((member: OrganizationMember) => {
        const membership = member.memberships.find((item) => item.organization_id === organizationId);
        return <tr key={member.user_id} className="directory-row" onClick={() => { changeRole.reset(); setOpened(member); }}>
          <td>{member.display_name}<span className="table-subtext">{member.user_key}</span></td>
          <td>{membership ? ROLE_LABELS[membership.role] ?? membership.role : "—"}</td>
        </tr>;
      })}</tbody>
    </table>
    {changeRole.isError && !opened && <p className="directory-note">{changeRole.error.message}</p>}
    {opened && <MemberDialog
      name={opened.display_name}
      userKey={opened.user_key}
      pending={changeRole.isPending}
      error={changeRole.isError ? changeRole.error.message : undefined}
      memberships={[{
        organizationId,
        organizationName: organization.name,
        role: opened.memberships.find((item) => item.organization_id === organizationId)?.role ?? "observer",
        options,
        editable: opened.memberships.find((item) => item.organization_id === organizationId)?.role !== "super_admin" && opened.user_id !== principal.data?.data.user_id,
      }]}
      onClose={() => setOpened(null)}
      onConfirm={(changes) => { const next = changes[0]; if (next) changeRole.mutate({ userId: opened.user_id, role: next.role }); }}
    />}
    <p className="directory-note"><Link href={`/members?organization=${organization.id}`}>Tous les membres</Link></p>
  </div>;
}
