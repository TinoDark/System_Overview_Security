"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity, AlertTriangle, Boxes, ChevronDown, ClipboardCheck, FileClock,
  FileText, LayoutDashboard, LogOut, Menu, Network, Search, Shield,
  ShieldAlert, X,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  api,
  clearToken,
  getOrganizationId,
  getToken,
  saveLogoutWarning,
  saveOrganizationId,
} from "@/lib/api";
import type { Membership } from "@/types/api";
import { ErrorState, LoadingState, SimulationBadge } from "./ui";

const navigation = [
  { label: "Vue d’ensemble", href: "/dashboard", icon: LayoutDashboard },
  { label: "Incidents", href: "/incidents", icon: ShieldAlert },
  { label: "Événements", href: "/events", icon: Activity },
  { label: "Actifs", href: "/assets", icon: Boxes },
  { label: "Intégrations", href: "/integrations", icon: Network },
  { label: "Politiques", href: "/policies", icon: FileText },
  { label: "Approbations", href: "/approvals", icon: ClipboardCheck },
  { label: "Audit", href: "/audit", icon: FileClock },
];

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const tokenPresent = typeof window !== "undefined" && Boolean(getToken());
  const principalQuery = useQuery({
    queryKey: ["principal"],
    queryFn: () => api.me(),
    enabled: tokenPresent,
    retry: false,
  });

  useEffect(() => { setOrganizationId(getOrganizationId()); }, []);
  useEffect(() => {
    if (!tokenPresent) router.replace("/login");
  }, [router, tokenPresent]);

  if (!tokenPresent) return <div className="auth-loading"><LoadingState label="Redirection vers la connexion…" /></div>;
  if (principalQuery.isLoading) return <div className="auth-loading"><LoadingState label="Vérification de la session…" /></div>;
  if (principalQuery.isError) {
    return <div className="auth-loading"><ErrorState error={principalQuery.error} onRetry={() => {
      clearToken(); queryClient.clear(); router.replace("/login");
    }} /><button className="button button-secondary" onClick={() => { clearToken(); router.replace("/login"); }}>Retour à la connexion</button></div>;
  }
  if (!principalQuery.data) return <div className="auth-loading"><LoadingState label="Vérification de la session…" /></div>;
  const principal = principalQuery.data.data;
  const memberships = principal.memberships ?? [];
  const activeMembership = memberships.find((membership) => membership.organization_id === organizationId);

  function chooseOrganization(id: string) {
    saveOrganizationId(id);
    setOrganizationId(id);
    void queryClient.invalidateQueries();
  }

  async function logout() {
    try {
      await api.logout();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erreur inattendue";
      saveLogoutWarning(`La session locale est fermée, mais la révocation serveur a échoué : ${message}`);
    }
    clearToken();
    queryClient.clear();
    router.replace("/login");
  }

  const nav = <><div className="brand"><div className="brand-mark"><Shield size={20} /></div><div><strong>NORTHSTAR</strong><span>SECURITY OPERATIONS</span></div></div>
    <div className="side-label">ESPACE DE TRAVAIL</div>
    <nav className="side-nav">{navigation.map((item) => {
      const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
      const Icon = item.icon;
      return <Link key={item.href} href={item.href} className={`nav-link${active ? " active" : ""}`} onClick={() => setMobileOpen(false)}>
        <Icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.href === "/incidents" && <span className="nav-indicator" />}
      </Link>;
    })}</nav><div className="sidebar-bottom"><SimulationBadge /><div className="system-status"><span className="source-dot" /> Données servies par FastAPI</div></div></>;

  return <div className="portal-layout">
    <aside className="sidebar">{nav}</aside>
    {mobileOpen && <div className="mobile-backdrop" onClick={() => setMobileOpen(false)} />}
    <aside className={`mobile-sidebar${mobileOpen ? " open" : ""}`}><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu"><X size={20} /></button>{nav}</aside>
    <div className="main-column">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu"><Menu size={20} /></button>
        <div className="topbar-context"><span className="live-dot" /> SOC CONSOLE <span className="breadcrumb-divider">/</span> {navigation.find((item) => pathname.startsWith(item.href))?.label ?? "Portail"}</div>
        <div className="topbar-actions"><div className="org-select-wrap"><Network size={15} />
          <select aria-label="Organisation active" value={organizationId ?? ""} onChange={(event) => chooseOrganization(event.target.value)}>
            <option value="" disabled>{memberships.length ? "Choisir l’organisation" : "Aucune organisation"}</option>
            {memberships.map((membership: Membership) => <option key={membership.organization_id} value={membership.organization_id}>{membership.organization_name}</option>)}
          </select><ChevronDown size={14} /></div>
          <div className="user-chip"><div className="avatar">{(principal.display_name || principal.user_key).slice(0, 1).toUpperCase()}</div><div className="user-details"><strong>{principal.display_name || principal.user_key}</strong><span>{activeMembership?.role?.replaceAll("_", " ") ?? "Démo"}</span></div></div>
          <button className="icon-button logout-button" title="Déconnexion" onClick={() => void logout()}><LogOut size={17} /></button>
        </div>
      </header>
      {!activeMembership && <div className="tenant-banner"><AlertTriangle size={17} />{memberships.length ? "Sélectionnez une organisation pour accéder aux données." : "Aucune organisation disponible pour ce compte."}</div>}
      <main className="main-content">{activeMembership ? children : <section className="tenant-empty"><div className="empty-icon"><Search size={22} /></div><h2>Organisation requise</h2><p>Choisissez un tenant autorisé dans la barre supérieure. Chaque appel métier transmettra explicitement son identifiant à l’API.</p></section>}</main>
      <footer className="footer"><span>Northstar SOC · Prototype</span><span>Données et autorisations fournies par le backend FastAPI</span></footer>
    </div>
  </div>;
}
