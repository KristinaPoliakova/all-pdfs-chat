'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import * as authApi from '@/lib/api/auth';
import { setUnauthorizedHandler } from '@/lib/api/client';
import { ApiError } from '@/lib/api/errors';
import { clearAuthSession, getAuthToken, setAuthToken } from '@/lib/auth/session';
import { useHasSession } from '@/hooks/useSession';
import type { LoginRequest, RegisterRequest, User } from '@/types/auth';

interface AuthContextValue {
  user: User | null;
  /** Authoritative signed-in flag, driven by the session token (reactive). */
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (body: LoginRequest) => Promise<void>;
  register: (body: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isAuthenticated = useHasSession();

  const clearSession = useCallback(() => {
    clearAuthSession();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getAuthToken()) {
        if (!cancelled) setIsLoading(false);
        return;
      }

      try {
        const me = await authApi.getMe();
        if (!cancelled) setUser(me);
      } catch (error) {
        // Only an explicit 401 means the session is invalid. Transient failures
        // (network blips, 5xx, timeouts) must NOT drop a still-valid token —
        // doing so logs the user out of the UI while their data still loads.
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (body: LoginRequest) => {
    const result = await authApi.login(body);
    setAuthToken(result.token);
    setUser(result.user);
  }, []);

  const register = useCallback(async (body: RegisterRequest) => {
    const result = await authApi.register(body);
    setAuthToken(result.token);
    setUser(result.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getAuthToken()) {
        await authApi.logout();
      }
    } catch {
      /* revoke best-effort */
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, isAuthenticated, isLoading, login, register, logout }),
    [user, isAuthenticated, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
