'use client';

import { useState, type DragEvent } from 'react';
import { Plus } from 'lucide-react';
import { useFileUpload } from '@/hooks/usePdfUpload';
import { UploadErrorAlert } from '@/components/upload/UploadErrorAlert';

export function UploadDropzone() {
  const { inputRef, isPending, validationError, handleFile, openPicker, upload } = useFileUpload();
  const [isDragOver, setIsDragOver] = useState(false);

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
    <div className="flex flex-col gap-2">
      <button
        type="button"
        disabled={isPending}
        onClick={openPicker}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={[
          'flex min-h-[236px] w-full cursor-pointer flex-col items-center justify-center gap-[10px] rounded-[var(--r-2xl)] border-[1.5px] border-dashed p-6 text-center transition-colors',
          isDragOver ? 'border-[var(--accent)]' : 'border-[var(--border)]',
          isPending ? 'cursor-not-allowed opacity-60' : 'hover:border-[var(--accent)]',
        ].join(' ')}
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
        <span className="flex h-[46px] w-[46px] items-center justify-center rounded-[13px] bg-[var(--surface-2)] text-[var(--accent)]">
          <Plus className="h-6 w-6" strokeWidth={1.75} aria-hidden />
        </span>
        <span className="text-[13px] font-semibold text-[var(--text)]">
          {isPending ? 'Uploading…' : 'Drop a PDF'}
        </span>
        <span className="text-[11.5px] text-[var(--text-dim)]">or click to browse · up to 10 MB</span>
      </button>

      {validationError ? (
        <p role="alert" className="text-[12px] text-[var(--danger)]">
          {validationError}
        </p>
      ) : null}
      <UploadErrorAlert error={upload.error} returnTo="/" />
    </div>
  );
}
