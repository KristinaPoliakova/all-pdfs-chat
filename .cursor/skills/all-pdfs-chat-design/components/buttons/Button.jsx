import React from 'react';

/**
 * Canvas primary action button. Sentence-case labels, soft light-pink accent.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  leftIcon = null,
  children,
  style = {},
  ...rest
}) {
  const sizes = {
    sm: { padding: '8px 13px', fontSize: '13px' },
    md: { padding: '10px 16px', fontSize: 'var(--fs-base)' },
    lg: { padding: '13px 20px', fontSize: '14.5px' },
  };
  const variants = {
    primary: { background: 'var(--accent)', color: 'var(--accent-ink)', border: '1px solid transparent' },
    secondary: { background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)' },
    ghost: { background: 'transparent', color: 'var(--text-dim)', border: '1px solid transparent' },
  };
  return (
    <button
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        fontFamily: 'var(--font-sans)',
        fontWeight: 'var(--fw-bold)',
        lineHeight: 1,
        borderRadius: 'var(--r-lg)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background var(--dur-fast), opacity var(--dur-fast)',
        ...sizes[size],
        ...variants[variant],
        ...style,
      }}
      {...rest}
    >
      {leftIcon}
      {children}
    </button>
  );
}
