"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, LockKeyhole, Shield, Sparkles } from "lucide-react";
import { api, consumeLogoutWarning, saveToken } from "@/lib/api";
import { ErrorNotice, SimulationBadge } from "@/components/ui";

export default function LoginPage() {
  const [userKey, setUserKey] = useState("");
  const [errorText, setErrorText] = useState("");
  const [logoutWarning, setLogoutWarning] = useState("");
  const router = useRouter();
  const queryClient = useQueryClient();
  useEffect(() => { setLogoutWarning(consumeLogoutWarning() ?? ""); }, []);
  const login = useMutation({
    mutationFn: () => api.login(userKey.trim()),
    onSuccess: async (result) => {
      const token = result.data.access_token ?? result.data.token;
      if (!token) { setErrorText("Le backend n’a pas retourné de jeton de démonstration."); return; }
      saveToken(token);
      queryClient.setQueryData(["principal"], { data: result.data.principal, meta: result.meta });
      try {
        const principal = result.data.principal ? { data: result.data.principal, meta: result.meta } : await api.me();
        const firstMembership = principal.data.memberships?.[0];
        if (firstMembership) {
          const { saveOrganizationId } = await import("@/lib/api");
          saveOrganizationId(firstMembership.organization_id);
        }
        queryClient.setQueryData(["principal"], principal);
        router.replace("/dashboard");
      } catch (error) {
        setErrorText(error instanceof Error ? error.message : "Session de démonstration indisponible.");
      }
    },
  });

  return <main className="login-page"><div className="login-grid" /><div className="login-top"><div className="brand login-brand"><div className="brand-mark"><Shield size={20} /></div><div><strong>NORTHSTAR</strong><span>SECURITY OPERATIONS</span></div></div><SimulationBadge /></div>
    <div className="login-content"><div className="login-orbit"><div className="orbit-ring orbit-ring-one" /><div className="orbit-ring orbit-ring-two" /><div className="orbit-core"><Shield size={34} /></div><span className="orbit-node node-one" /><span className="orbit-node node-two" /><span className="orbit-node node-three" /></div>
      <section className="login-card"><div className="eyebrow">ESPACE SOC · ACCÈS DÉVELOPPEUR</div><h1>Reprenez la<br /><span>main sur vos alertes.</span></h1><p className="login-intro">Connectez-vous à l’environnement de démonstration Northstar.</p>
        <div className="simulation-callout"><Sparkles size={16} /><span>Connexion mock de développement. Aucun fournisseur d’identité externe n’est utilisé.</span></div>
        {logoutWarning && <div className="notice notice-error"><AlertTriangle size={16} />{logoutWarning}</div>}
        <form onSubmit={(event) => { event.preventDefault(); setErrorText(""); login.mutate(); }}>
          <label htmlFor="user-key">Clé utilisateur de démo</label><div className="input-icon-wrap"><LockKeyhole size={17} /><input id="user-key" list="demo-user-keys" autoComplete="username" value={userKey} onChange={(event) => setUserKey(event.target.value)} placeholder="Ex. analyst-a" required /><datalist id="demo-user-keys">
            <option value="analyst-a" /><option value="admin-a" /><option value="operator-a" /><option value="auditor-a" /><option value="observer-a" />
            <option value="analyst-b" /><option value="admin-b" /><option value="operator-b" /><option value="super-admin" />
          </datalist></div>
          <span className="microcopy">Clés de démonstration listées dans le README backend.</span>
          {errorText && <ErrorNotice>{errorText}</ErrorNotice>}
          {login.isError && <ErrorNotice>{login.error.message}</ErrorNotice>}
          <button className="button button-primary login-submit" disabled={login.isPending || !userKey.trim()}>{login.isPending ? "Connexion…" : "Entrer dans le portail"}<ArrowRight size={17} /></button>
        </form><div className="login-footnote"><span className="status-dot" /> Authentification par API · RBAC et accès tenant contrôlés côté serveur</div>
      </section>
    </div><div className="login-bottom"><span>PROTOTYPE · ENVIRONNEMENT DE DÉVELOPPEMENT</span><span>Interface seule — aucune action sur des outils réels</span></div></main>;
}
