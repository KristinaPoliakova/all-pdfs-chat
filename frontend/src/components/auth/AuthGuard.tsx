'use client';

import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { safeReturnTo } from '@/lib/auth/paths';

export function GuestGuard({
  children,
  returnTo,
}: {
  children: ReactNode;
  returnTo?: string | null;
}) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const destination = safeReturnTo(returnTo);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(destination);
    }
  }, [isAuthenticated, router, destination]);

  // A present session token flips isAuthenticated synchronously after mount, so
  // a signed-in visitor is redirected away instead of seeing the auth form.
  if (isAuthenticated) {
    return null;
  }

  return children;
}
