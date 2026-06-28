'use client';

import { useSyncExternalStore } from 'react';
import { usePdfList } from '@/hooks/usePdfList';
import { getAuthToken } from '@/lib/auth/session';
import { PdfListItem } from './PdfListItem';

function subscribeToStorage(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  window.addEventListener('storage', callback);
  return () => window.removeEventListener('storage', callback);
}

export function PdfLibrary() {
  // The session token lives in localStorage, which is unavailable during SSR.
  // useSyncExternalStore uses the server snapshot (false) for the initial
  // hydration render so server and client agree, then re-renders with the
  // client value — avoiding a hydration mismatch.
  const hasSession = useSyncExternalStore(
    subscribeToStorage,
    () => Boolean(getAuthToken()),
    () => false,
  );
  const { data, isPending, isError } = usePdfList();

  if (!hasSession) return null;

  return (
    <section className="mt-10" aria-labelledby="library-heading">
      <h2 id="library-heading" className="mb-3 text-sm font-semibold text-foreground">
        Your PDFs
      </h2>
      {isPending ? (
        <p className="text-sm text-muted">Loading your PDFs…</p>
      ) : isError ? (
        <p className="text-sm text-danger">Couldn&apos;t load your PDFs. Please refresh.</p>
      ) : !data || data.length === 0 ? (
        <p className="text-sm text-muted">No PDFs yet — upload one above.</p>
      ) : (
        <ul className="space-y-3">
          {data.map((document) => (
            <PdfListItem key={document.id} document={document} />
          ))}
        </ul>
      )}
    </section>
  );
}
