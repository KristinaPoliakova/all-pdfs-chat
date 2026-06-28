'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { ApiError, manageErrorMessage } from '@/lib/api/errors';
import {
  useDeleteConversation,
  useRenameConversation,
} from '@/hooks/useConversationMutations';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { InlineEdit } from '@/components/ui/InlineEdit';
import type { Conversation } from '@/types/conversation';

export function ConversationListItem({
  conversation,
  pdfId,
  active,
}: {
  conversation: Conversation;
  pdfId: string;
  active: boolean;
}) {
  const router = useRouter();
  const rename = useRenameConversation(pdfId);
  const remove = useDeleteConversation(pdfId);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const label = conversation.title ?? 'New conversation';

  if (editing) {
    return (
      <li className="px-2 py-1">
        <InlineEdit
          initialValue={conversation.title ?? ''}
          maxLength={200}
          onSubmit={(title) => {
            rename.mutate(
              { conversationId: conversation.id, title },
              {
                onSuccess: () => setEditing(false),
                onError: (err) =>
                  setError(err instanceof ApiError ? manageErrorMessage(err) : 'Rename failed.'),
              },
            );
          }}
          onCancel={() => setEditing(false)}
        />
        {error ? (
          <p role="alert" className="mt-1 text-xs text-danger">
            {error}
          </p>
        ) : null}
      </li>
    );
  }

  return (
    <li
      className={[
        'group rounded-md px-2 py-1.5 text-sm',
        active ? 'bg-surface text-foreground' : 'text-muted hover:bg-surface/60',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-2">
        <Link href={`/pdfs/${pdfId}/conversations/${conversation.id}`} className="flex-1 truncate">
          {label}
        </Link>
        <span className="flex shrink-0 gap-1 opacity-0 group-hover:opacity-100">
          <button
            type="button"
            aria-label={`Rename ${label}`}
            onClick={() => {
              setError(null);
              setEditing(true);
            }}
            className="rounded px-1 text-xs text-muted hover:text-foreground"
          >
            Rename
          </button>
          <button
            type="button"
            aria-label={`Delete ${label}`}
            onClick={() => {
              setError(null);
              setConfirming(true);
            }}
            className="rounded px-1 text-xs text-muted hover:text-danger"
          >
            Delete
          </button>
        </span>
      </div>
      {error ? (
        <p role="alert" className="mt-1 text-xs text-danger">
          {error}
        </p>
      ) : null}
      {confirming ? (
        <ConfirmDialog
          title="Delete conversation"
          message={`Delete "${label}"? This cannot be undone.`}
          confirmLabel="Delete"
          onCancel={() => setConfirming(false)}
          onConfirm={() => {
            remove.mutate(conversation.id, {
              onSuccess: () => {
                setConfirming(false);
                if (active) router.push(`/pdfs/${pdfId}`);
              },
              onError: (err) => {
                setConfirming(false);
                setError(err instanceof ApiError ? manageErrorMessage(err) : 'Delete failed.');
              },
            });
          }}
        />
      ) : null}
    </li>
  );
}
