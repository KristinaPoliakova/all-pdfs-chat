'use client';

import { useQuery } from '@tanstack/react-query';
import { listPdfs } from '@/lib/api/pdfs';
import { useHasSession } from '@/hooks/useSession';

export function usePdfList() {
  const hasSession = useHasSession();
  return useQuery({
    queryKey: ['pdfs'],
    queryFn: listPdfs,
    enabled: hasSession,
  });
}
