import { describe, expect, it } from 'vitest';
import { ApiError, authErrorMessage, uploadErrorMessage } from '@/lib/api/errors';

describe('authErrorMessage', () => {
  it('maps 401 to sign-in prompt', () => {
    expect(authErrorMessage(new ApiError(401, 'Unauthorized'))).toBe(
      'Please sign in to continue.',
    );
  });

  it('maps 409 to account exists message', () => {
    expect(authErrorMessage(new ApiError(409, 'User already exists'))).toBe(
      'An account with this email already exists.',
    );
  });

  it('passes through 400 validation detail', () => {
    expect(authErrorMessage(new ApiError(400, 'Password too short'))).toBe(
      'Password too short',
    );
  });
});

describe('uploadErrorMessage with auth', () => {
  it('maps 401 to sign-in prompt', () => {
    expect(uploadErrorMessage(new ApiError(401, 'Not authenticated'))).toBe(
      'Please sign in to continue.',
    );
  });
});
