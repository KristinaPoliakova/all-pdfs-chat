import { ProcessingStatusBadge } from '@/components/pdf/ProcessingStatusBadge';
import { isInProgress } from '@/lib/processing-status';
import type { PdfDocument } from '@/types/pdf';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function PdfStatusCard({ document }: { document: PdfDocument }) {
  const { filename, size_bytes, processing_status, classification_error, parsing_error } =
    document;
  const inProgress = isInProgress(processing_status);
  const errorMessage = classification_error ?? parsing_error;

  return (
    <article className="rounded-[var(--r-xl)] border border-[var(--border)] bg-[var(--surface-2)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-display truncate font-semibold text-[var(--text)]">{filename}</p>
          <p className="mt-1 text-[13px] text-[var(--text-dim)]">{formatFileSize(size_bytes)}</p>
        </div>
        <ProcessingStatusBadge status={processing_status} />
      </div>

      <div className="mt-5 space-y-4" aria-live="polite">
        {inProgress ? (
          <div className="flex items-center gap-3 text-[13px] text-[var(--text-dim)]">
            <span
              className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]"
              aria-hidden
            />
            <span>Processing your document…</span>
          </div>
        ) : null}

        {errorMessage ? (
          <p
            role="alert"
            className="rounded-[var(--r-md)] border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-3 py-2 text-[var(--fs-sm)] text-[var(--danger)]"
          >
            {errorMessage}
          </p>
        ) : null}
      </div>
    </article>
  );
}
