"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Popup } from "@/components/member-dialog";
import { ErrorState, LoadingState, PageHeading } from "@/components/ui";
import type { Organization } from "@/types/api";

export default function OrganizationsPage() {
  const queryClient = useQueryClient();
  const organizations = useQuery({ queryKey: ["organizations"], queryFn: () => api.organizations() });
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [confirmCreate, setConfirmCreate] = useState(false);
  const create = useMutation({
    mutationFn: () => api.createOrganization(name.trim()),
    onSuccess: async (result) => {
      setNote(`${result.data.name} est créée.`);
      setName("");
      setAdding(false);
      setConfirmCreate(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["organizations"] }),
        queryClient.invalidateQueries({ queryKey: ["principal"] }),
      ]);
    },
  });

  return <div className="page-stack">
    <PageHeading title="Organisations" description="Cliquez une organisation pour voir ses comptes." actions={<button type="button" className="button button-secondary" onClick={() => { setNote(""); setConfirmCreate(false); setAdding(true); }}>Ajouter</button>} />
    {note && <p className="directory-note">{note}</p>}
    {adding && <Popup title={confirmCreate ? "Confirmer l’organisation" : "Nouvelle organisation"} onClose={() => { setAdding(false); setConfirmCreate(false); setName(""); }}>
      {confirmCreate ? <>
        <p>Créer l’organisation « {name.trim()} » ?</p>
        {create.isError && <p className="member-dialog-error">{create.error.message}</p>}
        <button type="button" className="member-dialog-submit" disabled={create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Confirmation…" : "Confirmer"}</button>
        <button type="button" className="member-dialog-back" onClick={() => setConfirmCreate(false)}>Revenir</button>
      </> : <form onSubmit={(event) => { event.preventDefault(); if (name.trim()) setConfirmCreate(true); }}>
        <label>Nom<input value={name} onChange={(event) => setName(event.target.value)} maxLength={200} required autoFocus placeholder="Ex. Organisation C" /></label>
        {create.isError && <p className="member-dialog-error">{create.error.message}</p>}
        <button className="member-dialog-submit" disabled={!name.trim()}>Continuer</button>
      </form>}
    </Popup>}
    {organizations.isLoading ? <LoadingState /> : organizations.isError ? <ErrorState error={organizations.error} onRetry={() => void organizations.refetch()} /> : <table className="directory">
      <thead><tr><th>Organisation</th></tr></thead>
      <tbody>
        {organizations.data?.data.map((organization: Organization) => <tr key={organization.id}>
          <td><Link href={`/organizations/${organization.id}`}>{organization.name}</Link></td>
        </tr>)}
      </tbody>
    </table>}
  </div>;
}
