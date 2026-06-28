'use client';

import { useParams } from 'next/navigation';
import { PdfStatusCard } from '@/components/pdf/PdfStatusCard';
import { usePdfDocument } from '@/hooks/usePdfDocument';
import { isChatEnabled } from '@/lib/processing-status';

export default function PdfConversationIndexPage() {
  const params = useParams();
  const pdfId = typeof params.id === 'string' ? params.id : '';
  // Hits the React Query cache the layout already populated.
  const { data } = usePdfDocument(pdfId);

  if (data && !isChatEnabled(data.processing_status)) {
    return <PdfStatusCard document={data} />;
  }

  return (
    <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-border p-10 text-center">
      <p className="text-sm text-muted">
        Select a conversation, or start a new one to chat about this PDF.
      </p>
    </div>
  );
}
