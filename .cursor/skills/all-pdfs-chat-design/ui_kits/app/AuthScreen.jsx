import React from 'react';
import { Input } from '../../components/forms/Input.jsx';
import { Button } from '../../components/buttons/Button.jsx';
import { Avatar } from '../../components/avatar/Avatar.jsx';

/**
 * Auth screen — split brand / form card. Toggles login ↔ register.
 */
export function AuthScreen({ onSubmit }) {
  const [mode, setMode] = React.useState('login');
  const reg = mode === 'register';
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, fontFamily: 'var(--font-sans)', color: 'var(--text)' }}>
      <div style={{ width: 920, maxWidth: '100%', display: 'grid', gridTemplateColumns: '1fr 1fr', borderRadius: 'var(--r-3xl)', overflow: 'hidden', border: '1px solid var(--border)', boxShadow: 'var(--shadow-modal)' }}>
        <div style={{ position: 'relative', background: 'var(--surface)', padding: '44px 40px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 540, overflow: 'hidden' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'var(--stripe-brand)', opacity: 0.5 }} />
          <div style={{ position: 'absolute', width: 360, height: 360, borderRadius: '50%', background: 'var(--accent)', filter: 'blur(120px)', opacity: 0.28, top: -80, left: -60 }} />
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 11 }}>
            <Avatar brand size={34} />
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 17, letterSpacing: '-0.01em' }}>All PDFs Chat</span>
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1.18, fontWeight: 600, letterSpacing: '-0.02em' }}>Talk to your<br />documents.</div>
            <p style={{ margin: '16px 0 0', fontSize: '14.5px', lineHeight: 1.6, color: 'var(--text-dim)', maxWidth: 300 }}>Upload a PDF, let it parse, then ask anything — every answer cites the exact page it came from.</p>
          </div>
          <div style={{ position: 'relative', display: 'flex', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-mono)', color: 'var(--text-dim)' }}>
            <span style={{ border: '1px solid var(--border)', padding: '4px 10px', borderRadius: 'var(--r-pill)' }}>cited sources</span>
            <span style={{ border: '1px solid var(--border)', padding: '4px 10px', borderRadius: 'var(--r-pill)' }}>private</span>
          </div>
        </div>
        <div style={{ background: 'var(--bg)', padding: '48px 44px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>{reg ? 'Create your account' : 'Welcome back'}</div>
          <div style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginTop: 6 }}>{reg ? 'Start chatting with your PDFs in seconds.' : 'Sign in to your document library.'}</div>
          <div style={{ marginTop: 26 }}><Input label="Email" type="email" placeholder="you@company.com" /></div>
          <div style={{ marginTop: 16 }}><Input label="Password" type="password" placeholder="••••••••" hint={reg ? 'At least 8 characters' : undefined} /></div>
          <div style={{ marginTop: 24 }}>
            <Button size="lg" style={{ width: '100%' }} onClick={onSubmit}>{reg ? 'Create account' : 'Sign in'}</Button>
          </div>
          <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13, color: 'var(--text-dim)' }}>
            {reg ? 'Already have an account? ' : 'New here? '}
            <span onClick={() => setMode(reg ? 'login' : 'register')} style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}>{reg ? 'Sign in' : 'Create one'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
