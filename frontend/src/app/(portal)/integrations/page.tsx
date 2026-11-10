"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable, Play, RefreshCw } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, ErrorNotice, ErrorState, formatDate, LoadingState, PageHeading, SimulationBadge, StatusBadge } from "@/components/ui";
import type { Integration } from "@/types/api";

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState("");
  const integrations = useQuery({ queryKey: ["integrations"], queryFn: () => api.integrations() });
  const collect = useMutation({ mutationFn: (id: string) => api.collect(id), onSuccess: async (result) => {
    const run = result.data;
    setFeedback(`Collecte ${run.status} · ${run.received} reçus, ${run.inserted} insérés, ${run.duplicates} doublons, ${run.incidents_created} incidents créés.`);
    await queryClient.invalidateQueries({ queryKey: ["integrations"] });
    await queryClient.invalidateQueries({ queryKey: ["events"] });
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  } });
  const connectors = integrations.data?.data ?? [];
  return <div className="page-stack"><PageHeading eyebrow="SOURCES DE DÉTECTION" title="Intégrations" description="Consultez les providers mock et lancez une collecte déterministe via l’API." actions={<SimulationBadge />} />
    {feedback && <div className="notice notice-success"><RefreshCw size={16} />{feedback}<button className="notice-dismiss" onClick={() => setFeedback("")}>×</button></div>}
    {collect.isError && <ErrorNotice>{collect.error.message}</ErrorNotice>}
    <div className="integration-grid">{integrations.isLoading ? <LoadingState /> : integrations.isError ? <ErrorState error={integrations.error} onRetry={() => void integrations.refetch()} /> : connectors.length ?
      connectors.map((integration: Integration) => <article className="integration-card" key={integration.id}><div className="integration-card-head"><div className="connector-symbol large"><Cable size={19} /></div><StatusBadge value={integration.status ?? (integration.enabled ? "active" : "inactive")} /></div>
        <div className="eyebrow">{integration.integration_type.replace("mock_", "").toUpperCase()}</div><h2>{integration.name}</h2><p className="integration-id">{integration.id}</p>
        <div className="integration-meta"><span><span className="status-dot" /> Dernière collecte</span><strong>{formatDate(integration.last_collected_at ?? undefined)}</strong></div>
        <div className="integration-meta"><span>Événements reçus</span><strong>{integration.events_received ?? "—"}</strong></div>
        <div className="integration-footer"><SimulationBadge subtle /><button className="button button-secondary button-small" disabled={collect.isPending || integration.enabled === false} onClick={() => collect.mutate(integration.id)}><Play size={14} /> Collecter</button></div>
      </article>) : <div className="panel"><EmptyState title="Aucune intégration" description="Le backend n’a pas encore enregistré de provider mock pour ce tenant." /></div>}
    </div>
    <div className="inline-note">Les providers et leur état sont lus depuis l’API. Aucun appel réseau vers Wazuh, Rspamd, ClamAV ou MISP n’est effectué.</div>
  </div>;
}
