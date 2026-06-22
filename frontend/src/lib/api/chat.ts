import { apiFetch } from './client';

export interface ChatAnswer {
  answer: string;
  citations: number[];
}

export async function sendChatMessage(pdfId: string, message: string): Promise<ChatAnswer> {
  return apiFetch<ChatAnswer>(`/pdfs/${encodeURIComponent(pdfId)}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
}
