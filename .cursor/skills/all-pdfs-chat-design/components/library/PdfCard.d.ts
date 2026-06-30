import * as React from 'react';

/**
 * @startingPoint section="Library" subtitle="Document card — thumbnail, name, status" viewport="380x236"
 */
export interface PdfCardProps {
  /** Filename, e.g. "Q3 Financial Report.pdf". */
  name: string;
  /** Page count. */
  pages?: number;
  /** Processing state. Default "ready". */
  status?: 'ready' | 'parsing' | 'error';
  /** Number of conversations on this PDF. */
  chats?: number;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export function PdfCard(props: PdfCardProps): JSX.Element;
