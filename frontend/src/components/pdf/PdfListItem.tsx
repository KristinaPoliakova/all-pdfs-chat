'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { InlineEdit } from '@/components/ui/InlineEdit';
import { useDeletePdf, useRenamePdf } from '@/hooks/usePdfMutations';
import { ApiError, manageErrorMessage } from '@/lib/api/errors';
import { isInProgress, statusLabel } from '@/lib/processing-status';
import type { PdfDocument } from '@/types/pdf';

function cardMeta(document: PdfDocument): { dot: string; text: string } {
  const status = document.processing_status;
  if (status === 'parsed') {
    const pages = document.page_count ? ` · ${document.page_count} pp` : '';
    return { dot: 'var(--success)', text: `Ready${pages}` };
  }
  if (status === 'classification_failed' || status === 'parsing_failed') {
    return { dot: 'var(--danger)', text: statusLabel(status) };
  }
  return { dot: 'var(--accent)', text: 'Processing' };
}

export function PdfListItem({ document }: { document: PdfDocument }) {
  const rename = useRenamePdf();
  const remove = useDeletePdf();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsing = isInProgress(document.processing_status);
  const meta = cardMeta(document);

  if (editing) {
    return (
      <li className="rounded-[var(--r-2xl)] border border-[var(--border)] bg-[var(--surface)] p-4">
        <InlineEdit
          initialValue={document.filename}
          maxLength={512}
          onSubmit={(filename) =>
            rename.mutate(
              { id: document.id, filename },
              {
                onSuccess: () => setEditing(false),
                onError: (err) =>
                  setError(err instanceof ApiError ? manageErrorMessage(err) : 'Rename failed.'),
              },
            )
          }
          onCancel={() => setEditing(false)}
        />
        {error ? (
          <p role="alert" className="mt-2 text-[12px] text-[var(--danger)]">
            {error}
          </p>
        ) : null}
      </li>
    );
  }

  return (
    <li className="group relative overflow-hidden rounded-[var(--r-2xl)] border border-[var(--border)] bg-[var(--surface)] transition-[border-color,transform] [transition-duration:var(--dur-fast)] [transition-timing-function:var(--ease-out)] hover:-translate-y-0.5 hover:border-[var(--accent)]">
      <Link
        href={`/pdfs/${document.id}`}
        aria-label={`Open ${document.filename}`}
        className="absolute inset-0 z-10"
      />

      <div
        className="relative flex h-32 items-center justify-center"
        style={{ background: 'var(--stripe), var(--bg)' }}
        aria-hidden
      >
        {parsing ? (
          <span className="font-mono animate-canvas-pulse rounded-[var(--r-pill)] border border-[var(--accent)] bg-[var(--bg)] px-[11px] py-[5px] text-[var(--fs-mono)] text-[var(--accent)]">
            parsing…
          </span>
        ) : null}
      </div>

      <div className="relative px-4 py-[15px]">
        <p className="font-display truncate text-[14px] font-semibold text-[var(--text)]">
          {document.filename}
        </p>
        <div className="mt-2 flex items-center gap-[7px]">
          <span
            className="h-[6px] w-[6px] shrink-0 rounded-full"
            style={{ backgroundColor: meta.dot }}
            aria-hidden
          />
          <span className="text-[11.5px] text-[var(--text-dim)]">{meta.text}</span>
        </div>
      </div>

      <div className="absolute right-2 top-2 z-20 flex gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <button
          type="button"
          onClick={() => {
            setError(null);
            setEditing(true);
          }}
          className="cursor-pointer rounded-[var(--r-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[11px] text-[var(--text)] hover:border-[var(--accent)]"
        >
          Rename
        </button>
        <button
          type="button"
          onClick={() => {
            setError(null);
            setConfirming(true);
          }}
          className="cursor-pointer rounded-[var(--r-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[11px] text-[var(--danger)] hover:border-[var(--danger)]"
        >
          Delete
        </button>
      </div>

      {error ? (
        <p role="alert" className="relative px-4 pb-3 text-[12px] text-[var(--danger)]">
          {error}
        </p>
      ) : null}

      {confirming ? (
        <ConfirmDialog
          title="Delete PDF"
          message={`Delete "${document.filename}" and all its conversations? This cannot be undone.`}
          confirmLabel="Delete"
          onCancel={() => setConfirming(false)}
          onConfirm={() =>
            remove.mutate(document.id, {
              onSuccess: () => setConfirming(false),
              onError: (err) => {
                setConfirming(false);
                setError(err instanceof ApiError ? manageErrorMessage(err) : 'Delete failed.');
              },
            })
          }
        />
      ) : null}
    </li>
  );
}
