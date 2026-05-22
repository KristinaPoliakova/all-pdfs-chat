import { ApiError, uploadErrorMessage } from '@/lib/api/errors';

function errorMessage(error: unknown): string | null {
  if (!error) {
    return null;
  }
  if (error instanceof ApiError) {
    return uploadErrorMessage(error);
  }
  return 'Upload failed. Please try again.';
}

export function UploadErrorAlert({ error }: { error: unknown }) {
  const message = errorMessage(error);
  if (!message) {
    return null;
  }

  return (
    <div
      role="alert"
      className="mt-4 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger"
    >
      {message}
    </div>
  );
}
