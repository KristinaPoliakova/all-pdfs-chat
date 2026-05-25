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
      className="mt-4 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger"
    >
      <p>{message}</p>
      {isUnauthorized ? (
        <Link
          href={loginPath(returnTo)}
          className="mt-2 inline-block font-medium text-accent-cyan hover:underline"
        >
          Sign in to upload
        </Link>
      ) : null}
    </div>
  );
}
