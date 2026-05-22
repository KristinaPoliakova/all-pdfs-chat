import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-accent h-0.5" aria-hidden />
      <main className="mx-auto max-w-2xl px-4 py-12">
        <header className="mb-10">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            All PDFs Chat
          </h1>
          <p className="mt-2 text-sm text-muted">
            Upload a PDF and ask questions once processing completes.
          </p>
        </header>
        {children}
      </main>
    </div>
  );
}
