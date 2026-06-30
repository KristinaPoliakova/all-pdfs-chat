import Link from 'next/link';
import { FileText, Quote, ShieldCheck } from 'lucide-react';
import { loginPath, registerPath } from '@/lib/auth/paths';

export function LandingHero() {
  return (
    <section
      aria-labelledby="landing-heading"
      className="animate-canvas-fade-in flex min-h-[calc(100vh-176px)] items-center"
    >
      <div className="grid w-full items-center gap-12 lg:grid-cols-2">
        <div>
          <h1
            id="landing-heading"
            className="font-display text-[40px] font-semibold leading-[var(--lh-tight)] tracking-[var(--ls-tight)] text-[var(--text)] sm:text-[52px]"
          >
            Talk to your documents.
          </h1>

          <p className="mt-5 max-w-[460px] text-[15px] leading-[var(--lh-normal)] text-[var(--text-dim)]">
            Upload a PDF, let it parse, then ask anything — every answer cites the exact page it came
            from.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={registerPath('/')}
              className="rounded-[var(--r-lg)] bg-[var(--accent)] px-5 py-[13px] text-[var(--fs-base)] font-bold text-[var(--accent-ink)] transition-opacity hover:opacity-90"
            >
              Create account
            </Link>
            <Link
              href={loginPath('/')}
              className="rounded-[var(--r-lg)] border border-[var(--border)] bg-[var(--surface)] px-5 py-[13px] text-[var(--fs-base)] font-semibold text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
            >
              Sign in
            </Link>
          </div>

          <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-[var(--fs-sm)] text-[var(--text-dim)]">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[var(--accent)]" strokeWidth={1.75} aria-hidden />
              Private to your account
            </span>
            <span className="inline-flex items-center gap-2">
              <Quote className="h-4 w-4 text-[var(--accent)]" strokeWidth={1.75} aria-hidden />
              Page-level citations
            </span>
          </div>
        </div>

        <ChatPreview />
      </div>
    </section>
  );
}

function ChatPreview() {
  return (
    <div className="relative">
      <div
        className="absolute -right-12 -top-14 h-[300px] w-[300px] rounded-full opacity-[0.22]"
        style={{ background: 'var(--accent)', filter: 'blur(120px)' }}
        aria-hidden
      />

      <div className="relative overflow-hidden rounded-[var(--r-3xl)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-modal)]">
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-5 py-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-[var(--r-md)] bg-[var(--surface-2)] text-[var(--accent)]">
            <FileText className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="font-display truncate text-[var(--fs-base)] font-semibold text-[var(--text)]">
              Q3 Financial Report.pdf
            </p>
            <p className="font-mono text-[var(--fs-mono)] text-[var(--text-dim)]">ready · 24 pp</p>
          </div>
        </div>

        <div className="flex flex-col gap-4 bg-[var(--bg)] px-5 py-6">
          <p className="max-w-[84%] self-end rounded-[var(--bubble-user)] bg-[var(--accent)] px-[14px] py-[10px] text-[var(--fs-sm)] leading-[1.5] text-[var(--accent-ink)]">
            What was Q3 revenue, and how did it compare to Q2?
          </p>

          <div className="max-w-[90%] self-start">
            <p className="rounded-[var(--bubble-bot)] bg-[var(--surface-2)] px-[15px] py-3 text-[var(--fs-sm)] leading-[var(--lh-normal)] text-[var(--text)]">
              Q3 revenue was $48.2M, up 14% from Q2&apos;s $42.3M — driven by the enterprise segment,
              which grew 22% quarter-over-quarter.
            </p>
            <div className="mt-[7px] flex flex-wrap gap-[6px]">
              {['p. 12', 'p. 13'].map((page) => (
                <span
                  key={page}
                  className="font-mono rounded-[var(--r-pill)] border border-[var(--border)] px-[9px] py-[3px] text-[var(--fs-mono)] text-[var(--text-dim)]"
                >
                  {page}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
