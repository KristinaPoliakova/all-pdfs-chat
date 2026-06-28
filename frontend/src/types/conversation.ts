export interface Conversation {
  id: string;
  pdf_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  citations: number[];
}

export interface ConversationMessagesResponse {
  messages: ConversationMessage[];
}

export interface ChatAnswer {
  answer: string;
  citations: number[];
}
