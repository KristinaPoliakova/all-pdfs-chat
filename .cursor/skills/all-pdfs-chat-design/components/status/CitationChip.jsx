import React from 'react';

/**
 * Mono page-citation chip. Renders the source page for an answer.
 */
export function CitationChip({ page, children, style = {} }) {
  const label = children ?? (typeof page === 'number' ? `p. ${page}` : page);
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--fs-mono)',
      color: 'var(--text-dim)',
      background: 'var(--bg)',
      border: '1px solid var(--border)',
      padding: '3px 9px',
      borderRadius: 'var(--r-pill)',
      ...style,
    }}>{label}</span>
  );
}
