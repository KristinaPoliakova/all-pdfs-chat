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
    return (
      <div className="flex-1 overflow-y-auto p-[22px]">
        <PdfStatusCard document={data} />
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center p-[22px] text-center">
      <p className="text-[13px] text-[var(--text-dim)]">
        Select a conversation, or start a new one to chat about this PDF.
      </p>
    </div>
  );
}
