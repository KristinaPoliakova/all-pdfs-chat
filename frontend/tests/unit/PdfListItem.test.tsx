import { cleanup, fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PdfListItem } from '@/components/pdf/PdfListItem';
import { renamePdf } from '@/lib/api/pdfs';
import { ApiError } from '@/lib/api/errors';
import { renderWithClient } from '../test-utils';
import type { PdfDocument } from '@/types/pdf';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/lib/api/pdfs', () => ({ renamePdf: vi.fn(), deletePdf: vi.fn() }));

const mockedRename = vi.mocked(renamePdf);

const doc: PdfDocument = {
  id: 'p1',
  filename: 'report.pdf',
  size_bytes: 10,
  created_at: 'x',
  processing_status: 'parsed',
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('PdfListItem', () => {
  it('surfaces a rename failure as a visible alert (does not swallow the error while editing)', async () => {
    mockedRename.mockRejectedValue(new ApiError(422, 'Title too long'));
    renderWithClient(<PdfListItem document={doc} />);

    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'renamed.pdf' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Title too long');
  });
});
