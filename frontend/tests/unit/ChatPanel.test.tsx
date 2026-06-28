import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ChatPanel } from '@/components/chat/ChatPanel';
import {
  getConversationMessages,
  sendConversationMessage,
} from '@/lib/api/conversations';
import { ApiError } from '@/lib/api/errors';
import { renderWithClient } from '../test-utils';

vi.mock('@/lib/api/conversations', () => ({
  getConversationMessages: vi.fn(),
  sendConversationMessage: vi.fn(),
}));

const mockedGetMessages = vi.mocked(getConversationMessages);
const mockedSend = vi.mocked(sendConversationMessage);

beforeEach(() => {
  mockedGetMessages.mockResolvedValue([]);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ChatPanel', () => {
  it('is disabled when enabled=false', () => {
    renderWithClient(<ChatPanel pdfId="p1" conversationId="c1" enabled={false} />);
    expect(screen.getByText('Chat unlocks when parsing completes')).toBeTruthy();
    expect(screen.getByRole('textbox')).toHaveProperty('disabled', true);
  });

  it('hydrates existing history from the server', async () => {
    mockedGetMessages.mockResolvedValue([
      { role: 'user', content: 'earlier question', citations: [] },
      { role: 'assistant', content: 'earlier answer', citations: [2] },
    ]);

    renderWithClient(<ChatPanel pdfId="p1" conversationId="c1" enabled />);

    expect(await screen.findByText('earlier question')).toBeTruthy();
    expect(screen.getByText('earlier answer')).toBeTruthy();
    expect(screen.getByText('Sources: p. 2')).toBeTruthy();
  });

  it('sends to the conversation chat endpoint and renders the answer', async () => {
    mockedSend.mockResolvedValue({ answer: 'It is a report.', citations: [1, 3] });

    renderWithClient(<ChatPanel pdfId="p1" conversationId="c1" enabled />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'What is this?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(screen.getByText('What is this?')).toBeTruthy();
    expect(await screen.findByText('It is a report.')).toBeTruthy();
    expect(await screen.findByText('Sources: p. 1, 3')).toBeTruthy();
    expect(mockedSend).toHaveBeenCalledWith('c1', 'What is this?');
  });

  it('shows an accessible error and recovers when chat rejects', async () => {
    mockedSend.mockRejectedValue(new ApiError(409, 'PDF is not ready for chat yet'));

    renderWithClient(<ChatPanel pdfId="p1" conversationId="c1" enabled />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This PDF is not ready for chat yet. Please wait for parsing to finish.');
    await waitFor(() => expect(screen.getByRole('textbox')).toHaveProperty('disabled', false));
  });

  it('shows a generic error for unknown failures', async () => {
    mockedSend.mockRejectedValue(new Error('boom'));

    renderWithClient(<ChatPanel pdfId="p1" conversationId="c1" enabled />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');
  });
});
