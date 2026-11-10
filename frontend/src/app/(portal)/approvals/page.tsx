"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ClipboardCheck, X } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { DataTable, ErrorNotice, ErrorState, formatDate, LoadingState, PageHeading, SimulationBadge, StatusBadge } from "@/components/ui";
import type { Approval } from "@/types/api";

export default function ApprovalsPage() {
  const client = useQueryClient();
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const approvals = useQuery({ queryKey: ["approvals"], queryFn: () => api.approvals() });
  const decision = useMutation({
    mutationFn: ({ id, choice, justification }: { id: string; choice: "approve" | "reject"; justification: string }) => api.decideApproval(id, choice, justification),
    onSuccess: async (_data, variables) => {
      setFeedback(`Décision « ${variables.choice === "approve" ? "approuvée" : "refusée"} » transmise à l’API.`);
      await client.invalidateQueries({ queryKey: ["approvals"] });
      await client.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
  const rows = approvals.data?.data ?? [];
  return <div className="page-stack"><PageHeading eyebrow="SÉPARATION DES RÔLES" title="Approbations" description="Examinez les demandes en attente et transmettez une décision justifiée." actions={<SimulationBadge />} />
    <div className="notice notice-info"><ClipboardCheck size={17} />Le backend valide le rôle, l’expiration et la séparation demandeur/décideur. L’interface ne fait qu’exposer le parcours.</div>
    {feedback && <div className="notice notice-success"><Check size={16} />{feedback}<button className="notice-dismiss" onClick={() => setFeedback("")}>×</button></div>}
    {decision.isError && <ErrorNotice>{decision.error.message}</ErrorNotice>}
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">DEMANDES DE RÉPONSE</div><h2>File d’approbation</h2></div></div>
      {approvals.isLoading ? <LoadingState /> : approvals.isError ? <ErrorState error={approvals.error} onRetry={() => void approvals.refetch()} /> :
        <DataTable headers={["Incident", "Demandeur", "Statut", "Expire le", "Justification / décision"]} empty={!rows.length}>{rows.map((approval: Approval) => <ApprovalRow key={approval.id} approval={approval}
          justification={justifications[approval.id] ?? ""} onChange={(value) => setJustifications((current) => ({ ...current, [approval.id]: value }))}
          onDecide={(choice) => decision.mutate({ id: approval.id, choice, justification: (justifications[approval.id] ?? "").trim() })} pending={decision.isPending} />)}</DataTable>}
    </section>
  </div>;
}

function ApprovalRow({ approval, justification, onChange, onDecide, pending }: {
  approval: Approval; justification: string; onChange: (value: string) => void; onDecide: (choice: "approve" | "reject") => void; pending: boolean;
}) {
  const pendingApproval = approval.status === "pending";
  return <tr><td><span className="table-primary">{approval.incident_id}</span><span className="table-subtext">Réponse {approval.response_id}</span></td><td>{approval.requested_by}</td><td><StatusBadge value={approval.status} /></td><td>{formatDate(approval.expires_at)}</td>
    <td>{pendingApproval ? <div className="approval-controls"><input aria-label="Justification obligatoire" value={justification} onChange={(event) => onChange(event.target.value)} placeholder="Justification requise…" />
      <button className="button button-success button-small" disabled={pending || !justification.trim()} onClick={() => onDecide("approve")} title="Approuver"><Check size={14} /></button>
      <button className="button button-danger button-small" disabled={pending || !justification.trim()} onClick={() => onDecide("reject")} title="Refuser"><X size={14} /></button></div> : <span className="muted-copy">{approval.justification ?? "Décision enregistrée"}</span>}</td></tr>;
}
