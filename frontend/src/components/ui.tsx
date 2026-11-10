"use client";

import type { ReactNode } from "react";
import { AlertCircle, LoaderCircle, Radio, ShieldCheck } from "lucide-react";
import type { Severity } from "@/types/api";

export function PageHeading({ eyebrow, title, description, actions }: {
  eyebrow?: string; title: string; description?: string; actions?: ReactNode;
}) {
  return <div className="page-heading">
    <div><div className="eyebrow">{eyebrow ?? "SECURITY OPERATIONS"}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>
    {actions && <div className="heading-actions">{actions}</div>}
  </div>;
}

export function SimulationBadge({ subtle = false }: { subtle?: boolean }) {
  return <span className={`simulation-badge${subtle ? " subtle" : ""}`}><Radio size={12} /> SIMULATION</span>;
}

export function SeverityBadge({ severity }: { severity?: Severity | string }) {
  const value = (severity ?? "unknown").toLowerCase();
  return <span className={`severity severity-${value}`}>{value}</span>;
}

export function StatusBadge({ value }: { value?: string }) {
  const text = value ?? "unknown";
  return <span className={`status status-${text.toLowerCase().replaceAll("_", "-")}`}>{text.replaceAll("_", " ")}</span>;
}

export function LoadingState({ label = "Chargement des données…" }: { label?: string }) {
  return <div className="state-card"><LoaderCircle className="spin" size={20} /><span>{label}</span></div>;
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Une erreur inattendue est survenue.";
  return <div className="state-card state-error"><AlertCircle size={20} /><div><strong>Impossible de charger les données</strong><p>{message}</p>{onRetry && <button className="button button-secondary button-small" onClick={onRetry}>Réessayer</button>}</div></div>;
}

export function EmptyState({ title = "Aucun résultat", description = "Aucune donnée ne correspond à cette vue." }: { title?: string; description?: string }) {
  return <div className="empty-state"><div className="empty-icon"><ShieldCheck size={23} /></div><strong>{title}</strong><p>{description}</p></div>;
}

export function MetricCard({ label, value, note, icon, tone }: {
  label: string; value: string | number; note?: string; icon: ReactNode; tone?: "blue" | "amber" | "red" | "green";
}) {
  return <article className="metric-card"><div className={`metric-icon tone-${tone ?? "blue"}`}>{icon}</div>
    <div className="metric-label">{label}</div><div className="metric-value">{value}</div>{note && <div className="metric-note">{note}</div>}</article>;
}

export function DataTable({ headers, children, empty }: { headers: string[]; children: ReactNode; empty?: boolean }) {
  return <div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
    <tbody>{empty ? <tr><td colSpan={headers.length}><EmptyState /></td></tr> : children}</tbody></table></div>;
}

export function ErrorNotice({ children }: { children: ReactNode }) {
  return <div className="notice notice-error"><AlertCircle size={17} />{children}</div>;
}

export function formatDate(value?: string): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
