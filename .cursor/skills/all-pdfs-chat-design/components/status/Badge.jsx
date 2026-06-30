import React from 'react';

/**
 * Small pill label. Use `tone` for semantic color.
 */
export function Badge({ tone = 'neutral', children, style = {} }) {
  const tones = {
    neutral: { color: 'var(--text-dim)', background: 'var(--surface-2)', border: '1px solid var(--border)' },
    accent:  { color: 'var(--accent)', background: 'var(--accent-soft)', border: '1px solid transparent' },
    success: { color: 'var(--success)', background: 'rgba(91,201,138,0.13)', border: '1px solid transparent' },
    danger:  { color: 'var(--danger)', background: 'rgba(240,96,122,0.13)', border: '1px solid transparent' },
  };
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--fs-meta)',
      fontWeight: 'var(--fw-semibold)',
      padding: '4px 10px',
      borderRadius: 'var(--r-pill)',
      ...tones[tone],
      ...style,
    }}>{children}</span>
  );
}
