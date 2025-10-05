// frontend/src/components/ConfirmDialog.jsx
export default function ConfirmDialog({ open, title = "Are you sure?", body, onCancel, onConfirm }) {
  if (!open) return null;
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="modal-header"><strong>{title}</strong></div>
        <div className="modal-body">{body || "Confirm this action?"}</div>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className="btn danger" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
}
