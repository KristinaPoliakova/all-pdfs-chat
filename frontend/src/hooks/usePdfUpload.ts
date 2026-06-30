'use client';

import { useCallback, useRef, useState } from 'react';
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

/**
 * Shared upload controller for the file picker UI (top-bar button + dropzone
 * tile). Owns client-side validation and exposes a hidden-input ref so callers
 * can render a styled trigger that opens the OS file dialog.
 */
export function useFileUpload() {
  const upload = usePdfUpload();
  const inputRef = useRef<HTMLInputElement>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { mutate, isPending } = upload;

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file || isPending) return;
      const err = validatePdfFile(file);
      if (err) {
        setValidationError(err);
        return;
      }
      setValidationError(null);
      mutate(file);
    },
    [isPending, mutate],
  );

  const openPicker = useCallback(() => {
    if (!isPending) inputRef.current?.click();
  }, [isPending]);

  return { upload, inputRef, isPending, validationError, handleFile, openPicker };
}
