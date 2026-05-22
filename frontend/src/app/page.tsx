'use client';

import { AppShell } from '@/components/layout/AppShell';
import { UploadDropzone } from '@/components/upload/UploadDropzone';
import { UploadErrorAlert } from '@/components/upload/UploadErrorAlert';
import { usePdfUpload } from '@/hooks/usePdfUpload';

export default function Home() {
  const upload = usePdfUpload();

  return (
    <AppShell>
      <UploadDropzone upload={upload} />
      <UploadErrorAlert error={upload.error} />
    </AppShell>
  );
}
