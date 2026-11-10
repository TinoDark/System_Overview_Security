"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertOctagon, ArrowUpRight, Boxes, Radio, ShieldAlert, Timer } from "lucide-react";
import { api } from "@/lib/api";
import { EmptyState, ErrorState, formatDate, LoadingState, MetricCard, PageHeading, SeverityBadge, SimulationBadge, StatusBadge } from "@/components/ui";
import type { Incident, Integration } from "@/types/api";

export default function DashboardPage() {
  const summary = useQuery({ queryKey: ["dashboard", "summary"], queryFn: () => api.summary() });
  const timeline = useQuery({ queryKey: ["dashboard", "timeline"], queryFn: () => api.timeline() });
  const incidents = useQuery({ queryKey: ["incidents", "dashboard"], queryFn: () => api.incidents({ limit: 100 }) });
  const integrations = useQuery({ queryKey: ["integrations"], queryFn: () => api.integrations() });
  const metrics = summary.data?.data;
  const recentTimeline = timeline.data?.data ?? [];
  const topIncidents = (incidents.data?.data ?? []).filter((incident) => incident.status === "new" || incident.status === "in_progress").slice(0, 5);
  const connectors = integrations.data?.data ?? [];

  return <div className="page-stack">
    <PageHeading eyebrow="CENTRE DE COMMANDEMENT" title="Vue d’ensemble" description="Surveillez les signaux et l’activité de votre organisation." actions={<SimulationBadge />} />
    {summary.isLoading ? <LoadingState /> : summary.isError ? <ErrorState error={summary.error} onRetry={() => void summary.refetch()} /> :
      <div className="metric-grid">
        <MetricCard label="Événements · 24 h" value={metrics?.events_24h ?? "—"} note="Agrégation API" icon={<Activity size={19} />} />
        <MetricCard label="Incidents ouverts" value={metrics?.incidents_open ?? "—"} note="Nouveaux et en cours" icon={<ShieldAlert size={19} />} tone="amber" />
        <MetricCard label="Alertes critiques" value={metrics?.incidents_critical ?? "—"} note="Priorité immédiate" icon={<AlertOctagon size={19} />} tone="red" />
        <MetricCard label="Connecteurs actifs" value={metrics?.active_integrations ?? "—"} note="État fourni par l’API" icon={<Radio size={19} />} tone="green" />
      </div>}
    <div className="dashboard-grid">
      <section className="panel timeline-panel"><div className="panel-heading"><div><div className="eyebrow">OBSERVABILITÉ</div><h2>Activité récente</h2></div><Timer size={18} className="muted-icon" /></div>
        {timeline.isLoading ? <LoadingState /> : timeline.isError ? <ErrorState error={timeline.error} onRetry={() => void timeline.refetch()} /> : recentTimeline.length ?
          <div className="timeline-list">{recentTimeline.slice(-8).reverse().map((entry, index) => {
            const label = String(entry.label ?? entry.event_type ?? entry.bucket ?? "Activité");
            const count = entry.count ?? entry.total ?? entry.value;
            const time = entry.timestamp ?? entry.occurred_at ?? entry.time;
            return <div className="timeline-row" key={String(entry.id ?? `${label}-${index}`)}><span className="timeline-point" /><div className="timeline-row-copy"><strong>{label}</strong><span>{time ? formatDate(String(time)) : "Période agrégée"}</span></div><span className="timeline-count">{typeof count === "number" ? count : "—"}</span></div>;
          })}</div> : <EmptyState title="Aucune activité" description="La timeline sera renseignée à partir des événements du tenant." />}
      </section>
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">À TRAITER</div><h2>Incidents prioritaires</h2></div><Link href="/incidents" className="text-link">Tout voir <ArrowUpRight size={14} /></Link></div>
        {incidents.isLoading ? <LoadingState /> : incidents.isError ? <ErrorState error={incidents.error} onRetry={() => void incidents.refetch()} /> : topIncidents.length ?
          <div className="priority-list">{topIncidents.slice(0, 5).map((incident: Incident) => <Link className="priority-item" href={`/incidents/${incident.id}`} key={incident.id}>
            <div className="priority-mark"><AlertOctagon size={16} /></div><div className="priority-copy"><strong>{incident.title}</strong><span>{incident.risk_score} risk score · {formatDate(incident.created_at)}</span></div><SeverityBadge severity={incident.severity} />
          </Link>)}</div> : <EmptyState title="Aucun incident ouvert" description="Le backend ne signale aucun incident à traiter." />}
      </section>
      <section className="panel connector-panel"><div className="panel-heading"><div><div className="eyebrow">SOURCES DE DONNÉES</div><h2>État des connecteurs</h2></div><Link href="/integrations" className="text-link">Gérer <ArrowUpRight size={14} /></Link></div>
        {integrations.isLoading ? <LoadingState /> : integrations.isError ? <ErrorState error={integrations.error} onRetry={() => void integrations.refetch()} /> : connectors.length ?
          <div className="connector-list">{connectors.slice(0, 4).map((connector: Integration) => <div className="connector-item" key={connector.id}><div className="connector-symbol"><Boxes size={16} /></div><div className="connector-copy"><strong>{connector.name}</strong><span>{connector.provider ?? connector.type ?? "Mock provider"}</span></div><StatusBadge value={connector.status ?? (connector.enabled ? "active" : "inactive")} /><SimulationBadge subtle /></div>)}</div> : <EmptyState title="Aucun connecteur configuré" description="Les intégrations présentes seront chargées depuis l’API." />}
      </section>
      <section className="panel posture-panel"><div className="eyebrow">PÉRIMÈTRE</div><h2>Actifs surveillés</h2><div className="posture-value">{metrics?.total_assets ?? "—"}<span> actifs</span></div><p>Inventaire provenant du tenant actif.</p><Link className="text-link" href="/assets">Ouvrir l’inventaire <ArrowUpRight size={14} /></Link></section>
    </div>
  </div>;
}
