"use client";

import { useEffect, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Activity, Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { DataTable, ErrorState, formatDate, LoadingState, PageHeading, SeverityBadge, SimulationBadge } from "@/components/ui";
import type { SecurityEvent, Severity } from "@/types/api";

export default function EventsPage() {
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [severity, setSeverity] = useState("");
  const [selectedId, setSelectedId] = useState("");
  useEffect(() => {
    setSelectedId(new URLSearchParams(window.location.search).get("event") ?? "");
  }, []);
  const events = useInfiniteQuery({
    queryKey: ["events", { source, severity }],
    queryFn: ({ pageParam }) => api.events({ source: source || undefined, severity: severity || undefined, limit: 100, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.meta.next_cursor ?? undefined,
  });
  const detail = useQuery({ queryKey: ["event", selectedId], queryFn: () => api.event(selectedId), enabled: Boolean(selectedId) });
  const rows = (events.data?.pages.flatMap((page) => page.data) ?? []).filter((event) => `${event.message} ${event.external_event_id} ${event.event_type} ${event.asset?.hostname ?? ""} ${event.asset?.ip_address ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="page-stack">
    <PageHeading eyebrow="TÉLÉMÉTRIE NORMALISÉE" title="Événements" description="Recherchez et inspectez les événements collectés pour le tenant actif." actions={<SimulationBadge />} />
    <div className="filter-bar"><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher dans les événements…" /></label>
      <select value={source} onChange={(event) => setSource(event.target.value)}><option value="">Toutes les sources</option>{["wazuh", "rspamd", "clamav", "misp"].map((item) => <option key={item}>{item}</option>)}</select>
      <select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">Toutes sévérités</option>{(["critical", "high", "medium", "low", "info"] as Severity[]).map((item) => <option key={item}>{item}</option>)}
      </select><span className="result-count">{events.isSuccess ? `${rows.length} événement${rows.length > 1 ? "s" : ""}` : ""}</span></div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">JOURNAL DES SIGNAUX</div><h2><Activity size={18} /> Flux d’événements</h2></div></div>
      {events.isLoading ? <LoadingState /> : events.isError ? <ErrorState error={events.error} onRetry={() => void events.refetch()} /> :
        <DataTable headers={["Événement", "Sévérité", "Source", "Actif", "Type", "Horodatage", ""]} empty={!rows.length}>{rows.map((event: SecurityEvent) =>
          <tr key={event.event_id}><td><button className="table-primary-link button-as-link" onClick={() => setSelectedId(event.event_id)}>{event.message}</button><span className="table-subtext">{event.external_event_id}</span></td><td><SeverityBadge severity={event.severity} /></td>
            <td><span className="source-label">{event.source}</span>{event.is_simulated && <SimulationBadge subtle />}</td><td>{event.asset?.hostname ?? event.asset?.ip_address ?? "—"}</td><td>{event.event_type}</td><td>{formatDate(event.occurred_at)}</td><td><button className="row-action" onClick={() => setSelectedId(event.event_id)}>Inspecter <span>→</span></button></td></tr>)}</DataTable>}
      {events.hasNextPage && <button className="button button-secondary load-more" disabled={events.isFetchingNextPage} onClick={() => void events.fetchNextPage()}>{events.isFetchingNextPage ? "Chargement…" : "Charger la page suivante"}</button>}
    </section>
    {selectedId && <div className="modal-backdrop" onClick={() => setSelectedId("")}><section className="event-drawer" onClick={(event) => event.stopPropagation()}>
      <div className="drawer-heading"><div><div className="eyebrow">ÉVÉNEMENT · DÉTAIL API</div><h2>Inspection</h2></div><button className="icon-button" onClick={() => setSelectedId("")} aria-label="Fermer"><X size={18} /></button></div>
      {detail.isLoading ? <LoadingState /> : detail.isError ? <ErrorState error={detail.error} onRetry={() => void detail.refetch()} /> : detail.data && <EventDetails event={detail.data.data} />}
    </section></div>}
  </div>;
}

function EventDetails({ event }: { event: SecurityEvent }) {
  return <><div className="incident-badges"><SeverityBadge severity={event.severity} />{event.is_simulated && <SimulationBadge />}</div>
    <h3 className="event-message">{event.message}</h3>
    <dl className="detail-list"><div><dt>Source</dt><dd>{event.source}</dd></div><div><dt>Type</dt><dd>{event.event_type}</dd></div><div><dt>Horodatage</dt><dd>{formatDate(event.occurred_at)}</dd></div><div><dt>Actif</dt><dd>{event.asset?.hostname ?? event.asset?.ip_address ?? "—"}</dd></div><div><dt>Utilisateur</dt><dd>{event.actor?.username ?? "—"}</dd></div><div><dt>Version schéma</dt><dd>{event.schema_version ?? "—"}</dd></div></dl>
    {event.indicators?.length ? <div className="indicator-list"><h3>Indicateurs</h3>{event.indicators.map((indicator, index) => <div key={`${indicator.type}-${index}`}><span>{indicator.type}</span><code>{indicator.value}</code></div>)}</div> : null}
    <details className="raw-details"><summary>Payload normalisé</summary><pre>{JSON.stringify(event.raw_event ?? event, null, 2)}</pre></details>
  </>;
}
