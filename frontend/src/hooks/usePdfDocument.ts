'use client';

import { useQuery } from '@tanstack/react-query';
import { getPdf } from '@/lib/api/pdfs';
import { isTerminal } from '@/lib/processing-status';

export function usePdfDocument(pdfId: string) {
  return useQuery({
    queryKey: ['pdf', pdfId],
    queryFn: () => getPdf(pdfId),
    enabled: Boolean(pdfId),
    refetchInterval: (query) => {
      const status = query.state.data?.processing_status;
      return status && isTerminal(status) ? false : 1500;
    },
    refetchIntervalInBackground: true,
  });
}
