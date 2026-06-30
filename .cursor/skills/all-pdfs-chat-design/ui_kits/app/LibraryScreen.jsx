import React from 'react';
import { Avatar } from '../../components/avatar/Avatar.jsx';
import { Button } from '../../components/buttons/Button.jsx';
import { PdfCard } from '../../components/library/PdfCard.jsx';
import { UploadTile } from '../../components/library/UploadTile.jsx';

/**
 * Library (home) — sticky bar + 3-col document grid. `onOpen(id)` opens chat.
 */
export function LibraryScreen({ pdfs, onOpen, onSignOut }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)', color: 'var(--text)' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, padding: '16px 32px', background: 'var(--bar-bg)', backdropFilter: 'var(--blur-bar)', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <Avatar brand size={30} />
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 'var(--fs-title)', letterSpacing: '-0.01em' }}>All PDFs Chat</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button>+ Upload</Button>
          <Avatar initials="" onClick={onSignOut} />
        </div>
      </div>

      <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto', padding: '34px 32px 80px' }}>
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 600, letterSpacing: '-0.01em' }}>Your Library</div>
          <div style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginTop: 4 }}>{pdfs.length} documents · click a document to open the conversation</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
          <UploadTile />
          {pdfs.map((p) => (
            <PdfCard key={p.id} name={p.name} pages={p.pages} status={p.status} chats={p.chats} onClick={() => onOpen(p.id)} />
          ))}
        </div>
      </div>
    </div>
  );
}
