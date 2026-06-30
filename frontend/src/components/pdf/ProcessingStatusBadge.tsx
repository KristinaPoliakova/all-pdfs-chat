import { statusLabel } from '@/lib/processing-status';
import type { PdfProcessingStatus } from '@/types/pdf';

function isFailed(status: PdfProcessingStatus): boolean {
  return status === 'classification_failed' || status === 'parsing_failed';
}

function badgeStyle(status: PdfProcessingStatus): { text: string; dot: string } {
  if (status === 'parsed') {
    return { text: 'text-[var(--text-dim)]', dot: 'bg-[var(--success)]' };
  }
  if (isFailed(status)) {
    return { text: 'text-[var(--danger)]', dot: 'bg-[var(--danger)]' };
  }
  return { text: 'text-[var(--text-dim)]', dot: 'animate-canvas-pulse bg-[var(--accent)]' };
}

export function ProcessingStatusBadge({ status }: { status: PdfProcessingStatus }) {
  const { text, dot } = badgeStyle(status);

  return (
    <span className={`inline-flex items-center gap-2 text-[12px] font-medium ${text}`}>
      <span className={`h-[6px] w-[6px] shrink-0 rounded-full ${dot}`} aria-hidden />
      {statusLabel(status)}
    </span>
  );
}
