# UI Kit — All PDFs Chat (Canvas)

Full-screen recreations of the app's three surfaces, composed from the Canvas component primitives in `../../components/`.

## Files
- **`index.html`** — the rendered, **interactive** demo (open it). Flow: auth → sign in → library → click a card → chat slides in → type & send → close → sign out → auth. Single soft-pink theme. Self-contained (React + Babel via CDN, links `../../styles.css`). This is the `@dsCard` preview and the App starting point.
- **`AuthScreen.jsx`** — split brand/form auth card; toggles login ↔ register.
- **`LibraryScreen.jsx`** — sticky top bar + 3-col document grid (`UploadTile` + `PdfCard`s).
- **`ChatPanelView.jsx`** — fixed-right slide-in conversation panel over a scrim (`ChatBubble` + composer).

The `.jsx` files are the production-shaped composition (they import the real primitives); `index.html` inlines the same screens so it renders without a build step.

## Mapping to the real app
These mirror the redesign of the existing Next.js app. Map them onto the real source under `frontend/src/{app,components,hooks,lib}`: the library and slide-in chat wire to the existing `/pdfs/[id]` route and its data hooks. The kit is cosmetic; data/messages are mocked.
