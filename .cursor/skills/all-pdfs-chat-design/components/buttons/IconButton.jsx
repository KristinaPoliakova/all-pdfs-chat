import React from 'react';

/**
 * Square/round icon button — toolbar actions, send, close.
 */
export function IconButton({
  variant = 'accent',
  shape = 'square',
  size = 34,
  label,
  children,
  style = {},
  ...rest
}) {
  const variants = {
    accent: { background: 'var(--accent)', color: 'var(--accent-ink)' },
    subtle: { background: 'var(--surface-2)', color: 'var(--text-dim)' },
    ghost: { background: 'transparent', color: 'var(--text-dim)' },
  };
  return (
    <button
      aria-label={label}
      style={{
        width: size,
        height: size,
        flex: 'none',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: 'none',
        borderRadius: shape === 'round' ? 'var(--r-full)' : 'var(--r-md)',
        fontSize: Math.round(size * 0.47),
        fontWeight: 'var(--fw-bold)',
        cursor: 'pointer',
        transition: 'background var(--dur-fast)',
        ...variants[variant],
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
