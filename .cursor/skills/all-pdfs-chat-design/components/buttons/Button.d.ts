import * as React from 'react';

/**
 * @startingPoint section="Buttons" subtitle="Primary / secondary / ghost action button" viewport="700x150"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style. Default "primary". */
  variant?: 'primary' | 'secondary' | 'ghost';
  /** Size. Default "md". */
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  /** Optional icon node rendered before the label. */
  leftIcon?: React.ReactNode;
  children?: React.ReactNode;
}

export function Button(props: ButtonProps): JSX.Element;
