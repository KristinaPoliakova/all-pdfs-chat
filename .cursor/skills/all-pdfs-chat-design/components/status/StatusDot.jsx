import React from 'react';

/**
 * Status dot + label. "ready" is green; "parsing" pulses accent.
 */
export function StatusDot({ status = 'ready', label, style = {} }) {
  const map = {
    ready:   { color: 'var(--success)', text: label ?? 'Ready', pulse: false },
    parsing: { color: 'var(--accent)',  text: label ?? 'Parsing…', pulse: true },
    error:   { color: 'var(--danger)',  text: label ?? 'Failed', pulse: false },
  };
  const s = map[status] || map.ready;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', ...style }}>
      <span style={{
        width: '6px', height: '6px', borderRadius: 'var(--r-full)',
        background: s.color, flex: 'none',
        animation: s.pulse ? 'cv-pulse 1.6s ease-in-out infinite' : 'none',
      }} />
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--fs-meta)', color: 'var(--text-dim)' }}>{s.text}</span>
    </span>
  );
}
