"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MemberDialog, Popup, type DialogMembership } from "@/components/member-dialog";
import { DEFAULT_MEMBER_ROLE, ROLE_LABELS, rolesFor } from "@/lib/member-assignment";
import { ErrorState, LoadingState, PageHeading } from "@/components/ui";
import type { OrganizationMember, Role } from "@/types/api";

function MembersPage() {
  const queryClient = useQueryClient();
  const requestedOrg = useSearchParams().get("organization");
  const principal = useQuery({ queryKey: ["principal"], queryFn: () => api.me() });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api.members() });
  const adminOrgs = useMemo(
    () => (principal.data?.data.memberships ?? []).filter((membership) => membership.role === "super_admin" || membership.role === "security_admin"),
    [principal.data],
  );
  const [orgFilter, setOrgFilter] = useState(requestedOrg ?? "all");
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [userKey, setUserKey] = useState("");
  const [organizationId, setOrganizationId] = useState(requestedOrg && adminOrgs.some((item) => item.organization_id === requestedOrg) ? requestedOrg : adminOrgs[0]?.organization_id ?? "");
  const activeOrgId = adminOrgs.some((item) => item.organization_id === organizationId) ? organizationId : adminOrgs[0]?.organization_id ?? "";
  const activeOrg = adminOrgs.find((item) => item.organization_id === activeOrgId);
  const [role, setRole] = useState<Role>(DEFAULT_MEMBER_ROLE);
  const [note, setNote] = useState("");
  const [confirmCreate, setConfirmCreate] = useState(false);
  const [opened, setOpened] = useState<OrganizationMember | null>(null);
  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (members.data?.data ?? []).filter((member) => {
      const inOrg = orgFilter === "all" || member.memberships.some((membership) => membership.organization_id === orgFilter);
      const matches = !needle || member.display_name.toLowerCase().includes(needle) || member.user_key.toLowerCase().includes(needle);
      return inOrg && matches;
    });
  }, [members.data, orgFilter, query]);
  const create = useMutation({
    mutationFn: () => api.createMember({
      user_key: userKey.trim(),
      display_name: displayName.trim(),
      memberships: [{ organization_id: activeOrgId, role: rolesFor(activeOrg ?? { role: "security_admin" }).includes(role) ? role : DEFAULT_MEMBER_ROLE }],
    }),
    onSuccess: async (result) => {
      setNote(`${result.data.display_name} est ajouté.`);
      setDisplayName("");
      setUserKey("");
      setAdding(false);
      setConfirmCreate(false);
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });
  const changeRole = useMutation({
    mutationFn: async (input: { userId: string; changes: { organizationId: string; role: Role }[] }) => {
      for (const change of input.changes) {
        await api.updateMemberRole(input.userId, { organization_id: change.organizationId, role: change.role });
      }
    },
    onSuccess: async () => {
      setNote("Rôle remplacé.");
      setOpened(null);
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });

  const chosenRole = activeOrg && rolesFor(activeOrg).includes(role) ? role : DEFAULT_MEMBER_ROLE;
  const canAskCreate = displayName.trim().length > 0 && userKey.trim().length > 0 && Boolean(activeOrgId);

  return <div className="page-stack">
    <PageHeading title="Membres" description="Cliquez un compte pour ouvrir sa fiche et changer son rôle." actions={<button type="button" className="button button-secondary" onClick={() => { setNote(""); setConfirmCreate(false); setAdding(true); }}>Ajouter</button>} />
    {note && <p className="directory-note">{note}</p>}
    {adding && <Popup title={confirmCreate ? "Confirmer le compte" : "Nouveau compte"} onClose={() => { setAdding(false); setConfirmCreate(false); }}>
      {confirmCreate && activeOrg ? <>
        <p>Créer le compte « {displayName.trim()} » ({userKey.trim()}) comme {ROLE_LABELS[chosenRole]} dans {activeOrg.organization_name} ?</p>
        {create.isError && <p className="member-dialog-error">{create.error.message}</p>}
        <button type="button" className="member-dialog-submit" disabled={create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Confirmation…" : "Confirmer"}</button>
        <button type="button" className="member-dialog-back" onClick={() => setConfirmCreate(false)}>Revenir</button>
      </> : <form onSubmit={(event) => { event.preventDefault(); if (canAskCreate) setConfirmCreate(true); }}>
        <label>Nom affiché<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={200} required autoFocus placeholder="Ex. Nina Analyste" /></label>
        <label>Clé de connexion<input value={userKey} onChange={(event) => setUserKey(event.target.value)} maxLength={100} required spellCheck={false} placeholder="Ex. nina.analyste" autoComplete="off" /></label>
        {adminOrgs.length > 1 && <label>Organisation<select value={activeOrgId} onChange={(event) => setOrganizationId(event.target.value)}>
          {adminOrgs.map((membership) => <option key={membership.organization_id} value={membership.organization_id}>{membership.organization_name}</option>)}
        </select></label>}
        <label>Rôle<select value={chosenRole} onChange={(event) => setRole(event.target.value as Role)}>
          {(activeOrg ? rolesFor(activeOrg) : [DEFAULT_MEMBER_ROLE]).map((option) => <option key={option} value={option}>{ROLE_LABELS[option]}</option>)}
        </select></label>
        {create.isError && <p className="member-dialog-error">{create.error.message}</p>}
        <button className="member-dialog-submit" disabled={!canAskCreate}>Continuer</button>
      </form>}
    </Popup>}
    <div className="directory-tools">
      <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nom ou clé" aria-label="Filtrer les comptes" />
      {adminOrgs.length > 1 && <select className="directory-filter" aria-label="Organisation" value={orgFilter} onChange={(event) => setOrgFilter(event.target.value)}>
        <option value="all">Toutes</option>
        {adminOrgs.map((membership) => <option key={membership.organization_id} value={membership.organization_id}>{membership.organization_name}</option>)}
      </select>}
    </div>
    {members.isLoading ? <LoadingState /> : members.isError ? <ErrorState error={members.error} onRetry={() => void members.refetch()} /> : <table className="directory">
      <thead><tr><th>Compte</th><th>Rôle</th></tr></thead>
      <tbody>
        {rows.map((member: OrganizationMember) => <tr key={member.user_id} className="directory-row" onClick={() => { changeRole.reset(); setOpened(member); }}>
          <td>{member.display_name}<span className="table-subtext">{member.user_key}</span></td>
          <td>{member.memberships.filter((membership) => orgFilter === "all" || membership.organization_id === orgFilter).map((membership) => <div key={membership.organization_id} className="directory-role">
            {adminOrgs.length > 1 && <span>{membership.organization_name}</span>}
            <strong>{ROLE_LABELS[membership.role] ?? membership.role}</strong>
          </div>)}</td>
        </tr>)}
      </tbody>
    </table>}
    {changeRole.isError && !opened && <p className="directory-note">{changeRole.error.message}</p>}
    {opened && <MemberDialog
      name={opened.display_name}
      userKey={opened.user_key}
      pending={changeRole.isPending}
      error={changeRole.isError ? changeRole.error.message : undefined}
      memberships={opened.memberships.filter((membership) => orgFilter === "all" || membership.organization_id === orgFilter).map((membership): DialogMembership => {
        const caller = adminOrgs.find((item) => item.organization_id === membership.organization_id);
        return {
          organizationId: membership.organization_id,
          organizationName: membership.organization_name,
          role: membership.role,
          options: caller ? rolesFor(caller) : [],
          editable: Boolean(caller) && membership.role !== "super_admin" && opened.user_id !== principal.data?.data.user_id,
        };
      })}
      onClose={() => setOpened(null)}
      onConfirm={(changes) => changeRole.mutate({ userId: opened.user_id, changes })}
    />}
  </div>;
}

export default function MembersRoute() {
  return <Suspense fallback={<LoadingState label="Chargement des membres…" />}><MembersPage /></Suspense>;
}
