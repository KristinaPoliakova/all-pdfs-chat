import * as React from 'react';

export interface CitationChipProps {
  /** Page number; rendered as "p. N". */
  page?: number;
  /** Custom content (overrides page). */
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export function CitationChip(props: CitationChipProps): JSX.Element;
