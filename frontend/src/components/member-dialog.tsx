"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ROLE_LABELS } from "@/lib/member-assignment";
import type { Role } from "@/types/api";

export function Popup({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return <div className="member-dialog-backdrop" onMouseDown={onClose}>
    <section className="member-dialog" role="dialog" aria-modal="true" aria-labelledby="member-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="member-dialog-close" aria-label="Fermer" onClick={onClose}>×</button>
      <h2 id="member-dialog-title">{title}</h2>
      {children}
    </section>
  </div>;
}

export interface DialogMembership {
  organizationId: string;
  organizationName: string;
  role: Role;
  options: Role[];
  editable: boolean;
}

export function MemberDialog({ name, userKey, memberships, pending, error, onClose, onConfirm }: {
  name: string;
  userKey: string;
  memberships: DialogMembership[];
  pending: boolean;
  error?: string;
  onClose: () => void;
  onConfirm: (changes: { organizationId: string; role: Role }[]) => void;
}) {
  const [roles, setRoles] = useState<Record<string, Role>>(() => Object.fromEntries(memberships.map((membership) => [membership.organizationId, membership.role])));
  const changes = memberships.filter((membership) => membership.editable && roles[membership.organizationId] && roles[membership.organizationId] !== membership.role);

  return <Popup title={name} onClose={onClose}>
    {memberships.map((membership) => <div key={membership.organizationId} className="member-dialog-block">
      <p>{userKey}. {membership.organizationName}. Rôle actuel : {ROLE_LABELS[membership.role] ?? membership.role}.</p>
      {membership.editable ? <label>Nouveau rôle
        <select value={roles[membership.organizationId] ?? membership.role} onChange={(event) => setRoles((current) => ({ ...current, [membership.organizationId]: event.target.value as Role }))}>
          {(membership.options.includes(membership.role) ? membership.options : [membership.role, ...membership.options]).map((option) => <option key={option} value={option}>{ROLE_LABELS[option] ?? option}</option>)}
        </select>
      </label> : <p>Ce rôle ne se modifie pas.</p>}
    </div>)}
    {error && <p className="member-dialog-error">{error}</p>}
    {changes.length > 0 && <button type="button" className="member-dialog-submit" disabled={pending} onClick={() => onConfirm(changes.map((membership) => ({ organizationId: membership.organizationId, role: roles[membership.organizationId] })))}>{pending ? "Confirmation…" : "Confirmer"}</button>}
  </Popup>;
}
