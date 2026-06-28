'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createConversation,
  deleteConversation,
  renameConversation,
} from '@/lib/api/conversations';

export function useCreateConversation(pdfId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => createConversation(pdfId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['conversations', pdfId] });
    },
  });
}

export function useRenameConversation(pdfId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      renameConversation(conversationId, title),
    onSuccess: (conversation) => {
      void qc.invalidateQueries({ queryKey: ['conversations', pdfId] });
      void qc.invalidateQueries({ queryKey: ['conversation', conversation.id] });
    },
  });
}

export function useDeleteConversation(pdfId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => deleteConversation(conversationId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['conversations', pdfId] });
    },
  });
}
