Dashed drop target for uploading a PDF. Sits as the first cell of the library grid so "add" is always in the same place.

```jsx
<UploadTile onClick={pickFile} />
```

Wire `onClick` / drag handlers to the existing upload mutation. Swap the "+" glyph for a Lucide `upload` icon in production.
