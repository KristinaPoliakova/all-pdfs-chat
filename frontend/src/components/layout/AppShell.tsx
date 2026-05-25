'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-accent h-0.5" aria-hidden />
      <main className="mx-auto max-w-2xl px-4 py-12">
        <header className="mb-10 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">
              All PDFs Chat
            </h1>
            <p className="mt-2 text-sm text-muted">
              Upload a PDF and ask questions once processing completes.
            </p>
          </div>
          {!isLoading && user ? (
            <div className="flex shrink-0 flex-col items-end gap-1 text-right">
              <span className="max-w-[12rem] truncate text-xs text-muted" title={user.email}>
                {user.email}
              </span>
              <button
                type="button"
                onClick={() => void logout()}
                className="text-xs text-accent-cyan hover:underline"
              >
                Sign out
              </button>
            </div>
          ) : !isLoading ? (
            <div className="flex shrink-0 items-center gap-3 text-xs">
              <Link href="/login" className="text-accent-cyan hover:underline">
                Sign in
              </Link>
              <Link href="/register" className="text-muted hover:text-foreground hover:underline">
                Register
              </Link>
            </div>
          ) : null}
        </header>
        {children}
      </main>
    </div>
  );
}
