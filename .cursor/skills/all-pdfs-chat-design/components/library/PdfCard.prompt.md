The core library tile — one per uploaded PDF. Diagonal-stripe thumbnail (swap for a real first-page render when available), filename, and status. Clicking opens the chat panel.

```jsx
<PdfCard name="Q3 Financial Report.pdf" pages={24} chats={2} onClick={() => open(id)} />
<PdfCard name="Transformer Scaling.pdf" status="parsing" />
```

Lifts + accent border on hover. Lives in a 3-col grid with 18px gaps.
