'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ApiError, authErrorMessage } from '@/lib/api/errors';

interface AuthFormProps {
  mode: 'login' | 'register';
  onSubmit: (values: { email: string; password: string }) => Promise<void>;
}

const INPUT_CLASS =
  'w-full rounded-[var(--r-lg)] border border-[var(--border)] bg-[var(--surface)] px-[14px] py-3 text-[var(--fs-base)] text-[var(--text)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--focus-ring)]';

export function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';
  const title = isRegister ? 'Create your account' : 'Welcome back';
  const subtitle = isRegister
    ? 'Start chatting with your PDFs in seconds.'
    : 'Sign in to your document library.';
  const submitLabel = isRegister ? 'Create account' : 'Sign in';
  const alternateHref = isRegister ? '/login' : '/register';
  const altPrompt = isRegister ? 'Already have an account?' : 'New here?';
  const altLink = isRegister ? 'Sign in' : 'Create one';

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await onSubmit({ email, password });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(authErrorMessage(err));
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1 className="font-display text-[var(--fs-h2)] font-semibold tracking-[var(--ls-snug)] text-[var(--text)]">
        {title}
      </h1>
      <p className="mt-[6px] text-[var(--fs-sm)] text-[var(--text-dim)]">{subtitle}</p>

      <label
        htmlFor="email"
        className="mb-[7px] mt-[26px] block text-[12.5px] font-semibold text-[var(--text)]"
      >
        Email
      </label>
      <input
        id="email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className={INPUT_CLASS}
      />

      <label
        htmlFor="password"
        className="mb-[7px] mt-4 block text-[12.5px] font-semibold text-[var(--text)]"
      >
        Password
      </label>
      <input
        id="password"
        name="password"
        type="password"
        autoComplete={isRegister ? 'new-password' : 'current-password'}
        placeholder="••••••••"
        required
        minLength={isRegister ? 8 : 1}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className={INPUT_CLASS}
      />
      {isRegister ? (
        <p className="mt-[6px] text-[11.5px] text-[var(--text-dim)]">At least 8 characters</p>
      ) : null}

      {error ? (
        <p role="alert" className="mt-4 text-[var(--fs-sm)] text-[var(--danger)]">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-6 w-full cursor-pointer rounded-[var(--r-lg)] bg-[var(--accent)] px-4 py-[13px] text-[var(--fs-base)] font-bold text-[var(--accent-ink)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? 'Please wait…' : submitLabel}
      </button>

      <p className="mt-5 text-center text-[var(--fs-sm)] text-[var(--text-dim)]">
        {altPrompt}{' '}
        <Link href={alternateHref} className="font-semibold text-[var(--accent)] hover:underline">
          {altLink}
        </Link>
      </p>
    </form>
  );
}
