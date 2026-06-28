'use client';

import { useQuery } from '@tanstack/react-query';
import {
  getConversation,
  getConversationMessages,
  listConversations,
} from '@/lib/api/conversations';

export function useConversations(pdfId: string) {
  return useQuery({
    queryKey: ['conversations', pdfId],
    queryFn: () => listConversations(pdfId),
    enabled: Boolean(pdfId),
  });
}

export function useConversation(conversationId: string) {
  return useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => getConversation(conversationId),
    enabled: Boolean(conversationId),
  });
}

export function useConversationMessages(conversationId: string) {
  return useQuery({
    queryKey: ['conversation-messages', conversationId],
    queryFn: () => getConversationMessages(conversationId),
    enabled: Boolean(conversationId),
  });
}
