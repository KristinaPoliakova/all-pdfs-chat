import * as React from 'react';

/**
 * @startingPoint section="Forms" subtitle="Labeled text input with focus ring" viewport="700x150"
 */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Field label rendered above the input. */
  label?: string;
  /** Helper text rendered below (e.g. "At least 8 characters"). */
  hint?: string;
  type?: string;
}

export function Input(props: InputProps): JSX.Element;
