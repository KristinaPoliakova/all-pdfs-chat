'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { AuthForm } from '@/components/auth/AuthForm';
import { GuestGuard } from '@/components/auth/AuthGuard';
import { useAuth } from '@/hooks/useAuth';
import { safeReturnTo } from '@/lib/auth/paths';

function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = safeReturnTo(searchParams.get('returnTo'));

  return (
    <GuestGuard returnTo={returnTo}>
      <AppShell>
        <div className="mx-auto max-w-sm">
          <h2 className="mb-6 text-xl font-semibold tracking-tight text-foreground">
            Create account
          </h2>
          <AuthForm
            mode="register"
            onSubmit={async (values) => {
              await register(values);
              router.replace(returnTo);
            }}
          />
        </div>
      </AppShell>
    </GuestGuard>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  );
}
