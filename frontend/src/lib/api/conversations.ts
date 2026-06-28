import type {
  ChatAnswer,
  Conversation,
  ConversationMessage,
  ConversationMessagesResponse,
} from '@/types/conversation';
import { apiFetch } from './client';

export async function createConversation(pdfId: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/pdfs/${encodeURIComponent(pdfId)}/conversations`, {
    method: 'POST',
  });
}

export async function listConversations(pdfId: string): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/pdfs/${encodeURIComponent(pdfId)}/conversations`);
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/conversations/${encodeURIComponent(conversationId)}`);
}

export async function renameConversation(
  conversationId: string,
  title: string,
): Promise<Conversation> {
  return apiFetch<Conversation>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiFetch<void>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
  });
}

export async function getConversationMessages(
  conversationId: string,
): Promise<ConversationMessage[]> {
  const res = await apiFetch<ConversationMessagesResponse>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`,
  );
  return res.messages;
}

export async function sendConversationMessage(
  conversationId: string,
  message: string,
): Promise<ChatAnswer> {
  return apiFetch<ChatAnswer>(`/conversations/${encodeURIComponent(conversationId)}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
}
