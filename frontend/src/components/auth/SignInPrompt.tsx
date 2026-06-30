import Link from 'next/link';
import { loginPath, registerPath } from '@/lib/auth/paths';

interface SignInPromptProps {
  message: string;
  returnTo?: string;
}

export function SignInPrompt({ message, returnTo = '/' }: SignInPromptProps) {
  return (
    <div className="rounded-[var(--r-xl)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-6 text-center">
      <p className="text-[var(--fs-sm)] text-[var(--text-dim)]">{message}</p>
      <div className="mt-4 flex items-center justify-center gap-4 text-[var(--fs-sm)]">
        <Link href={loginPath(returnTo)} className="font-semibold text-[var(--accent)] hover:underline">
          Sign in
        </Link>
        <span className="text-[var(--text-dim)]" aria-hidden>
          ·
        </span>
        <Link
          href={registerPath(returnTo)}
          className="font-semibold text-[var(--accent)] hover:underline"
        >
          Create account
        </Link>
      </div>
    </div>
  );
}
