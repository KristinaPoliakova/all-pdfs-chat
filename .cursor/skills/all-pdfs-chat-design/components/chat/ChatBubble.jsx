import React from 'react';
import { CitationChip } from '../status/CitationChip.jsx';

/**
 * Chat message bubble. User bubbles are accent-filled and right-aligned;
 * assistant bubbles are surface-2, left-aligned, with citation chips.
 */
export function ChatBubble({ role = 'assistant', children, citations = [] }) {
  const isUser = role === 'user';
  if (isUser) {
    return (
      <div style={{
        alignSelf: 'flex-end',
        maxWidth: '84%',
        background: 'var(--accent)',
        color: 'var(--accent-ink)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--fs-sm)',
        lineHeight: 1.5,
        padding: '10px 14px',
        borderRadius: 'var(--bubble-user)',
      }}>{children}</div>
    );
  }
  return (
    <div style={{ alignSelf: 'flex-start', maxWidth: '90%' }}>
      <div style={{
        background: 'var(--surface-2)',
        color: 'var(--text)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--fs-sm)',
        lineHeight: 'var(--lh-normal)',
        padding: '12px 15px',
        borderRadius: 'var(--bubble-bot)',
      }}>{children}</div>
      {citations.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', marginTop: '7px', flexWrap: 'wrap' }}>
          {citations.map((p) => <CitationChip key={p} page={p} />)}
        </div>
      )}
    </div>
  );
}
