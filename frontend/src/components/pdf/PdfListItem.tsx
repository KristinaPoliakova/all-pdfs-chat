'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ProcessingStatusBadge } from '@/components/pdf/ProcessingStatusBadge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { InlineEdit } from '@/components/ui/InlineEdit';
import { useDeletePdf, useRenamePdf } from '@/hooks/usePdfMutations';
import { ApiError, manageErrorMessage } from '@/lib/api/errors';
import type { PdfDocument } from '@/types/pdf';

export function PdfListItem({ document }: { document: PdfDocument }) {
  const rename = useRenamePdf();
  const remove = useDeletePdf();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <li className="rounded-lg border border-border p-4">
      <div className="flex items-center justify-between gap-3">
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
          <>
            <div className="min-w-0">
              <Link
                href={`/pdfs/${document.id}`}
                className="block truncate text-sm font-medium text-foreground hover:underline"
              >
                {document.filename}
              </Link>
              <div className="mt-1">
                <ProcessingStatusBadge status={document.processing_status} />
              </div>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setEditing(true);
                }}
                className="rounded-lg border border-border px-2 py-1 text-xs text-foreground hover:bg-surface"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setConfirming(true);
                }}
                className="rounded-lg border border-border px-2 py-1 text-xs text-danger hover:bg-surface"
              >
                Delete
              </button>
            </div>
          </>
        )}
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-xs text-danger">
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
