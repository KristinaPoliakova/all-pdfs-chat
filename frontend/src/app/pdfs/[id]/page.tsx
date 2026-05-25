'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { SignInPrompt } from '@/components/auth/SignInPrompt';
import { AppShell } from '@/components/layout/AppShell';
import { PdfStatusCard } from '@/components/pdf/PdfStatusCard';
import { useAuth } from '@/hooks/useAuth';
import { usePdfDocument } from '@/hooks/usePdfDocument';
import { getAuthToken } from '@/lib/auth/session';
import { ApiError } from '@/lib/api/errors';
import { isChatEnabled } from '@/lib/processing-status';

function StatusSkeleton() {
  return (
    <div className="animate-pulse space-y-4 rounded-lg border border-border p-6">
      <div className="h-5 w-2/3 rounded bg-border" />
      <div className="h-4 w-1/4 rounded bg-border" />
      <div className="h-4 w-1/3 rounded bg-border" />
    </div>
  );
}

export default function PdfDetailPage() {
  const params = useParams();
  const id = typeof params.id === 'string' ? params.id : '';
  const { isLoading: authLoading } = useAuth();
  const hasSession = Boolean(getAuthToken());
  const { data, isPending, isError, error } = usePdfDocument(id);
  const returnTo = id ? `/pdfs/${id}` : '/';

  if (!id) {
    return (
      <AppShell>
        <p className="text-sm text-danger">Invalid document link.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Upload another PDF
        </Link>
      </AppShell>
    );
  }

  if (authLoading) {
    return (
      <AppShell>
        <StatusSkeleton />
      </AppShell>
    );
  }

  if (!hasSession) {
    return (
      <AppShell>
        <SignInPrompt message="Sign in to view this document." returnTo={returnTo} />
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to upload
        </Link>
      </AppShell>
    );
  }

  if (isPending) {
    return (
      <AppShell>
        <StatusSkeleton />
      </AppShell>
    );
  }

  if (isError && error instanceof ApiError && error.status === 401) {
    return (
      <AppShell>
        <SignInPrompt
          message="Your session expired. Sign in again to view this document."
          returnTo={returnTo}
        />
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Back to upload
        </Link>
      </AppShell>
    );
  }

  if (isError && error instanceof ApiError && error.status === 404) {
    return (
      <AppShell>
        <p className="text-sm text-muted">Document not found.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Upload another PDF
        </Link>
      </AppShell>
    );
  }

  if (isError || !data) {
    return (
      <AppShell>
        <p className="text-sm text-danger">Could not load document. Please try again.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
          Upload another PDF
        </Link>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PdfStatusCard document={data} />
      <ChatPanel pdfId={id} enabled={isChatEnabled(data.processing_status)} />
      <Link href="/" className="mt-6 inline-block text-sm text-accent-cyan hover:underline">
        Upload another PDF
      </Link>
    </AppShell>
  );
}
