import type { ReactNode } from 'react';

function BrandPanel() {
  return (
    <div className="relative hidden min-h-[540px] flex-col justify-between overflow-hidden bg-[var(--surface)] p-[44px_40px] md:flex">
      <div
        className="absolute inset-0 opacity-50"
        style={{ background: 'var(--stripe-brand)' }}
        aria-hidden
      />
      <div
        className="absolute -left-[60px] -top-20 h-[360px] w-[360px] rounded-full opacity-[0.28]"
        style={{ background: 'var(--accent)', filter: 'blur(120px)' }}
        aria-hidden
      />

      <div className="relative flex items-center gap-[11px]">
        <span className="font-display flex h-[34px] w-[34px] items-center justify-center rounded-[var(--r-md)] bg-[var(--accent)] text-[var(--fs-h3)] font-bold text-[var(--accent-ink)]">
          A
        </span>
        <span className="font-display text-[var(--fs-h3)] font-semibold tracking-[var(--ls-snug)] text-[var(--text)]">
          All PDFs Chat
        </span>
      </div>

      <div className="relative">
        <h2 className="font-display text-[var(--fs-display)] font-semibold leading-[var(--lh-tight)] tracking-[var(--ls-tight)] text-[var(--text)]">
          Talk to your
          <br />
          documents.
        </h2>
        <p className="mt-4 max-w-[300px] text-[14.5px] leading-[1.6] text-[var(--text-dim)]">
          Upload a PDF, let it parse, then ask anything — every answer cites the exact page it came
          from.
        </p>
      </div>

      <div className="relative flex gap-2">
        {['cited sources', 'private'].map((chip) => (
          <span
            key={chip}
            className="font-mono rounded-[var(--r-pill)] border border-[var(--border)] px-[10px] py-1 text-[var(--fs-meta)] text-[var(--text-dim)]"
          >
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="grid w-[var(--auth-max)] max-w-full grid-cols-1 overflow-hidden rounded-[var(--r-3xl)] border border-[var(--border)] shadow-[var(--shadow-modal)] md:grid-cols-2">
        <BrandPanel />
        <div className="flex flex-col justify-center bg-[var(--bg)] p-[48px_44px]">{children}</div>
      </div>
    </div>
  );
}
