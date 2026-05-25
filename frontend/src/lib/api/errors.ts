export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

export function authErrorMessage(err: ApiError): string {
  switch (err.status) {
    case 400:
      return err.detail;
    case 401:
      return 'Please sign in to continue.';
    case 409:
      return 'An account with this email already exists.';
    default:
      return 'Authentication failed. Please try again.';
  }
}

export function uploadErrorMessage(err: ApiError): string {
  switch (err.status) {
    case 400:
      return err.detail;
    case 401:
      return 'Please sign in to continue.';
    case 413:
      return 'File is too large. Maximum size is 10 MB.';
    case 415:
      return 'Only PDF files are supported.';
    default:
      return 'Upload failed. Please try again.';
  }
}
