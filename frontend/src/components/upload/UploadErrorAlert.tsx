import Link from 'next/link';
import { ApiError, uploadErrorMessage } from '@/lib/api/errors';
import { loginPath } from '@/lib/auth/paths';

function errorMessage(error: unknown): string | null {
  if (!error) {
    return null;
  }
  if (error instanceof ApiError) {
    return uploadErrorMessage(error);
  }
  return 'Upload failed. Please try again.';
}

export function UploadErrorAlert({
  error,
  returnTo = '/',
}: {
  error: unknown;
  returnTo?: string;
}) {
  const message = errorMessage(error);
  if (!message) {
    return null;
  }

  const isUnauthorized = error instanceof ApiError && error.status === 401;

  return (
    <div
      role="alert"
      className="rounded-[var(--r-xl)] border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-4 py-3 text-[var(--fs-sm)] text-[var(--danger)]"
    >
      <p>{message}</p>
      {isUnauthorized ? (
        <Link
          href={loginPath(returnTo)}
          className="mt-2 inline-block font-semibold text-[var(--accent)] hover:underline"
        >
          Sign in to upload
        </Link>
      ) : null}
    </div>
  );
}
