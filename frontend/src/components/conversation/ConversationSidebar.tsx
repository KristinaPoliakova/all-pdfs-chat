'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
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
    <aside className="w-60 shrink-0 border-r border-border pr-4">
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
                err instanceof ApiError ? manageErrorMessage(err) : 'Could not start a conversation.',
              ),
          });
        }}
        className="w-full rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        + New conversation
      </button>
      {createError ? (
        <p role="alert" className="mt-2 text-xs text-danger">
          {createError}
        </p>
      ) : null}
      {!parsed ? (
        <p className="mt-2 text-xs text-muted">Available once parsing completes.</p>
      ) : null}

      <ul className="mt-4 space-y-1">
        {isPending ? (
          <li className="px-2 py-1 text-sm text-muted">Loading…</li>
        ) : !conversations || conversations.length === 0 ? (
          <li className="px-2 py-1 text-sm text-muted">No conversations yet.</li>
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
    </aside>
  );
}
