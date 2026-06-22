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

export function chatErrorMessage(err: ApiError): string {
  switch (err.status) {
    case 401:
      return 'Please sign in to continue.';
    case 404:
      return 'This PDF could not be found.';
    case 409:
      return 'This PDF is not ready for chat yet. Please wait for parsing to finish.';
    case 502:
      return err.detail || 'The assistant is temporarily unavailable. Please try again.';
    case 504:
      return err.detail || 'The assistant took too long to respond. Please try again.';
    default:
      return 'Something went wrong. Please try again.';
  }
}
