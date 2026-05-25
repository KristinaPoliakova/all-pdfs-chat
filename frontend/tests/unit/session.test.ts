import { beforeEach, describe, expect, it } from 'vitest';
import {
  AUTH_TOKEN_STORAGE_KEY,
  clearAuthSession,
  getAuthToken,
  setAuthToken,
} from '@/lib/auth/session';

describe('auth session', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when no token is stored', () => {
    expect(getAuthToken()).toBeNull();
  });

  it('stores and retrieves the bearer token', () => {
    setAuthToken('secret-token');
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe('secret-token');
    expect(getAuthToken()).toBe('secret-token');
  });

  it('clears the stored token', () => {
    setAuthToken('secret-token');
    clearAuthSession();
    expect(getAuthToken()).toBeNull();
  });
});
