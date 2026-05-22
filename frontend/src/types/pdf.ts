export type PdfProcessingStatus =
  | 'uploaded'
  | 'classifying'
  | 'classified'
  | 'parsing'
  | 'parsed'
  | 'classification_failed'
  | 'parsing_failed';

export interface PdfDocument {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
  processing_status: PdfProcessingStatus;
  page_count?: number | null;
  classification_error?: string | null;
  classified_at?: string | null;
  parsing_error?: string | null;
  parsed_at?: string | null;
}
