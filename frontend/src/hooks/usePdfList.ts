'use client';

import { useQuery } from '@tanstack/react-query';
import { listPdfs } from '@/lib/api/pdfs';
import { getAuthToken } from '@/lib/auth/session';

export function usePdfList() {
  const hasSession = Boolean(getAuthToken());
  return useQuery({
    queryKey: ['pdfs'],
    queryFn: listPdfs,
    enabled: hasSession,
  });
}
