export const AUTH_TOKEN_STORAGE_KEY = 'all_pdfs_chat_token';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

/**
 * Subscribe to auth-token changes. Fires for in-tab updates (set/clear) — which
 * the native `storage` event does NOT cover — as well as cross-tab `storage`
 * events. Lets the header and library stay in sync from a single source.
 */
export function subscribeAuth(callback: () => void): () => void {
  listeners.add(callback);
  if (typeof window !== 'undefined') {
    window.addEventListener('storage', callback);
  }
  return () => {
    listeners.delete(callback);
    if (typeof window !== 'undefined') {
      window.removeEventListener('storage', callback);
    }
  };
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
  notify();
}

export function clearAuthSession(): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  notify();
}
