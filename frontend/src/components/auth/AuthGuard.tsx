'use client';

import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { safeReturnTo } from '@/lib/auth/paths';

function AuthLoading() {
  return (
    <div className="animate-pulse space-y-4 rounded-lg border border-border p-6">
      <div className="h-5 w-1/3 rounded bg-border" />
      <div className="h-4 w-2/3 rounded bg-border" />
    </div>
  );
}

export function GuestGuard({
  children,
  returnTo,
}: {
  children: ReactNode;
  returnTo?: string | null;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const destination = safeReturnTo(returnTo);

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(destination);
    }
  }, [isLoading, user, router, destination]);

  if (isLoading) {
    return <AuthLoading />;
  }

  if (user) {
    return null;
  }

  return children;
}
