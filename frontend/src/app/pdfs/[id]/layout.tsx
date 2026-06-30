'use client';

import { useParams, useRouter } from 'next/navigation';
import { useCallback, type ReactNode } from 'react';
import { SignInPrompt } from '@/components/auth/SignInPrompt';
import { AppShell } from '@/components/layout/AppShell';
import { ChatOverlay, PanelHeader } from '@/components/chat/ChatOverlay';
import { ConversationSidebar } from '@/components/conversation/ConversationSidebar';
import { PdfLibrary } from '@/components/pdf/PdfLibrary';
import { useAuth } from '@/hooks/useAuth';
import { useConversations } from '@/hooks/useConversations';
import { usePdfDocument } from '@/hooks/usePdfDocument';
import { useHasSession } from '@/hooks/useSession';
import { ApiError } from '@/lib/api/errors';
import { isChatEnabled, isInProgress } from '@/lib/processing-status';
import type { PdfDocument } from '@/types/pdf';

function panelMeta(document: PdfDocument, conversationCount: number): string {
  if (isInProgress(document.processing_status)) {
    return 'Still parsing…';
  }
  const pages = document.page_count != null ? `${document.page_count} pages` : 'Document';
  const convos =
    conversationCount === 1 ? '1 conversation' : `${conversationCount} conversations`;
  return `${pages} · ${convos}`;
}

function PanelMessage({ children }: { children: ReactNode }) {
  return <div className="flex flex-1 items-center justify-center p-6 text-center">{children}</div>;
}

export default function PdfLayout({ children }: { children: ReactNode }) {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === 'string' ? params.id : '';
  const conversationId =
    typeof params.conversationId === 'string' ? params.conversationId : null;
  const { isLoading: authLoading } = useAuth();
  const hasSession = useHasSession();
  const { data, isPending, isError, error } = usePdfDocument(id);
  const { data: conversations } = useConversations(hasSession && id ? id : '');
  const returnTo = id ? `/pdfs/${id}` : '/';

  const close = useCallback(() => router.push('/'), [router]);

  let body: ReactNode;
  let header: ReactNode = <PanelHeader title="Conversation" onClose={close} />;

  if (!id) {
    body = (
      <PanelMessage>
        <p className="text-[13px] text-[var(--danger)]">Invalid document link.</p>
      </PanelMessage>
    );
  } else if (authLoading || (hasSession && isPending)) {
    body = (
      <PanelMessage>
        <p className="text-[13px] text-[var(--text-dim)]">Loading document…</p>
      </PanelMessage>
    );
  } else if (!hasSession || (isError && error instanceof ApiError && error.status === 401)) {
    body = (
      <PanelMessage>
        <SignInPrompt message="Sign in to view this document." returnTo={returnTo} />
      </PanelMessage>
    );
  } else if (isError && error instanceof ApiError && error.status === 404) {
    body = (
      <PanelMessage>
        <p className="text-[13px] text-[var(--text-dim)]">Document not found.</p>
      </PanelMessage>
    );
  } else if (isError || !data) {
    body = (
      <PanelMessage>
        <p className="text-[13px] text-[var(--danger)]">Could not load document. Please try again.</p>
      </PanelMessage>
    );
  } else {
    header = (
      <PanelHeader
        title={data.filename}
        meta={panelMeta(data, conversations?.length ?? 0)}
        onClose={close}
      />
    );
    body = (
      <>
        <ConversationSidebar
          pdfId={id}
          activeId={conversationId}
          parsed={isChatEnabled(data.processing_status)}
        />
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
      </>
    );
  }

  return (
    <>
      <AppShell>
        <PdfLibrary />
      </AppShell>
      <ChatOverlay onClose={close}>
        {header}
        {body}
      </ChatOverlay>
    </>
  );
}
