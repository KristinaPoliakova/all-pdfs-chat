import * as React from 'react';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Default "accent". */
  variant?: 'accent' | 'subtle' | 'ghost';
  /** Default "square". */
  shape?: 'square' | 'round';
  /** Pixel size of the square. Default 34. */
  size?: number;
  /** Accessible label (required — the button is icon-only). */
  label: string;
  children?: React.ReactNode;
}

export function IconButton(props: IconButtonProps): JSX.Element;
