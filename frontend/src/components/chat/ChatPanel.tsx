'use client';

import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { sendConversationMessage } from '@/lib/api/conversations';
import { ApiError, chatErrorMessage } from '@/lib/api/errors';
import { useConversationMessages } from '@/hooks/useConversations';
import type { ConversationMessage } from '@/types/conversation';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  citations?: number[];
}

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
  const hasCitations = !isUser && message.citations !== undefined && message.citations.length > 0;
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
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
      {hasCitations ? (
        <p className="mt-1 px-1 text-xs text-muted">
          Sources: p. {message.citations!.join(', ')}
        </p>
      ) : null}
    </div>
  );
}

function toUiMessage(message: ConversationMessage): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: message.role,
    content: message.content,
    createdAt: new Date().toISOString(),
    citations: message.citations,
  };
}

export function ChatPanel({
  pdfId,
  conversationId,
  enabled,
}: {
  pdfId: string;
  conversationId: string;
  enabled: boolean;
}) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const { data: history, isPending: historyPending } = useConversationMessages(conversationId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hydratedFor = useRef<string | null>(null);

  // Reseed local messages from server history when the conversation changes
  // or its history first loads. Local state then owns in-session turns.
  useEffect(() => {
    if (history && hydratedFor.current !== conversationId) {
      hydratedFor.current = conversationId;
      setMessages(history.map(toUiMessage));
      setError(null);
    }
  }, [history, conversationId]);

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
    setError(null);
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    // Lock hydration: once the user sends, local state owns the transcript so a
    // late-arriving history fetch can't overwrite in-session turns.
    hydratedFor.current = conversationId;

    try {
      const reply = await sendConversationMessage(conversationId, text);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: reply.answer,
          createdAt: new Date().toISOString(),
          citations: reply.citations,
        },
      ]);
      // Title may be set on the first turn; updated_at changes ordering.
      void queryClient.invalidateQueries({ queryKey: ['conversations', pdfId] });
      void queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
    } catch (err) {
      setError(
        err instanceof ApiError ? chatErrorMessage(err) : 'Something went wrong. Please try again.',
      );
    } finally {
      setIsSending(false);
    }
  }, [draft, enabled, isSending, conversationId, pdfId, queryClient]);

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
      <h2 id={`${inputId}-heading`} className="sr-only">
        Chat
      </h2>

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto" role="log" aria-live="polite">
        {historyPending && messages.length === 0 ? (
          <p className="text-sm text-muted">Loading conversation…</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-muted">Ask a question about this PDF.</p>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      {error ? (
        <p
          role="alert"
          className="mb-3 rounded-md border border-[var(--color-accent-red,#ef4444)] bg-surface px-3 py-2 text-sm text-foreground"
        >
          {error}
        </p>
      ) : null}

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
