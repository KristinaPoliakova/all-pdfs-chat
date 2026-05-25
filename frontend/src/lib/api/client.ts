import { getAuthToken } from '@/lib/auth/session';
import { ApiError } from './errors';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api/v1';

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { skipAuth?: boolean },
): Promise<T> {
  const { skipAuth, headers, ...rest } = init ?? {};
  const mergedHeaders = new Headers(headers);

  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      mergedHeaders.set('Authorization', `Bearer ${token}`);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: mergedHeaders,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* ignore */
    }

    if (res.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }

    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}
