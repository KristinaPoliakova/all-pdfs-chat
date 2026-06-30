import React from 'react';
import { StatusDot } from '../status/StatusDot.jsx';

/**
 * Library document card — thumbnail + filename + status. Click to open chat.
 */
export function PdfCard({ name, pages, status = 'ready', chats = 0, onClick, style = {} }) {
  const [hover, setHover] = React.useState(false);
  const parsing = status === 'parsing';
  const meta = parsing
    ? 'Processing'
    : `Ready · ${pages} pp${chats ? ` · ${chats} chat${chats > 1 ? 's' : ''}` : ''}`;
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        border: `1px solid ${hover ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--r-2xl)',
        overflow: 'hidden',
        background: 'var(--surface)',
        cursor: 'pointer',
        transform: hover ? 'translateY(-2px)' : 'none',
        transition: 'border-color var(--dur-fast), transform var(--dur-fast)',
        ...style,
      }}
    >
      <div style={{
        position: 'relative',
        height: '128px',
        background: 'var(--stripe), var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {parsing && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--fs-mono)',
            color: 'var(--accent)',
            background: 'var(--bg)',
            padding: '5px 11px',
            borderRadius: 'var(--r-pill)',
            border: '1px solid var(--accent)',
            animation: 'cv-pulse 1.6s ease-in-out infinite',
          }}>parsing…</span>
        )}
      </div>
      <div style={{ padding: '15px 16px' }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'var(--fs-base)',
          fontWeight: 'var(--fw-semibold)',
          color: 'var(--text)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>{name}</div>
        <div style={{ marginTop: '8px' }}>
          <StatusDot status={status} label={meta} />
        </div>
      </div>
    </div>
  );
}
