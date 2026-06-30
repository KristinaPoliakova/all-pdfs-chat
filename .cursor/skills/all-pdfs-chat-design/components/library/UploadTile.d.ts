import * as React from 'react';

export interface UploadTileProps {
  onClick?: () => void;
  /** Default "Drop a PDF". */
  label?: string;
  /** Default "or click to browse · up to 10 MB". */
  hint?: string;
  style?: React.CSSProperties;
}

export function UploadTile(props: UploadTileProps): JSX.Element;
