'use client';

import { useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';

function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      type="button"
      onClick={onClose}
      aria-label="Close conversation"
      className="flex h-[30px] w-[30px] shrink-0 cursor-pointer items-center justify-center rounded-[var(--r-sm)] bg-[var(--surface-2)] text-[var(--text-dim)] transition-colors hover:text-[var(--text)]"
    >
      <X className="h-4 w-4" strokeWidth={1.75} aria-hidden />
    </button>
  );
}

export function PanelHeader({
  title,
  meta,
  onClose,
}: {
  title: string;
  meta?: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-[22px] py-[18px]">
      <div className="min-w-0">
        <h2 className="font-display truncate text-[15px] font-semibold text-[var(--text)]">{title}</h2>
        {meta ? <p className="mt-[2px] text-[11.5px] text-[var(--text-dim)]">{meta}</p> : null}
      </div>
      <CloseButton onClose={onClose} />
    </div>
  );
}

/**
 * Slide-in chat surface rendered over the library. The scrim and Escape key
 * both dismiss it; the caller owns navigation (typically back to the library).
 */
export function ChatOverlay({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <>
      <div
        className="animate-canvas-fade-in fixed inset-0 z-40 bg-[var(--scrim)] [backdrop-filter:var(--blur-scrim)]"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Conversation"
        className="animate-canvas-slide-in fixed inset-y-0 right-0 z-50 flex w-[var(--panel-w)] max-w-[94vw] flex-col border-l border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-panel)]"
      >
        {children}
      </div>
    </>
  );
}
