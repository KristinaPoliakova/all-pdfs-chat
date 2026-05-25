export const AUTH_TOKEN_STORAGE_KEY = 'all_pdfs_chat_token';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function getAuthToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }
  return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setAuthToken(token: string): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthSession(): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}
