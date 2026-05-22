'use client';

import { useCallback, useId, useState, type KeyboardEvent } from 'react';
import { sendChatMessage, type ChatMessage } from '@/lib/chat/stub-chat';

function LockIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-5 w-5 shrink-0"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
      />
    </svg>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <p
        className={[
          'max-w-[85%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-foreground text-background'
            : 'border border-border bg-background text-foreground',
        ].join(' ')}
      >
        {message.content}
      </p>
    </div>
  );
}

export function ChatPanel({ pdfId, enabled }: { pdfId: string; enabled: boolean }) {
  const inputId = useId();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!enabled || !text || isSending) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };

    setDraft('');
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);

    try {
      const reply = await sendChatMessage(pdfId, text);
      setMessages((prev) => [...prev, reply]);
    } finally {
      setIsSending(false);
    }
  }, [draft, enabled, isSending, pdfId]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey) return;
    e.preventDefault();
    void send();
  };

  if (!enabled) {
    return (
      <section
        className="mt-6 rounded-lg border border-border bg-surface/80 p-6 opacity-70"
        aria-labelledby={`${inputId}-heading`}
      >
        <div className="flex items-center gap-2 text-muted">
          <LockIcon />
          <h2 id={`${inputId}-heading`} className="text-sm font-medium">
            Chat unlocks when parsing completes
          </h2>
        </div>
        <label htmlFor={inputId} className="sr-only">
          Chat message
        </label>
        <textarea
          id={inputId}
          disabled
          rows={3}
          placeholder="Ask a question about this PDF…"
          className="mt-4 w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm text-muted"
        />
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            disabled
            className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background opacity-50"
          >
            Send
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="mt-6 rounded-lg border border-border p-6" aria-labelledby={`${inputId}-heading`}>
      <p className="mb-4 rounded-md border border-border bg-surface px-3 py-2 text-xs text-muted">
        Preview mode — responses are placeholders
      </p>

      <h2 id={`${inputId}-heading`} className="sr-only">
        Chat
      </h2>

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto" role="log" aria-live="polite">
        {messages.length === 0 ? (
          <p className="text-sm text-muted">Ask a question about this PDF.</p>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      <label htmlFor={inputId} className="sr-only">
        Chat message
      </label>
      <textarea
        id={inputId}
        rows={3}
        value={draft}
        disabled={isSending}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask a question about this PDF…"
        className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-[var(--color-accent-cyan)] disabled:opacity-60"
      />
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          disabled={isSending || !draft.trim()}
          onClick={() => void send()}
          className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </section>
  );
}
