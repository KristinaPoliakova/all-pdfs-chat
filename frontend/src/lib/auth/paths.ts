export function safeReturnTo(path: string | null | undefined): string {
  if (!path || !path.startsWith('/') || path.startsWith('//')) {
    return '/';
  }
  if (path.startsWith('/login') || path.startsWith('/register')) {
    return '/';
  }
  return path;
}

export function loginPath(returnTo?: string): string {
  const destination = safeReturnTo(returnTo);
  if (destination === '/') {
    return '/login';
  }
  return `/login?returnTo=${encodeURIComponent(destination)}`;
}

export function registerPath(returnTo?: string): string {
  const destination = safeReturnTo(returnTo);
  if (destination === '/') {
    return '/register';
  }
  return `/register?returnTo=${encodeURIComponent(destination)}`;
}
