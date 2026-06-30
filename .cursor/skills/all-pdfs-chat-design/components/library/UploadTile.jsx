import React from 'react';

/**
 * Dashed upload tile — first cell of the library grid.
 */
export function UploadTile({ onClick, label = 'Drop a PDF', hint = 'or click to browse · up to 10 MB', style = {} }) {
  return (
    <div
      onClick={onClick}
      style={{
        border: '1.5px dashed var(--border)',
        borderRadius: 'var(--r-2xl)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px',
        minHeight: '236px',
        color: 'var(--text-dim)',
        cursor: 'pointer',
        ...style,
      }}
    >
      <div style={{
        width: '46px', height: '46px',
        borderRadius: 'var(--r-xl)',
        background: 'var(--surface-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '24px', color: 'var(--accent)',
      }}>+</div>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 'var(--fw-semibold)', color: 'var(--text)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--fs-meta)' }}>{hint}</span>
    </div>
  );
}
