import { cleanup, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PdfLibrary } from '@/components/pdf/PdfLibrary';
import { listPdfs } from '@/lib/api/pdfs';
import { setAuthToken, clearAuthSession } from '@/lib/auth/session';
import { renderWithClient } from '../test-utils';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/lib/api/pdfs', () => ({
  listPdfs: vi.fn(),
  uploadPdf: vi.fn(),
  renamePdf: vi.fn(),
  deletePdf: vi.fn(),
}));
const mockedList = vi.mocked(listPdfs);

afterEach(() => {
  cleanup();
  clearAuthSession();
  vi.clearAllMocks();
});

describe('PdfLibrary', () => {
  it('renders the signed-in user\'s PDFs', async () => {
    setAuthToken('tok');
    mockedList.mockResolvedValue([
      { id: 'p1', filename: 'a.pdf', size_bytes: 1, created_at: 'x', processing_status: 'parsed' },
    ]);

    renderWithClient(<PdfLibrary />);

    expect(await screen.findByText('a.pdf')).toBeTruthy();
  });

  it('shows an empty state when there are no PDFs', async () => {
    setAuthToken('tok');
    mockedList.mockResolvedValue([]);

    renderWithClient(<PdfLibrary />);

    expect(await screen.findByText(/no pdfs yet/i)).toBeTruthy();
  });

  it('renders nothing for guests (no token)', () => {
    const { container } = renderWithClient(<PdfLibrary />);
    expect(container).toBeEmptyDOMElement();
    expect(mockedList).not.toHaveBeenCalled();
  });
});
