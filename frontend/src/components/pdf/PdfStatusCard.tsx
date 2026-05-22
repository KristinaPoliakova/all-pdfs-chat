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
    <article className="rounded-lg border border-border p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-foreground">{filename}</p>
          <p className="mt-1 text-sm text-muted">{formatFileSize(size_bytes)}</p>
        </div>
        <ProcessingStatusBadge status={processing_status} />
      </div>

      <div className="mt-6 space-y-4" aria-live="polite">
        {inProgress ? (
          <div className="flex items-center gap-3 text-sm text-muted">
            <span
              className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-border border-t-accent-cyan"
              aria-hidden
            />
            <span>Processing your document…</span>
          </div>
        ) : null}

        {errorMessage ? (
          <p role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
            {errorMessage}
          </p>
        ) : null}
      </div>
    </article>
  );
}
