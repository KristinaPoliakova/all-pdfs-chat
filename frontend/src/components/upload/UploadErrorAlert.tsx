import { ApiError, uploadErrorMessage } from '@/lib/api/errors';

export function UploadErrorAlert({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <div
      role="alert"
      className="mt-4 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger"
    >
      {uploadErrorMessage(error)}
    </div>
  );
}
