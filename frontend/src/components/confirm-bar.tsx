"use client";

export function ConfirmBar({ message, pending = false, onConfirm, onCancel }: {
  message: string;
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return <div className="confirm-bar" role="alertdialog" aria-label="Confirmation">
    <p>{message}</p>
    <button type="button" className="button button-primary" disabled={pending} onClick={onConfirm}>{pending ? "Confirmation…" : "Confirmer"}</button>
    <button type="button" className="button button-secondary" disabled={pending} onClick={onCancel}>Annuler</button>
  </div>;
}
