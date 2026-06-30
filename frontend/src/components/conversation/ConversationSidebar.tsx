'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';
import { ApiError, manageErrorMessage } from '@/lib/api/errors';
import { useConversations } from '@/hooks/useConversations';
import { useCreateConversation } from '@/hooks/useConversationMutations';
import { ConversationListItem } from './ConversationListItem';

export function ConversationSidebar({
  pdfId,
  activeId,
  parsed,
}: {
  pdfId: string;
  activeId: string | null;
  parsed: boolean;
}) {
  const router = useRouter();
  const { data: conversations, isPending } = useConversations(pdfId);
  const create = useCreateConversation(pdfId);
  const [createError, setCreateError] = useState<string | null>(null);

  return (
    <div className="border-b border-[var(--border)] px-[22px] py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-[var(--text-dim)]">
          Conversations
        </span>
        <button
          type="button"
          disabled={!parsed || create.isPending}
          onClick={() => {
            setCreateError(null);
            create.mutate(undefined, {
              onSuccess: (conversation) =>
                router.push(`/pdfs/${pdfId}/conversations/${conversation.id}`),
              onError: (err) =>
                setCreateError(
                  err instanceof ApiError
                    ? manageErrorMessage(err)
                    : 'Could not start a conversation.',
                ),
            });
          }}
          className="flex cursor-pointer items-center gap-[5px] rounded-[var(--r-sm)] border border-[var(--border)] px-[10px] py-[5px] text-[12px] font-semibold text-[var(--accent)] transition-colors hover:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus className="h-[14px] w-[14px]" strokeWidth={1.75} aria-hidden />
          New conversation
        </button>
      </div>
      {createError ? (
        <p role="alert" className="mt-2 text-[11.5px] text-[var(--danger)]">
          {createError}
        </p>
      ) : null}
      {!parsed ? (
        <p className="mt-2 text-[11.5px] text-[var(--text-dim)]">Available once parsing completes.</p>
      ) : null}

      <ul className="mt-2 max-h-[120px] space-y-1 overflow-y-auto">
        {isPending ? (
          <li className="px-1 py-1 text-[12px] text-[var(--text-dim)]">Loading…</li>
        ) : !conversations || conversations.length === 0 ? (
          <li className="px-1 py-1 text-[12px] text-[var(--text-dim)]">No conversations yet.</li>
        ) : (
          conversations.map((conversation) => (
            <ConversationListItem
              key={conversation.id}
              conversation={conversation}
              pdfId={pdfId}
              active={conversation.id === activeId}
            />
          ))
        )}
      </ul>
    </div>
  );
}
