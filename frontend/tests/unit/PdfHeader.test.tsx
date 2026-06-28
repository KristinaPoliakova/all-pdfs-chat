import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PdfHeader } from '@/components/pdf/PdfHeader';
import { deletePdf, renamePdf } from '@/lib/api/pdfs';
import { renderWithClient } from '../test-utils';
import type { PdfDocument } from '@/types/pdf';

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock('@/lib/api/pdfs', () => ({ renamePdf: vi.fn(), deletePdf: vi.fn() }));

const mockedRename = vi.mocked(renamePdf);
const mockedDelete = vi.mocked(deletePdf);

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

describe('PdfHeader', () => {
  it('renames the pdf', async () => {
    mockedRename.mockResolvedValue({ ...doc, filename: 'new.pdf' });
    renderWithClient(<PdfHeader document={doc} />);

    fireEvent.click(screen.getByRole('button', { name: /rename/i }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'new.pdf' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(mockedRename).toHaveBeenCalledWith('p1', 'new.pdf'));
  });

  it('deletes the pdf after confirmation and navigates home', async () => {
    mockedDelete.mockResolvedValue(undefined);
    renderWithClient(<PdfHeader document={doc} />);

    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete' })); // confirm

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('p1'));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/'));
  });
});
