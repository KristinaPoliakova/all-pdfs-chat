import * as React from 'react';

export interface AvatarProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** 1–2 letters. Default "A". */
  initials?: string;
  /** Pixel diameter. Default 32. */
  size?: number;
  /** Brand monogram styling (accent fill) instead of neutral. */
  brand?: boolean;
}

export function Avatar(props: AvatarProps): JSX.Element;
