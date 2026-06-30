'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { ProcessingStatusBadge } from '@/components/pdf/ProcessingStatusBadge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { InlineEdit } from '@/components/ui/InlineEdit';
import { useDeletePdf, useRenamePdf } from '@/hooks/usePdfMutations';
import { ApiError, manageErrorMessage } from '@/lib/api/errors';
import type { PdfDocument } from '@/types/pdf';

export function PdfHeader({ document }: { document: PdfDocument }) {
  const router = useRouter();
  const rename = useRenamePdf();
  const remove = useDeletePdf();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <header className="mb-4 border-b border-[var(--border)] pb-4">
      {editing ? (
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
      ) : (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="font-display truncate text-[var(--fs-h3)] font-semibold text-[var(--text)]">{document.filename}</h1>
            <div className="mt-1">
              <ProcessingStatusBadge status={document.processing_status} />
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded-[var(--r-md)] border border-[var(--border)] px-3 py-1.5 text-[var(--fs-sm)] text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            >
              Rename
            </button>
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="rounded-[var(--r-md)] border border-[var(--border)] px-3 py-1.5 text-[var(--fs-sm)] text-[var(--danger)] transition-colors hover:border-[var(--danger)] hover:bg-[var(--surface-2)]"
            >
              Delete PDF
            </button>
          </div>
        </div>
      )}
      {error ? (
        <p role="alert" className="mt-2 text-[var(--fs-sm)] text-[var(--danger)]">
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
              onSuccess: () => router.push('/'),
              onError: (err) => {
                setConfirming(false);
                setError(err instanceof ApiError ? manageErrorMessage(err) : 'Delete failed.');
              },
            })
          }
        />
      ) : null}
    </header>
  );
}
