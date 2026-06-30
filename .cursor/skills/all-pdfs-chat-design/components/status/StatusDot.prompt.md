Colored dot + label for a PDF's processing state, used in cards and lists.

```jsx
<StatusDot status="ready" label="Ready · 24 pp" />
<StatusDot status="parsing" />
```

`ready` = green dot; `parsing` = pulsing pink dot; `error` = red. Pass `label` to include page count / chats.
