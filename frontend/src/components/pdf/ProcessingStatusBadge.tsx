import { statusLabel } from '@/lib/processing-status';
import type { PdfProcessingStatus } from '@/types/pdf';

function isFailed(status: PdfProcessingStatus): boolean {
  return status === 'classification_failed' || status === 'parsing_failed';
}

export function ProcessingStatusBadge({ status }: { status: PdfProcessingStatus }) {
  const label = statusLabel(status);

  if (status === 'parsed') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/5 px-2.5 py-0.5 text-xs font-medium text-success">
        {label}
      </span>
    );
  }

  if (isFailed(status)) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-danger/30 bg-danger/5 px-2.5 py-0.5 text-xs font-medium text-danger">
        {label}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-xs font-medium text-foreground">
      <span
        className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-accent-cyan"
        aria-hidden
      />
      {label}
    </span>
  );
}
