import Link from 'next/link';
import { loginPath, registerPath } from '@/lib/auth/paths';

interface SignInPromptProps {
  message: string;
  returnTo?: string;
}

export function SignInPrompt({ message, returnTo = '/' }: SignInPromptProps) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-6 text-center">
      <p className="text-sm text-muted">{message}</p>
      <div className="mt-4 flex items-center justify-center gap-4 text-sm">
        <Link href={loginPath(returnTo)} className="font-medium text-accent-cyan hover:underline">
          Sign in
        </Link>
        <span className="text-muted" aria-hidden>
          ·
        </span>
        <Link href={registerPath(returnTo)} className="font-medium text-accent-cyan hover:underline">
          Create account
        </Link>
      </div>
    </div>
  );
}
