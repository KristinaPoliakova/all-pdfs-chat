import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { usePdfList } from '@/hooks/usePdfList';
import { listPdfs } from '@/lib/api/pdfs';
import { setAuthToken, clearAuthSession } from '@/lib/auth/session';
import { makeTestQueryClient } from '../test-utils';

vi.mock('@/lib/api/pdfs', () => ({ listPdfs: vi.fn() }));
const mockedListPdfs = vi.mocked(listPdfs);

afterEach(() => {
  clearAuthSession();
  vi.clearAllMocks();
});

describe('usePdfList', () => {
  it('fetches the pdf list when a session token is present', async () => {
    setAuthToken('tok');
    mockedListPdfs.mockResolvedValue([
      { id: 'p1', filename: 'a.pdf', size_bytes: 1, created_at: 'x', processing_status: 'parsed' },
    ]);
    const client = makeTestQueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => usePdfList(), { wrapper });

    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(mockedListPdfs).toHaveBeenCalledOnce();
  });

  it('does not fetch when there is no session token', async () => {
    const client = makeTestQueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    renderHook(() => usePdfList(), { wrapper });

    expect(mockedListPdfs).not.toHaveBeenCalled();
  });
});
