"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { DataTable, ErrorState, LoadingState, PageHeading, SeverityBadge, SimulationBadge, StatusBadge } from "@/components/ui";
import type { Policy } from "@/types/api";

export default function PoliciesPage() {
  const query = useQuery({ queryKey: ["policies"], queryFn: () => api.policies() });
  const policies = query.data?.data ?? [];
  return <div className="page-stack"><PageHeading eyebrow="GARDE-FOUS DE RÉPONSE" title="Politiques" description="Règles de réponse déclaratives, désactivées par défaut et gérées par l’API." actions={<SimulationBadge />} />
    <div className="notice notice-info"><ShieldCheck size={17} />Les politiques autorisent uniquement <code>simulate_containment</code>. Leur visibilité dans l’interface ne confère aucun droit d’exécution.</div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">RÈGLES CONFIGURÉES</div><h2><FileText size={18} /> Politiques du tenant</h2></div></div>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> :
        <DataTable headers={["Nom", "État", "Sévérité minimum", "Score minimum", "Action", "Approbation"]} empty={!policies.length}>{policies.map((policy: Policy) =>
          <tr key={policy.id}><td><span className="table-primary">{policy.name}</span><span className="table-subtext">{policy.id}</span></td><td><StatusBadge value={policy.enabled ? "enabled" : "disabled"} /></td>
            <td>{policy.trigger_min_severity ? <SeverityBadge severity={policy.trigger_min_severity} /> : "—"}</td><td>{policy.trigger_min_score ?? "—"}</td><td><code>{policy.action_type}</code></td><td>{policy.approval_required ? "Requise" : "Non"}</td></tr>)}</DataTable>}
    </section>
    <div className="inline-note">La gestion/édition des règles est limitée à l’API disponible. Cette vue n’affiche aucune politique fixture locale.</div>
  </div>;
}
