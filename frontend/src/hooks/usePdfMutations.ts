'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deletePdf, renamePdf } from '@/lib/api/pdfs';

export function useRenamePdf() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, filename }: { id: string; filename: string }) => renamePdf(id, filename),
    onSuccess: (pdf) => {
      void qc.invalidateQueries({ queryKey: ['pdfs'] });
      void qc.invalidateQueries({ queryKey: ['pdf', pdf.id] });
    },
  });
}

export function useDeletePdf() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deletePdf(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['pdfs'] });
    },
  });
}
