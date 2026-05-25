'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ApiError, authErrorMessage } from '@/lib/api/errors';

interface AuthFormProps {
  mode: 'login' | 'register';
  onSubmit: (values: { email: string; password: string }) => Promise<void>;
}

export function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const title = mode === 'login' ? 'Sign in' : 'Create account';
  const submitLabel = mode === 'login' ? 'Sign in' : 'Create account';
  const alternateHref = mode === 'login' ? '/register' : '/login';
  const alternateLabel =
    mode === 'login' ? 'Need an account? Register' : 'Already have an account? Sign in';

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
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-foreground">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-[var(--color-accent-cyan)]"
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-foreground">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          required
          minLength={mode === 'register' ? 8 : 1}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-[var(--color-accent-cyan)]"
        />
        {mode === 'register' ? (
          <p className="mt-1 text-xs text-muted">At least 8 characters</p>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? 'Please wait…' : submitLabel}
      </button>

      <p className="text-center text-sm text-muted">
        <Link href={alternateHref} className="text-accent-cyan hover:underline">
          {alternateLabel}
        </Link>
      </p>

      <h2 className="sr-only">{title}</h2>
    </form>
  );
}
