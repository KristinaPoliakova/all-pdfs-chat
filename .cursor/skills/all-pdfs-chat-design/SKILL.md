---
name: all-pdfs-chat-design
description: Use this skill to generate well-branded interfaces and assets for All PDFs Chat (the "Canvas" design system) — production code or throwaway prototypes/mocks. Contains design guidelines, color & type tokens, fonts, components, and an app UI kit.
user-invocable: true
---

Read `readme.md` in this skill, then explore the other files.

- **Foundations:** `styles.css` is the entry point — link it and everything inherits the Canvas tokens (colors, type, spacing, radius, effects). There is one theme: a soft pink "paper" surface with a soft light-pink accent.
- **Components:** `components/<group>/<Name>.jsx` (+ `.d.ts`, `.prompt.md`) — Button, IconButton, Input, Badge, StatusDot, CitationChip, Avatar, PdfCard, UploadTile, ChatBubble. They style via CSS custom properties, so they work anywhere `styles.css` is linked.
- **UI kit:** `ui_kits/app/` — interactive recreation of the three app screens (auth, library, slide-in chat). `index.html` is self-contained and is the visual reference for the redesign.

If creating visual artifacts (mocks, throwaway prototypes), copy assets out and produce static HTML files for the user to view. If working on production code, copy the tokens/components and follow `readme.md` to design as an expert in this brand.

If invoked with no other guidance, ask the user what they want to build, ask a few clarifying questions, and act as an expert designer who outputs HTML artifacts or production code as needed. Always follow the CONTENT FUNDAMENTALS (sentence case, plain calm voice, no emoji) and VISUAL FOUNDATIONS (one soft light-pink accent, document stripe texture, borders over shadows) in `readme.md`.
