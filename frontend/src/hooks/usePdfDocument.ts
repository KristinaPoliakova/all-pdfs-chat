'use client';

import { useQuery } from '@tanstack/react-query';
import { getPdf } from '@/lib/api/pdfs';
import { getAuthToken } from '@/lib/auth/session';
import { isTerminal } from '@/lib/processing-status';
import { useAuth } from '@/hooks/useAuth';

export function usePdfDocument(pdfId: string) {
  const { isLoading: authLoading } = useAuth();
  const hasSession = Boolean(getAuthToken());

  return useQuery({
    queryKey: ['pdf', pdfId],
    queryFn: () => getPdf(pdfId),
    enabled: Boolean(pdfId) && !authLoading && hasSession,
    refetchInterval: (query) => {
      const status = query.state.data?.processing_status;
      return status && isTerminal(status) ? false : 1500;
    },
    refetchIntervalInBackground: true,
  });
}
