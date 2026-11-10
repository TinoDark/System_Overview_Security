"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, MessageSquare, Play, Send, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { ErrorNotice, ErrorState, formatDate, LoadingState, PageHeading, SeverityBadge, SimulationBadge, StatusBadge } from "@/components/ui";
import type { IncidentStatus } from "@/types/api";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [justification, setJustification] = useState("");
  const [message, setMessage] = useState("");
  const detail = useQuery({ queryKey: ["incident", id], queryFn: () => api.incident(id), enabled: Boolean(id) });
  const responseId = detail.data?.data.response_id;
  const responseQuery = useQuery({
    queryKey: ["response", responseId],
    queryFn: () => api.response(responseId!),
    enabled: Boolean(responseId),
  });
  const invalidate = async () => { await queryClient.invalidateQueries({ queryKey: ["incident", id] }); await queryClient.invalidateQueries({ queryKey: ["incidents"] }); };
  const statusMutation = useMutation({ mutationFn: (status: IncidentStatus) => api.changeIncidentStatus(id, status, justification || undefined), onSuccess: async () => { setMessage("Statut mis à jour."); setJustification(""); await invalidate(); } });
  const commentMutation = useMutation({ mutationFn: (body: string) => api.addIncidentComment(id, body), onSuccess: async () => { setComment(""); setMessage("Commentaire transmis à l’API."); await invalidate(); } });
  const dryRunMutation = useMutation({ mutationFn: (targetId: string) => api.responseAction(targetId, "dry-run"), onSuccess: async (result) => {
    setMessage(result.data.result?.message ?? "Simulation dry-run transmise à l’API.");
    await queryClient.invalidateQueries({ queryKey: ["response", responseId] });
  } });
  const executeMutation = useMutation({ mutationFn: (targetId: string) => api.responseAction(targetId, "execute", responseQuery.data?.data.idempotency_key), onSuccess: async (result) => {
    setMessage(result.data.result?.message ?? "Demande d’exécution simulée transmise à l’API.");
    await queryClient.invalidateQueries({ queryKey: ["response", responseId] });
    await invalidate();
  } });
  const incident = detail.data?.data;

  if (detail.isLoading) return <div className="page-stack"><LoadingState /></div>;
  if (detail.isError) return <div className="page-stack"><Link href="/incidents" className="back-link"><ArrowLeft size={16} /> Retour aux incidents</Link><ErrorState error={detail.error} onRetry={() => void detail.refetch()} /></div>;
  if (!incident) return null;
  const nextStatus: Partial<Record<IncidentStatus, IncidentStatus>> = { new: "in_progress", in_progress: "resolved", resolved: "closed" };
  const next = nextStatus[incident.status];
  const mutationError = statusMutation.error ?? commentMutation.error ?? dryRunMutation.error ?? executeMutation.error;

  return <div className="page-stack">
    <Link href="/incidents" className="back-link"><ArrowLeft size={16} /> Tous les incidents</Link>
    <PageHeading eyebrow={`INCIDENT · ${incident.id.slice(0, 8)}`} title={incident.title} description={incident.description ?? "Investigation de sécurité — détails fournis par l’API."} actions={<SimulationBadge />} />
    {message && <div className="notice notice-success"><Check size={16} />{message}<button className="notice-dismiss" onClick={() => setMessage("")}>×</button></div>}
    {mutationError && <ErrorNotice>{mutationError.message}</ErrorNotice>}
    {responseQuery.isError && <ErrorNotice>{responseQuery.error.message}</ErrorNotice>}
    <div className="incident-overview">
      <section className="panel incident-summary"><div className="eyebrow">SYNTHÈSE</div><div className="incident-badges"><SeverityBadge severity={incident.severity} /><StatusBadge value={incident.status} /></div>
        <div className="risk-meter"><div className="risk-meter-top"><span>Score de risque</span><strong>{incident.risk_score}<small> / 100</small></strong></div><div className="risk-track"><span style={{ width: `${Math.min(incident.risk_score, 100)}%` }} /></div></div>
        <dl className="detail-list"><div><dt>Créé</dt><dd>{formatDate(incident.created_at)}</dd></div><div><dt>Mis à jour</dt><dd>{formatDate(incident.updated_at)}</dd></div><div><dt>Assigné à</dt><dd>{incident.assigned_to ?? "Non assigné"}</dd></div><div><dt>Événements liés</dt><dd>{incident.event_ids?.length ?? 0}</dd></div></dl>
        {next && <div className="action-block"><label htmlFor="justification">Justification (requise pour la clôture)</label><textarea id="justification" value={justification} onChange={(event) => setJustification(event.target.value)} placeholder="Contexte ou justification…" />
          <button className="button button-primary" disabled={statusMutation.isPending || (next === "closed" && !justification.trim())} onClick={() => statusMutation.mutate(next)}>Passer à « {next.replaceAll("_", " ")} »</button></div>}
      </section>
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">ANALYSE</div><h2>Facteurs de risque</h2></div></div>
        {incident.risk_factors?.length ? <div className="factor-list">{incident.risk_factors.map((factor, index) => <div className="factor-row" key={`${factor.code}-${index}`}><div className="factor-score">+{factor.contribution}</div><div><strong>{factor.code.replaceAll("_", " ")}</strong><p>{factor.explanation}</p></div></div>)}</div> : <div className="muted-copy">Aucun facteur explicite fourni par le backend.</div>}
        <div className="linked-events"><h3>Événements liés</h3>{incident.event_ids?.length ? incident.event_ids.map((eventId) => <Link key={eventId} className="linked-event" href={`/events?event=${encodeURIComponent(eventId)}`}><span className="timeline-point" /><span>{eventId}</span><span>Ouvrir →</span></Link>) : <p className="muted-copy">Aucun événement lié.</p>}</div>
      </section>
    </div>
    <div className="detail-grid">
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">COLLABORATION</div><h2><MessageSquare size={17} /> Commentaires</h2></div></div>
        <div className="comment-list">{incident.comments?.length ? incident.comments.map((item) => <div className="comment-row" key={item.id}><div className="avatar">{(item.author ?? "A").slice(0, 1).toUpperCase()}</div><div><div className="comment-meta"><strong>{item.author ?? "Analyste"}</strong><span>{formatDate(item.created_at)}</span></div><p>{item.body}</p></div></div>) : <p className="muted-copy">Aucun commentaire transmis.</p>}</div>
        <form className="comment-form" onSubmit={(event) => { event.preventDefault(); if (comment.trim()) commentMutation.mutate(comment.trim()); }}><textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Ajouter un commentaire…" /><button className="button button-primary" disabled={commentMutation.isPending || !comment.trim()}><Send size={15} /> Envoyer</button></form>
      </section>
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">RÉPONSE CONTRÔLÉE</div><h2><ShieldCheck size={17} /> Actions simulées</h2></div><SimulationBadge subtle /></div>
        <p className="muted-copy">Les actions sont transmises à l’API. L’interface ne remplace jamais ses contrôles d’autorisation ou son kill switch.</p>
        {incident.approval && <div className="approval-mini"><span>Approbation</span><StatusBadge value={incident.approval.status} /><span>{incident.approval.id}</span></div>}
        {incident.response_id && responseQuery.isLoading && <LoadingState label="Chargement de la réponse…" />}
        {responseQuery.data && <div className="approval-mini"><span>Réponse</span><StatusBadge value={responseQuery.data.data.status} /><span>{responseQuery.data.data.result?.message ?? responseQuery.data.data.id}</span></div>}
        {incident.response_id ? <div className="response-actions"><button className="button button-secondary" disabled={dryRunMutation.isPending} onClick={() => dryRunMutation.mutate(incident.response_id!)}><Play size={15} /> Dry-run</button>
          <button className="button button-danger" disabled={executeMutation.isPending || responseQuery.isLoading || !responseQuery.data?.data.idempotency_key} onClick={() => executeMutation.mutate(incident.response_id!)}>Exécuter la simulation</button></div> :
          <div className="inline-note">Aucune réponse associée disponible dans le détail API.</div>}
        <p className="microcopy">« Exécuter » ne contacte aucun outil réel depuis le frontend. L’API reste l’autorité et peut refuser la requête.</p>
      </section>
    </div>
  </div>;
}
