'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { AuthShell } from '@/components/auth/AuthShell';
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
      <AuthShell>
        <AuthForm
          mode="register"
          onSubmit={async (values) => {
            await register(values);
            router.replace(returnTo);
          }}
        />
      </AuthShell>
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
