Primary call-to-action button — use for the main action in a view (Upload, Send, Sign in). Sentence-case labels only.

```jsx
<Button onClick={save}>+ Upload</Button>
<Button variant="secondary" size="sm">Rename</Button>
<Button variant="ghost" size="sm">Cancel</Button>
```

Variants: `primary` (pink fill with dark ink, default), `secondary` (surface-2 fill + border), `ghost` (text-only). Sizes: `sm` / `md` / `lg`. Pass `leftIcon` for an icon before the label. One primary button per view.
