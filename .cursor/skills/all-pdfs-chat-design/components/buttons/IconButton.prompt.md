Icon-only button for compact actions — the chat send (↑), panel close (✕), toolbar controls. Always pass an accessible `label`.

```jsx
<IconButton label="Send" onClick={send}>↑</IconButton>
<IconButton variant="subtle" label="Close" onClick={close}>✕</IconButton>
```

Variants: `accent` (pink, default), `subtle` (surface-2), `ghost`. `shape`: `square` (default) or `round`. Replace the text glyph child with a real icon (Lucide) in production.
