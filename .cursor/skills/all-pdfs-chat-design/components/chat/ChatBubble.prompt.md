A single chat turn. Stack these in a flex column with 16px gaps inside the chat panel.

```jsx
<ChatBubble role="user">What was Q3 revenue?</ChatBubble>
<ChatBubble role="assistant" citations={[12, 13]}>
  Q3 revenue was $48.2M, up 14% from Q2.
</ChatBubble>
```

User = accent fill, right; assistant = surface-2, left, with `CitationChip`s underneath. The tucked bubble corner points toward the sender.
