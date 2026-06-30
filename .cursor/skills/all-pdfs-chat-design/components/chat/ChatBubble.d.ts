import * as React from 'react';

/**
 * @startingPoint section="Chat" subtitle="User / assistant message bubble with citations" viewport="480x220"
 */
export interface ChatBubbleProps {
  /** Who sent it. Default "assistant". */
  role?: 'user' | 'assistant';
  /** Message body. */
  children?: React.ReactNode;
  /** Page numbers cited (assistant only). */
  citations?: number[];
}

export function ChatBubble(props: ChatBubbleProps): JSX.Element;
