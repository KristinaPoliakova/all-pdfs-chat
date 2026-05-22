import type { PdfProcessingStatus } from '@/types/pdf';

const TERMINAL: PdfProcessingStatus[] = [
  'parsed',
  'classification_failed',
  'parsing_failed',
];

const IN_PROGRESS: PdfProcessingStatus[] = [
  'uploaded',
  'classifying',
  'classified',
  'parsing',
];

const LABELS: Record<PdfProcessingStatus, string> = {
  uploaded: 'Uploaded',
  classifying: 'Classifying pages',
  classified: 'Classified',
  parsing: 'Extracting text',
  parsed: 'Ready',
  classification_failed: 'Classification failed',
  parsing_failed: 'Parsing failed',
};

export function isTerminal(status: PdfProcessingStatus): boolean {
  return TERMINAL.includes(status);
}

export function isInProgress(status: PdfProcessingStatus): boolean {
  return IN_PROGRESS.includes(status);
}

export function isChatEnabled(status: PdfProcessingStatus): boolean {
  return status === 'parsed';
}

export function statusLabel(status: PdfProcessingStatus): string {
  return LABELS[status];
}
