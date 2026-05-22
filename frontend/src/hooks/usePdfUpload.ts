'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { uploadPdf } from '@/lib/api/pdfs';

const MAX_BYTES = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_BYTES ?? 10485760);

export function validatePdfFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    return 'Only PDF files are supported.';
  }
  if (file.size > MAX_BYTES) {
    return 'File is too large. Maximum size is 10 MB.';
  }
  return null;
}

export function usePdfUpload() {
  const router = useRouter();
  return useMutation({
    mutationFn: uploadPdf,
    onSuccess: (doc) => router.push(`/pdfs/${doc.id}`),
  });
}
