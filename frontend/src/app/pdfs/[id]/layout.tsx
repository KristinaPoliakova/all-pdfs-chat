'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import type { ReactNode } from 'react';
import { SignInPrompt } from '@/components/auth/SignInPrompt';
import { AppShell } from '@/components/layout/AppShell';
import { ConversationSidebar } from '@/components/conversation/ConversationSidebar';
import { PdfHeader } from '@/components/pdf/PdfHeader';
import { useAuth } from '@/hooks/useAuth';
import { usePdfDocument } from '@/hooks/usePdfDocument';
import { getAuthToken } from '@/lib/auth/session';
import { ApiError } from '@/lib/api/errors';
import { isChatEnabled } from '@/lib/processing-status';

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4 rounded-lg border border-border p-6">
      <div className="h-5 w-2/3 rounded bg-border" />
      <div className="h-4 w-1/4 rounded bg-border" />
    </div>
  );
}

export default function PdfLayout({ children }: { children: ReactNode }) {
  const params = useParams();
  const id = typeof params.id === 'string' ? params.id : '';
  const conversationId =
    typeof params.conversationId === 'string' ? params.conversationId : null;
  const { isLoading: authLoading } = useAuth();
  const hasSession = Boolean(getAuthToken());
  const { data, isPending, isError, error } = usePdfDocument(id);
  const returnTo = id ? `/pdfs/${id}` : '/';

  if (!id) {
    return (
      <AppShell>
        <p className="text-sm text-danger">Invalid document link.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to library
        </Link>
      </AppShell>
    );
  }

  if (authLoading || (hasSession && isPending)) {
    return (
      <AppShell>
        <Skeleton />
      </AppShell>
    );
  }

  if (!hasSession || (isError && error instanceof ApiError && error.status === 401)) {
    return (
      <AppShell>
        <SignInPrompt message="Sign in to view this document." returnTo={returnTo} />
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to library
        </Link>
      </AppShell>
    );
  }

  if (isError && error instanceof ApiError && error.status === 404) {
    return (
      <AppShell>
        <p className="text-sm text-muted">Document not found.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to library
        </Link>
      </AppShell>
    );
  }

  if (isError || !data) {
    return (
      <AppShell>
        <p className="text-sm text-danger">Could not load document. Please try again.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to library
        </Link>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PdfHeader document={data} />
      <div className="flex gap-6">
        <ConversationSidebar
          pdfId={id}
          activeId={conversationId}
          parsed={isChatEnabled(data.processing_status)}
        />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
      <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
        Back to library
      </Link>
    </AppShell>
  );
}
