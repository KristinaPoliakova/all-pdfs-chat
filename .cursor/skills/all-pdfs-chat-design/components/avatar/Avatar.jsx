import React from 'react';

/**
 * Round avatar. Renders the brand monogram or user initials.
 */
export function Avatar({ initials = 'A', size = 32, brand = false, style = {}, ...rest }) {
  return (
    <span
      style={{
        width: size,
        height: size,
        flex: 'none',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--r-full)',
        fontFamily: 'var(--font-display)',
        fontWeight: 'var(--fw-bold)',
        fontSize: Math.round(size * 0.42),
        background: brand ? 'var(--accent)' : 'var(--surface-2)',
        color: brand ? 'var(--accent-ink)' : 'var(--text-dim)',
        border: brand ? 'none' : '1px solid var(--border)',
        cursor: rest.onClick ? 'pointer' : 'default',
        ...style,
      }}
      {...rest}
    >{initials}</span>
  );
}
