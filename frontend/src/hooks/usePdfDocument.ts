'use client';

import { useQuery } from '@tanstack/react-query';
import { getPdf } from '@/lib/api/pdfs';
import { isTerminal } from '@/lib/processing-status';
import { useAuth } from '@/hooks/useAuth';
import { useHasSession } from '@/hooks/useSession';

export function usePdfDocument(pdfId: string) {
  const { isLoading: authLoading } = useAuth();
  const hasSession = useHasSession();

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
