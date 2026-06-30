import React from 'react';

/**
 * Labeled text input — Canvas form field.
 */
export function Input({ label, hint, type = 'text', style = {}, ...rest }) {
  return (
    <label style={{ display: 'block' }}>
      {label && (
        <span style={{
          display: 'block',
          fontSize: '12.5px',
          fontWeight: 'var(--fw-semibold)',
          color: 'var(--text)',
          marginBottom: '7px',
        }}>{label}</span>
      )}
      <input
        type={type}
        style={{
          width: '100%',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)',
          padding: '12px 14px',
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--fs-base)',
          color: 'var(--text)',
          outline: 'none',
          ...style,
        }}
        onFocus={(e) => { e.target.style.boxShadow = '0 0 0 2px var(--focus-ring)'; e.target.style.borderColor = 'var(--accent)'; }}
        onBlur={(e) => { e.target.style.boxShadow = 'none'; e.target.style.borderColor = 'var(--border)'; }}
        {...rest}
      />
      {hint && (
        <span style={{ display: 'block', fontSize: 'var(--fs-meta)', color: 'var(--text-dim)', marginTop: '6px' }}>{hint}</span>
      )}
    </label>
  );
}
