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
