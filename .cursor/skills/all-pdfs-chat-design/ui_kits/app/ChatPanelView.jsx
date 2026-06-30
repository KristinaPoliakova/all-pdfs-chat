import React from 'react';
import { IconButton } from '../../components/buttons/IconButton.jsx';
import { ChatBubble } from '../../components/chat/ChatBubble.jsx';

/**
 * Slide-in conversation panel. Render over the library behind a scrim.
 */
export function ChatPanelView({ pdf, messages, draft, onDraft, onSend, onClose }) {
  if (!pdf) return null;
  return (
    <React.Fragment>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 40, background: 'var(--scrim)', backdropFilter: 'var(--blur-scrim)', animation: 'cv-fade-in .18s ease' }} />
      <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 50, width: 'var(--panel-w)', maxWidth: '94vw', background: 'var(--surface)', borderLeft: '1px solid var(--border)', boxShadow: 'var(--shadow-panel)', display: 'flex', flexDirection: 'column', animation: 'cv-slide-in .22s var(--ease-out)', fontFamily: 'var(--font-sans)', color: 'var(--text)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '18px 22px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{pdf.name}</div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-dim)', marginTop: 2 }}>{pdf.pages} pages · {pdf.chats || 0} conversation{pdf.chats === 1 ? '' : 's'}</div>
          </div>
          <IconButton variant="subtle" label="Close conversation" size={30} onClick={onClose}>✕</IconButton>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 22, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {messages.map((m, i) => (
            <ChatBubble key={i} role={m.role} citations={m.cites}>{m.text}</ChatBubble>
          ))}
        </div>

        <div style={{ padding: '14px 22px 20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 9, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '8px 8px 8px 15px' }}>
            <textarea
              rows={1}
              value={draft}
              onChange={(e) => onDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); } }}
              placeholder="Ask about this PDF…"
              style={{ flex: 1, resize: 'none', border: 'none', background: 'transparent', outline: 'none', fontSize: 'var(--fs-sm)', lineHeight: 1.5, color: 'var(--text)', padding: '5px 0', maxHeight: 90 }}
            />
            <IconButton label="Send" onClick={onSend}>↑</IconButton>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}
