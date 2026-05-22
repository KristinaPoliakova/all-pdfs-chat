import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ChatPanel } from '@/components/chat/ChatPanel';

afterEach(() => {
  cleanup();
});

describe('ChatPanel', () => {
  it('is disabled when enabled=false', () => {
    render(<ChatPanel pdfId="pdf-1" enabled={false} />);
    expect(screen.getByText('Chat unlocks when parsing completes')).toBeTruthy();
    expect(screen.getByRole('textbox')).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Send' })).toHaveProperty('disabled', true);
  });

  it('when enabled, send message shows stub reply', async () => {
    render(<ChatPanel pdfId="pdf-1" enabled />);

    const panel = screen
      .getByText('Preview mode — responses are placeholders')
      .closest('section') as HTMLElement;

    const input = within(panel).getByRole('textbox');
    fireEvent.change(input, { target: { value: 'What is this document about?' } });
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }));

    expect(within(panel).getByText('What is this document about?')).toBeTruthy();

    await waitFor(
      () => {
        expect(
          within(panel).getByText(
            'Chat API is not connected yet. Your PDF is parsed and ready — answers will appear here once the backend ships.',
          ),
        ).toBeTruthy();
      },
      { timeout: 2000 },
    );
  });
});
