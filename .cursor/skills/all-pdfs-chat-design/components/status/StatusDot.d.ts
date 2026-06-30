import * as React from 'react';

export interface StatusDotProps {
  /** Processing state. Default "ready". */
  status?: 'ready' | 'parsing' | 'error';
  /** Override the default label text. */
  label?: string;
  style?: React.CSSProperties;
}

export function StatusDot(props: StatusDotProps): JSX.Element;
