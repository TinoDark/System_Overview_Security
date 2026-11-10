"use client";

import Link from "next/link";
import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Search, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { DataTable, ErrorState, formatDate, LoadingState, PageHeading, SeverityBadge, StatusBadge } from "@/components/ui";
import type { Incident, IncidentStatus, Severity } from "@/types/api";

export default function IncidentsPage() {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const query = useInfiniteQuery({
    queryKey: ["incidents", { severity, status }],
    queryFn: ({ pageParam }) => api.incidents({ severity: severity || undefined, status: status || undefined, limit: 100, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.meta.next_cursor ?? undefined,
  });
  const rows = (query.data?.pages.flatMap((page) => page.data) ?? []).filter((incident) => `${incident.title} ${incident.description ?? ""} ${incident.id}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="page-stack">
    <PageHeading eyebrow="TRIAGE ET RÉPONSE" title="Incidents" description="Analysez les détections corrélées et suivez leur cycle de vie." />
    <div className="filter-bar"><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un incident…" /></label>
      <select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">Toutes sévérités</option>{(["critical", "high", "medium", "low", "info"] as Severity[]).map((item) => <option key={item} value={item}>{item}</option>)}</select>
      <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Tous les statuts</option>{(["new", "in_progress", "resolved", "closed"] as IncidentStatus[]).map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select>
      <span className="result-count">{query.isSuccess ? `${rows.length} résultat${rows.length > 1 ? "s" : ""}` : " "}</span></div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">FILE D’INVESTIGATION</div><h2><ShieldAlert size={18} /> Incidents du tenant</h2></div></div>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> :
        <DataTable headers={["Incident", "Sévérité", "Risque", "Statut", "Événements", "Créé le", ""]} empty={!rows.length}>{rows.map((incident: Incident) =>
          <tr key={incident.id}><td><Link className="table-primary-link" href={`/incidents/${incident.id}`}>{incident.title}</Link><span className="table-subtext">{incident.id}</span></td><td><SeverityBadge severity={incident.severity} /></td>
            <td><span className="risk-score">{incident.risk_score}<small>/100</small></span></td><td><StatusBadge value={incident.status} /></td><td>{incident.event_ids?.length ?? 0}</td><td>{formatDate(incident.created_at)}</td><td><Link className="row-action" href={`/incidents/${incident.id}`}>Détails <span>→</span></Link></td></tr>)}</DataTable>}
      {query.hasNextPage && <button className="button button-secondary load-more" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>{query.isFetchingNextPage ? "Chargement…" : "Charger la page suivante"}</button>}
    </section>
  </div>;
}
