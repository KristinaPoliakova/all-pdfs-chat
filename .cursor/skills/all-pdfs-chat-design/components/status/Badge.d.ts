import * as React from 'react';

export interface BadgeProps {
  /** Semantic color. Default "neutral". */
  tone?: 'neutral' | 'accent' | 'success' | 'danger';
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export function Badge(props: BadgeProps): JSX.Element;
