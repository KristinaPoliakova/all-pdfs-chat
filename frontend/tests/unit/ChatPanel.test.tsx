import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { sendChatMessage } from '@/lib/api/chat';
import { ApiError } from '@/lib/api/errors';

vi.mock('@/lib/api/chat', () => ({
  sendChatMessage: vi.fn(),
}));

const mockedSendChatMessage = vi.mocked(sendChatMessage);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ChatPanel', () => {
  it('is disabled when enabled=false', () => {
    render(<ChatPanel pdfId="pdf-1" enabled={false} />);
    expect(screen.getByText('Chat unlocks when parsing completes')).toBeTruthy();
    expect(screen.getByRole('textbox')).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Send' })).toHaveProperty('disabled', true);
  });

  it('renders the user message and the assistant answer from the API', async () => {
    mockedSendChatMessage.mockResolvedValue({
      answer: 'This document is a quarterly financial report.',
      citations: [],
    });

    render(<ChatPanel pdfId="pdf-1" enabled />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'What is this document about?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(screen.getByText('What is this document about?')).toBeTruthy();

    await waitFor(() => {
      expect(
        screen.getByText('This document is a quarterly financial report.'),
      ).toBeTruthy();
    });

    expect(mockedSendChatMessage).toHaveBeenCalledWith('pdf-1', 'What is this document about?');
  });

  it('renders citations under the assistant answer when present', async () => {
    mockedSendChatMessage.mockResolvedValue({
      answer: 'See the referenced pages.',
      citations: [1, 3],
    });

    render(<ChatPanel pdfId="pdf-1" enabled />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Where?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('Sources: p. 1, 3')).toBeTruthy();
  });

  it('shows an accessible error and recovers when the API rejects', async () => {
    mockedSendChatMessage.mockRejectedValue(
      new ApiError(409, 'PDF is not ready for chat yet'),
    );

    render(<ChatPanel pdfId="pdf-1" enabled />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Question?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(
      'This PDF is not ready for chat yet. Please wait for parsing to finish.',
    );

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toHaveProperty('disabled', false);
    });
  });

  it('shows a generic error message for unknown failures', async () => {
    mockedSendChatMessage.mockRejectedValue(new Error('boom'));

    render(<ChatPanel pdfId="pdf-1" enabled />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Question?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Something went wrong. Please try again.');
  });
});
