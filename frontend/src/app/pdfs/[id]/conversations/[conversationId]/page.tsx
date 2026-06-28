'use client';

import { useParams } from 'next/navigation';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { usePdfDocument } from '@/hooks/usePdfDocument';
import { isChatEnabled } from '@/lib/processing-status';

export default function ConversationChatPage() {
  const params = useParams();
  const pdfId = typeof params.id === 'string' ? params.id : '';
  const conversationId =
    typeof params.conversationId === 'string' ? params.conversationId : '';
  // The layout already loaded and cached this query; this read hits the cache.
  const { data } = usePdfDocument(pdfId);
  const enabled = data ? isChatEnabled(data.processing_status) : false;

  return (
    <ChatPanel
      key={conversationId}
      pdfId={pdfId}
      conversationId={conversationId}
      enabled={enabled}
    />
  );
}
