import type { PdfDocument } from '@/types/pdf';
import { apiFetch } from './client';

export async function uploadPdf(file: File): Promise<PdfDocument> {
  const form = new FormData();
  form.append('file', file);
  return apiFetch<PdfDocument>('/pdfs', { method: 'POST', body: form });
}

export async function getPdf(id: string): Promise<PdfDocument> {
  return apiFetch<PdfDocument>(`/pdfs/${id}`);
}

export async function listPdfs(): Promise<PdfDocument[]> {
  return apiFetch<PdfDocument[]>('/pdfs');
}

export async function renamePdf(id: string, filename: string): Promise<PdfDocument> {
  return apiFetch<PdfDocument>(`/pdfs/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  });
}

export async function deletePdf(id: string): Promise<void> {
  await apiFetch<void>(`/pdfs/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
