"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, LockKeyhole, Shield } from "lucide-react";
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

  return <main className="login-page"><div className="login-top"><div className="brand login-brand"><div className="brand-mark"><Shield size={16} /></div><div><strong>Northstar</strong><span>Console SOC</span></div></div><SimulationBadge /></div>
    <div className="login-content">
      <section className="login-card"><h1>Connexion</h1><p className="login-intro">Environnement de démonstration. Saisissez une clé utilisateur.</p>
        <div className="simulation-callout">Authentification locale. Aucun fournisseur d’identité externe n’est utilisé.</div>
        {logoutWarning && <div className="notice notice-error"><AlertTriangle size={16} />{logoutWarning}</div>}
        <form onSubmit={(event) => { event.preventDefault(); setErrorText(""); login.mutate(); }}>
          <label htmlFor="user-key">Clé utilisateur de démo</label><div className="input-icon-wrap"><LockKeyhole size={17} /><input id="user-key" list="demo-user-keys" autoComplete="username" value={userKey} onChange={(event) => setUserKey(event.target.value)} placeholder="Ex. analyst-a" required /><datalist id="demo-user-keys">
            <option value="analyst-a" /><option value="admin-a" /><option value="operator-a" /><option value="auditor-a" /><option value="observer-a" />
            <option value="analyst-b" /><option value="admin-b" /><option value="operator-b" /><option value="super-admin" />
          </datalist></div>
          <span className="microcopy">Clés de démonstration listées dans le README backend.</span>
          {errorText && <ErrorNotice>{errorText}</ErrorNotice>}
          {login.isError && <ErrorNotice>{login.error.message}</ErrorNotice>}
          <button className="button button-primary login-submit" disabled={login.isPending || !userKey.trim()}>{login.isPending ? "Connexion…" : "Se connecter"}<ArrowRight size={16} /></button>
        </form><p className="login-footnote">Les droits sont vérifiés par l’API, pas par l’affichage.</p>
      </section>
    </div><div className="login-bottom"><span>Démonstration</span><span>Aucune action sur des outils réels</span></div></main>;
}
