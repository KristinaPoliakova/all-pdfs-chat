'use client';

import { usePdfList } from '@/hooks/usePdfList';
import { useHasSession } from '@/hooks/useSession';
import { UploadDropzone } from '@/components/upload/UploadDropzone';
import { PdfListItem } from './PdfListItem';

export function PdfLibrary() {
  const hasSession = useHasSession();
  const { data, isPending, isError } = usePdfList();

  if (!hasSession) return null;

  const count = data?.length ?? 0;
  const countLabel = count === 1 ? '1 document' : `${count} documents`;

  return (
    <section aria-labelledby="library-heading">
      <div className="mb-[22px]">
        <h1 id="library-heading" className="font-display text-[var(--fs-h1)] font-semibold tracking-[var(--ls-snug)] text-[var(--text)]">
          Your Library
        </h1>
        <p className="mt-1 text-[var(--fs-sm)] text-[var(--text-dim)]">
          {countLabel} · click a document to open the conversation
        </p>
      </div>

      <ul className="grid grid-cols-1 gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
        <li>
          <UploadDropzone />
        </li>

        {isPending ? (
          <li className="flex min-h-[236px] items-center justify-center rounded-[var(--r-2xl)] border border-[var(--border)] text-[var(--fs-sm)] text-[var(--text-dim)] sm:col-span-2">
            Loading your PDFs…
          </li>
        ) : isError ? (
          <li className="flex min-h-[236px] items-center justify-center rounded-[var(--r-2xl)] border border-[var(--border)] text-[var(--fs-sm)] text-[var(--danger)] sm:col-span-2">
            Couldn&apos;t load your PDFs. Please refresh.
          </li>
        ) : !data || data.length === 0 ? (
          <li className="flex min-h-[236px] items-center justify-center rounded-[var(--r-2xl)] border border-dashed border-[var(--border)] text-center text-[var(--fs-sm)] text-[var(--text-dim)] sm:col-span-2">
            No PDFs yet — drop one to get started.
          </li>
        ) : (
          data.map((document) => <PdfListItem key={document.id} document={document} />)
        )}
      </ul>
    </section>
  );
}
