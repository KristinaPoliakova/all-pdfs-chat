import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProcessingStatusBadge } from '@/components/pdf/ProcessingStatusBadge';
import { statusLabel } from '@/lib/processing-status';
import type { PdfProcessingStatus } from '@/types/pdf';

const ALL_STATUSES: PdfProcessingStatus[] = [
  'uploaded',
  'classifying',
  'classified',
  'parsing',
  'parsed',
  'classification_failed',
  'parsing_failed',
];

describe('ProcessingStatusBadge', () => {
  it.each(ALL_STATUSES)('renders label for %s', (status) => {
    render(<ProcessingStatusBadge status={status} />);
    expect(screen.getByText(statusLabel(status))).toBeTruthy();
  });
});
