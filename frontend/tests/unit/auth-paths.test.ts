import { describe, expect, it } from 'vitest';
import { loginPath, registerPath, safeReturnTo } from '@/lib/auth/paths';

describe('safeReturnTo', () => {
  it('defaults to home for missing or unsafe paths', () => {
    expect(safeReturnTo(null)).toBe('/');
    expect(safeReturnTo('https://evil.com')).toBe('/');
    expect(safeReturnTo('//evil.com')).toBe('/');
  });

  it('rejects auth pages as return targets', () => {
    expect(safeReturnTo('/login')).toBe('/');
    expect(safeReturnTo('/register?x=1')).toBe('/');
  });

  it('allows in-app paths', () => {
    expect(safeReturnTo('/pdfs/abc')).toBe('/pdfs/abc');
  });
});

describe('loginPath', () => {
  it('includes returnTo for deep links', () => {
    expect(loginPath('/pdfs/abc')).toBe('/login?returnTo=%2Fpdfs%2Fabc');
  });
});

describe('registerPath', () => {
  it('includes returnTo for deep links', () => {
    expect(registerPath('/pdfs/abc')).toBe('/register?returnTo=%2Fpdfs%2Fabc');
  });
});
