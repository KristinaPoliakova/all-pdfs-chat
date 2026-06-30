import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationSidebar } from '@/components/conversation/ConversationSidebar';
import { createConversation, listConversations } from '@/lib/api/conversations';
import { ApiError } from '@/lib/api/errors';
import { renderWithClient } from '../test-utils';

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ id: 'p1' }),
}));
vi.mock('@/lib/api/conversations', () => ({
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  renameConversation: vi.fn(),
  deleteConversation: vi.fn(),
}));

const mockedList = vi.mocked(listConversations);
const mockedCreate = vi.mocked(createConversation);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ConversationSidebar', () => {
  it('lists conversations with the New conversation fallback title', async () => {
    mockedList.mockResolvedValue([
      { id: 'c1', pdf_id: 'p1', title: 'Revenue?', created_at: 'x', updated_at: 'x' },
      { id: 'c2', pdf_id: 'p1', title: null, created_at: 'x', updated_at: 'x' },
    ]);

    renderWithClient(<ConversationSidebar pdfId="p1" activeId="c1" parsed />);

    expect(await screen.findByText('Revenue?')).toBeTruthy();
    // The untitled conversation renders its fallback title as a link. Scope to
    // the link role so it isn't confused with the "New conversation" button.
    expect(screen.getByRole('link', { name: 'New conversation' })).toBeTruthy();
  });

  it('creates a conversation and navigates to it', async () => {
    mockedList.mockResolvedValue([]);
    mockedCreate.mockResolvedValue({ id: 'c9', pdf_id: 'p1', title: null, created_at: 'x', updated_at: 'x' });

    renderWithClient(<ConversationSidebar pdfId="p1" activeId={null} parsed />);

    fireEvent.click(await screen.findByRole('button', { name: /new conversation/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/pdfs/p1/conversations/c9'));
  });

  it('disables creation when the PDF is not parsed', async () => {
    mockedList.mockResolvedValue([]);

    renderWithClient(<ConversationSidebar pdfId="p1" activeId={null} parsed={false} />);

    expect(screen.getByRole('button', { name: /new conversation/i })).toHaveProperty('disabled', true);
  });

  it('surfaces a visible error when conversation creation fails', async () => {
    mockedList.mockResolvedValue([]);
    mockedCreate.mockRejectedValue(new ApiError(409, 'PDF is not ready'));

    renderWithClient(<ConversationSidebar pdfId="p1" activeId={null} parsed />);

    fireEvent.click(await screen.findByRole('button', { name: /new conversation/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This PDF is not ready yet. Please wait for parsing to finish.');
    expect(pushMock).not.toHaveBeenCalled();
  });
});
