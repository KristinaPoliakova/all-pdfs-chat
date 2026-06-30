Monospace chip citing the source page of an answer. Render a row of them under an assistant message.

```jsx
{message.citations.map((p) => <CitationChip key={p} page={p} />)}
```

Always mono font. Citations are central to the product — every assistant answer that has sources should show them.
