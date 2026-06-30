'use client';

import { useSyncExternalStore } from 'react';
import { getAuthToken, subscribeAuth } from '@/lib/auth/session';

/**
 * Reactive "is there a session token?" signal. The token lives in localStorage
 * (unavailable during SSR), so the server snapshot is `false`; the client value
 * resolves after hydration and updates in-tab on login/logout. This is the
 * single source of truth for gating signed-in UI.
 */
export function useHasSession(): boolean {
  return useSyncExternalStore(
    subscribeAuth,
    () => getAuthToken() !== null,
    () => false,
  );
}
