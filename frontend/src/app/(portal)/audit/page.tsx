"use client";

import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { FileClock, Search } from "lucide-react";
import { api } from "@/lib/api";
import { DataTable, ErrorState, formatDate, LoadingState, PageHeading, StatusBadge } from "@/components/ui";
import type { AuditEntry } from "@/types/api";

export default function AuditPage() {
  const [action, setAction] = useState("");
  const query = useInfiniteQuery({
    queryKey: ["audit"],
    queryFn: ({ pageParam }) => api.audit({ limit: 100, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.meta.next_cursor ?? undefined,
  });
  const entries = (query.data?.pages.flatMap((page) => page.data) ?? []).filter((entry) => `${entry.action} ${entry.resource_type} ${entry.actor_user_id ?? ""}`.toLowerCase().includes(action.toLowerCase()));
  return <div className="page-stack"><PageHeading eyebrow="TRAÇABILITÉ APPEND-ONLY" title="Audit" description="Historique des actions exposé par le backend, filtré par organisation." />
    <div className="filter-bar"><label className="search-field"><Search size={16} /><input value={action} onChange={(event) => setAction(event.target.value)} placeholder="Filtrer par action…" /></label><span className="result-count">{query.isSuccess ? `${entries.length} entrées` : ""}</span></div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">JOURNAL D’ACTIVITÉ</div><h2><FileClock size={18} /> Événements d’audit</h2></div></div>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> :
        <DataTable headers={["Horodatage", "Acteur", "Action", "Ressource", "Résultat", "Correlation ID"]} empty={!entries.length}>{entries.map((entry: AuditEntry) =>
          <tr key={entry.id}><td>{formatDate(entry.created_at)}</td><td><code>{entry.actor_user_id ?? "Système"}</code></td><td className="table-primary">{entry.action}</td><td>{entry.resource_type}{entry.resource_id && <span className="table-subtext">{entry.resource_id}</span>}</td>
            <td><StatusBadge value={entry.outcome} /></td><td><code>{entry.correlation_id ?? "—"}</code></td></tr>)}</DataTable>}
      {query.hasNextPage && <button className="button button-secondary load-more" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{query.isFetchingNextPage ? "Chargement…" : "Charger la page suivante"}</button>}
    </section>
    <div className="inline-note">Les métadonnées d’audit expurgées ne sont pas développées ni enrichies côté navigateur.</div>
  </div>;
}
