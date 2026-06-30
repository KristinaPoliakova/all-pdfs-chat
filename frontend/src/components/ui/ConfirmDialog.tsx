'use client';

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="animate-canvas-fade-in fixed inset-0 z-50 flex items-center justify-center bg-[var(--scrim)] [backdrop-filter:var(--blur-scrim)] p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-[var(--r-2xl)] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-modal)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-display text-[var(--fs-title)] font-semibold text-[var(--text)]">{title}</h2>
        <p className="mt-2 text-[var(--fs-sm)] leading-[var(--lh-normal)] text-[var(--text-dim)]">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-[var(--r-md)] border border-[var(--border)] px-3 py-1.5 text-[var(--fs-sm)] text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-[var(--r-md)] bg-[var(--danger)] px-3 py-1.5 text-[var(--fs-sm)] font-medium text-white transition-opacity hover:opacity-90"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
