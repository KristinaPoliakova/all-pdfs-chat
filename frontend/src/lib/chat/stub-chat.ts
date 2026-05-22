export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export async function sendChatMessage(
  pdfId: string,
  message: string,
): Promise<ChatMessage> {
  void pdfId;
  void message;
  await new Promise((r) => setTimeout(r, 400));
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content:
      'Chat API is not connected yet. Your PDF is parsed and ready — answers will appear here once the backend ships.',
    createdAt: new Date().toISOString(),
  };
}
