'use client';

import { useCallback, useRef, useState, type DragEvent } from 'react';
import type { UseMutationResult } from '@tanstack/react-query';
import { validatePdfFile } from '@/hooks/usePdfUpload';
import type { PdfDocument } from '@/types/pdf';

type UploadMutation = UseMutationResult<PdfDocument, Error, File>;

export function UploadDropzone({ upload }: { upload: UploadMutation }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
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

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!isPending) setIsDragOver(true);
  };

  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="space-y-4">
      <button
        type="button"
        disabled={isPending}
        onClick={() => inputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={[
          'w-full rounded-xl border-2 border-dashed border-border bg-surface p-12 text-center transition-shadow',
          'hover:ring-2 hover:ring-[var(--color-accent-cyan)]',
          isDragOver ? 'ring-2 ring-[var(--color-accent-cyan)]' : '',
          isPending ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="sr-only"
          disabled={isPending}
          onChange={(e) => {
            handleFile(e.target.files?.[0]);
            e.target.value = '';
          }}
        />
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-background">
          <PdfIcon />
        </div>
        <p className="text-sm font-medium text-foreground">
          {isPending ? 'Uploading…' : 'Drop PDF or click to browse'}
        </p>
        <p className="mt-1 text-xs text-muted">PDF only, up to 10 MB</p>
      </button>

      {validationError ? (
        <p role="alert" className="text-sm text-danger">
          {validationError}
        </p>
      ) : null}
    </div>
  );
}

function PdfIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-6 w-6 text-muted"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
      />
    </svg>
  );
}
