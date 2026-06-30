'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useFileUpload } from '@/hooks/usePdfUpload';
import { UploadErrorAlert } from '@/components/upload/UploadErrorAlert';

function BrandMark() {
  return (
    <Link href="/" className="flex items-center gap-[11px]">
      <span className="font-display flex h-[30px] w-[30px] items-center justify-center rounded-[var(--r-sm)] bg-[var(--accent)] text-[15px] font-bold text-[var(--accent-ink)]">
        A
      </span>
      <span className="font-display text-[var(--fs-title)] font-semibold tracking-[var(--ls-snug)] text-[var(--text)]">
        All PDFs Chat
      </span>
    </Link>
  );
}

function UploadButton() {
  const { inputRef, isPending, validationError, handleFile, openPicker, upload } = useFileUpload();

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="sr-only"
        disabled={isPending}
        onChange={(e) => {
          handleFile(e.target.files?.[0]);
          e.target.value = '';
        }}
      />
      <button
        type="button"
        disabled={isPending}
        onClick={openPicker}
        className="flex cursor-pointer items-center gap-[6px] rounded-[var(--r-md)] bg-[var(--accent)] px-4 py-[10px] text-[var(--fs-sm)] font-bold text-[var(--accent-ink)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? (
          'Uploading…'
        ) : (
          <>
            <Plus className="h-4 w-4" strokeWidth={1.75} aria-hidden />
            Upload
          </>
        )}
      </button>
      {validationError ? (
        <p role="alert" className="sr-only">
          {validationError}
        </p>
      ) : null}
      {upload.error ? (
        <div className="fixed left-1/2 top-[72px] z-30 w-[min(680px,92vw)] -translate-x-1/2">
          <UploadErrorAlert error={upload.error} returnTo="/" />
        </div>
      ) : null}
    </>
  );
}

function AccountMenu({ email, onSignOut }: { email?: string; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const initial = (email?.trim()[0] ?? 'U').toUpperCase();

  useEffect(() => {
    if (!open) return;
    const onDocClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((v) => !v)}
        className="font-display flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] text-[13px] font-semibold text-[var(--text)] transition-opacity hover:opacity-80"
      >
        {initial}
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-[42px] z-50 w-[220px] overflow-hidden rounded-[var(--r-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-float)]"
        >
          {email ? (
            <div className="border-b border-[var(--border)] px-4 py-3">
              <p className="text-[11px] text-[var(--text-dim)]">Signed in as</p>
              <p className="truncate text-[13px] font-semibold text-[var(--text)]" title={email}>
                {email}
              </p>
            </div>
          ) : null}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onSignOut();
            }}
            className="block w-full cursor-pointer px-4 py-3 text-left text-[13px] text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 flex h-[var(--bar-h)] items-center justify-between gap-5 border-b border-[var(--border)] bg-[var(--bar-bg)] px-8 [backdrop-filter:var(--blur-bar)]">
        <BrandMark />
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <UploadButton />
              <AccountMenu email={user?.email} onSignOut={() => void logout()} />
            </>
          ) : (
            <div className="flex items-center gap-3 text-[13px]">
              <Link href="/login" className="font-semibold text-[var(--accent)] hover:underline">
                Sign in
              </Link>
              <Link href="/register" className="text-[var(--text-dim)] hover:text-[var(--text)]">
                Register
              </Link>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-[var(--content-max)] px-8 pb-[var(--space-16)] pt-[var(--space-10)]">{children}</main>
    </div>
  );
}
