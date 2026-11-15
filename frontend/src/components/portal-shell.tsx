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
import { canOpen } from "@/lib/access";
import { OrganizationProvider } from "@/lib/tenant";
import { ErrorState, LoadingState, SimulationBadge } from "./ui";

function OrganizationSwitcher({ memberships, organizationId, onChange }: {
  memberships: Membership[]; organizationId: string | null; onChange: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const active = memberships.find((membership) => membership.organization_id === organizationId);
  const label = active?.organization_name ?? (memberships.length ? "Organisation" : "Aucune organisation");
  if (memberships.length <= 1) {
    return <div className="org-current"><Network size={15} /><span>{label}</span></div>;
  }
  return <div className="org-menu">
    <button type="button" className="org-trigger" aria-expanded={open} aria-haspopup="listbox" onClick={() => setOpen((value) => !value)}>
      <Network size={15} /><span>{label}</span><ChevronDown size={14} />
    </button>
    {open && <ul className="org-list" role="listbox">
      {memberships.map((membership) => <li key={membership.organization_id}>
        <button type="button" role="option" aria-selected={membership.organization_id === organizationId} className={membership.organization_id === organizationId ? "active" : ""} onClick={() => { onChange(membership.organization_id); setOpen(false); }}>{membership.organization_name}</button>
      </li>)}
    </ul>}
  </div>;
}

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
  const [sessionReady, setSessionReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const principalQuery = useQuery({
    queryKey: ["principal"],
    queryFn: () => api.me(),
    enabled: sessionReady && hasToken,
    retry: false,
  });

  useEffect(() => {
    const token = Boolean(getToken());
    setHasToken(token);
    setOrganizationId(getOrganizationId());
    setSessionReady(true);
    if (!token) router.replace("/login");
  }, [router]);

  if (!sessionReady || !hasToken) return <div className="auth-loading"><LoadingState label="Vérification de la session…" /></div>;
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
    if (id === organizationId) return;
    saveOrganizationId(id);
    setOrganizationId(id);
    if (/^\/incidents\/.+/.test(pathname)) router.replace("/incidents");
    else if (pathname === "/events") router.replace("/events");
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

  const nav = <><div className="brand"><div className="brand-mark"><Shield size={16} /></div><div><strong>Northstar</strong><span>Console SOC</span></div></div>
    <div className="side-label">Navigation</div>
    <nav className="side-nav">{navigation.filter((item) => canOpen(activeMembership?.role, item.href)).map((item) => {
      const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
      const Icon = item.icon;
      return <Link key={item.href} href={item.href} className={`nav-link${active ? " active" : ""}`} onClick={() => setMobileOpen(false)}>
        <Icon size={16} strokeWidth={1.75} /><span>{item.label}</span>
      </Link>;
    })}</nav><div className="sidebar-bottom"><SimulationBadge /></div></>;

  const pageAllowed = canOpen(activeMembership?.role, pathname);
  return <OrganizationProvider organizationId={organizationId} role={activeMembership?.role ?? null}><div className="portal-layout">
    <aside className="sidebar">{nav}</aside>
    {mobileOpen && <div className="mobile-backdrop" onClick={() => setMobileOpen(false)} />}
    <aside className={`mobile-sidebar${mobileOpen ? " open" : ""}`}><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu"><X size={20} /></button>{nav}</aside>
    <div className="main-column">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu"><Menu size={20} /></button>
        <div className="topbar-context">{navigation.find((item) => pathname.startsWith(item.href))?.label ?? "Portail"}</div>
        <div className="topbar-actions"><OrganizationSwitcher memberships={memberships} organizationId={organizationId} onChange={chooseOrganization} />
          <div className="user-chip"><div className="avatar">{(principal.display_name || principal.user_key).slice(0, 1).toUpperCase()}</div><div className="user-details"><strong>{principal.display_name || principal.user_key}</strong><span>{activeMembership?.role?.replaceAll("_", " ") ?? "Démo"}</span></div></div>
          <button className="icon-button logout-button" title="Déconnexion" onClick={() => void logout()}><LogOut size={17} /></button>
        </div>
      </header>
      {!activeMembership && <div className="tenant-banner"><AlertTriangle size={17} />{memberships.length ? "Sélectionnez une organisation pour accéder aux données." : "Aucune organisation disponible pour ce compte."}</div>}
      <main key={organizationId ?? "none"} className="main-content">{activeMembership ? (pageAllowed ? children : <section className="tenant-empty"><div className="empty-icon"><Shield size={22} /></div><h2>Page non autorisée</h2><p>Ce rôle ne consulte pas cette page. Les données de l’organisation ne changent pas : seuls les membres autorisés y accèdent.</p></section>) : <section className="tenant-empty"><div className="empty-icon"><Search size={22} /></div><h2>Organisation requise</h2><p>Choisissez un tenant autorisé dans la barre supérieure. Chaque appel métier transmettra explicitement son identifiant à l’API.</p></section>}</main>
      <footer className="footer"><span>Northstar · démonstration</span><span>Les actions restent soumises au backend</span></footer>
    </div>
  </div></OrganizationProvider>;
}
