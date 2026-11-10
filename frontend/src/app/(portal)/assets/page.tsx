"use client";

import { useQuery } from "@tanstack/react-query";
import { Boxes, Search } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { DataTable, ErrorState, formatDate, LoadingState, PageHeading, StatusBadge } from "@/components/ui";
import type { Asset } from "@/types/api";

export default function AssetsPage() {
  const [search, setSearch] = useState("");
  const query = useQuery({ queryKey: ["assets"], queryFn: () => api.assets() });
  const allAssets = query.data?.data ?? [];
  const assets = allAssets.filter((asset) => `${asset.name} ${asset.hostname ?? ""} ${asset.ip_address ?? ""} ${asset.asset_type}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="page-stack"><PageHeading eyebrow="INVENTAIRE DU TENANT" title="Actifs" description="Visibilité sur les hôtes et systèmes rattachés à l’organisation." />
    <div className="filter-bar"><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrer par hôte, IP ou type…" /></label><span className="result-count">{query.isSuccess ? `${assets.length} actifs` : ""}</span></div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">ASSET INVENTORY</div><h2><Boxes size={18} /> Actifs enregistrés</h2></div></div>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> :
        <DataTable headers={["Actif", "Nom d’hôte", "Adresse IP", "Type", "Statut", "Mis à jour"]} empty={!assets.length}>{assets.map((asset: Asset) =>
          <tr key={asset.id}><td className="table-primary">{asset.name}</td><td>{asset.hostname ?? "—"}</td><td><code>{asset.ip_address ?? "—"}</code></td><td>{asset.asset_type}</td><td><StatusBadge value={asset.status ?? "active"} /></td><td>{formatDate(asset.updated_at)}</td></tr>)}</DataTable>}
    </section>
    {!query.isLoading && !query.isError && !allAssets.length && <div className="muted-copy page-hint">L’inventaire est vide côté API. Aucun actif de démonstration local n’est ajouté.</div>}
  </div>;
}
