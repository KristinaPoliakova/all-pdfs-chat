'use client';

import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { ArrowUp } from 'lucide-react';
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

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="max-w-[84%] self-end rounded-[var(--bubble-user)] bg-[var(--accent)] px-[14px] py-[10px] text-[var(--fs-sm)] leading-[1.5] text-[var(--accent-ink)]">
        {message.content}
      </div>
    );
  }

  const citations = message.citations ?? [];

  return (
    <div className="max-w-[90%] self-start">
      <div className="rounded-[var(--bubble-bot)] bg-[var(--surface-2)] px-[15px] py-3 text-[var(--fs-sm)] leading-[var(--lh-normal)] text-[var(--text)]">
        {message.content}
      </div>
      {citations.length > 0 ? (
        <div className="mt-[7px] flex flex-wrap gap-[6px]">
          {citations.map((page, index) => (
            <span
              key={`${page}-${index}`}
              className="font-mono rounded-[var(--r-pill)] border border-[var(--border)] bg-[var(--bg)] px-[9px] py-[3px] text-[var(--fs-mono)] text-[var(--text-dim)]"
            >
              p. {page}
            </span>
          ))}
        </div>
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

function Composer({
  inputId,
  draft,
  disabled,
  placeholder,
  onChange,
  onKeyDown,
  onSend,
  canSend,
}: {
  inputId: string;
  draft: string;
  disabled: boolean;
  placeholder: string;
  onChange?: (value: string) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend?: () => void;
  canSend: boolean;
}) {
  return (
    <div className="border-t border-[var(--border)] px-[22px] pb-5 pt-[14px]">
      <label htmlFor={inputId} className="sr-only">
        Chat message
      </label>
      <div className="flex items-end gap-[9px] rounded-[var(--r-xl)] border border-[var(--border)] bg-[var(--bg)] py-2 pl-[15px] pr-2">
        <textarea
          id={inputId}
          rows={1}
          value={draft}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={onKeyDown}
          className="max-h-[90px] flex-1 resize-none border-none bg-transparent py-[5px] text-[13.5px] leading-[1.5] text-[var(--text)] outline-none placeholder:text-[var(--text-dim)] disabled:opacity-60"
        />
        <button
          type="button"
          aria-label="Send"
          disabled={disabled || !canSend}
          onClick={onSend}
          className="flex h-[34px] w-[34px] shrink-0 cursor-pointer items-center justify-center rounded-[var(--r-md)] bg-[var(--accent)] text-[var(--accent-ink)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ArrowUp className="h-4 w-4" strokeWidth={1.75} aria-hidden />
        </button>
      </div>
    </div>
  );
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
  const scrollRef = useRef<HTMLDivElement>(null);

  // Reseed local messages from server history when the conversation changes
  // or its history first loads. Local state then owns in-session turns.
  useEffect(() => {
    if (history && hydratedFor.current !== conversationId) {
      hydratedFor.current = conversationId;
      setMessages(history.map(toUiMessage));
      setError(null);
    }
  }, [history, conversationId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && typeof el.scrollTo === 'function') {
      el.scrollTo({ top: el.scrollHeight });
    }
  }, [messages]);

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
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-1 items-center justify-center p-6 text-center">
          <p className="text-[13px] text-[var(--text-dim)]">Chat unlocks when parsing completes</p>
        </div>
        <Composer
          inputId={inputId}
          draft=""
          disabled
          placeholder="Ask about this PDF…"
          canSend={false}
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-[22px]"
      >
        {historyPending && messages.length === 0 ? (
          <p className="text-[13px] text-[var(--text-dim)]">Loading conversation…</p>
        ) : messages.length === 0 ? (
          <p className="text-[13px] text-[var(--text-dim)]">Ask a question about this PDF.</p>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      {error ? (
        <p
          role="alert"
          className="mx-[22px] mb-2 rounded-[10px] border border-[var(--danger)]/40 bg-[var(--danger)]/10 px-3 py-2 text-[13px] text-[var(--danger)]"
        >
          {error}
        </p>
      ) : null}

      <Composer
        inputId={inputId}
        draft={draft}
        disabled={isSending}
        placeholder="Ask about this PDF…"
        onChange={setDraft}
        onKeyDown={onKeyDown}
        onSend={() => void send()}
        canSend={Boolean(draft.trim())}
      />
    </div>
  );
}
