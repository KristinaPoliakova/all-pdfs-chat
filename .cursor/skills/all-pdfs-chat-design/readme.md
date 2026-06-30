# Canvas — All PDFs Chat Design System

**Canvas** is the visual + interaction language for **All PDFs Chat**, a web app where you upload a PDF, wait for it to parse, then ask questions and get answers that cite the exact page they came from.

This system encodes the "Canvas" redesign direction: a **visual document library** (card grid) with a **slide-in conversation panel**, in a refined, premium single-theme aesthetic — a soft pink "paper" surface with a soft light-pink signature. Use it to build new app screens and marketing pages that all feel like one product.

## Sources
- **Codebase (ground truth for behavior/data):** local folder `all-pdfs-chat/` — Next.js (App Router) + React + TypeScript + Tailwind v4 + TanStack Query frontend; FastAPI backend. Key UI under `frontend/src/{app,components,hooks,lib}`.
- **Visual direction (ground truth for this redesign):** `ui_kits/app/index.html` — a self-contained, interactive recreation of the three screens (auth, library, slide-in chat).
- The *old* app shipped with Inter + a cyan→purple gradient. **Canvas replaces that** — do not carry the old tokens forward.

---

## CONTENT FUNDAMENTALS
How copy is written in All PDFs Chat:

- **Voice:** plain, calm, and direct. Short sentences. No marketing fluff inside the product; a little warmth in onboarding/auth.
- **Person:** address the user as **you** ("Your Library", "Ask about this PDF"). The product refers to itself in the first person sparingly ("I'll cite the exact pages").
- **Casing:** **Sentence case** everywhere — buttons, titles, labels ("Create account", "New conversation", "Drop a PDF"). Never Title Case or ALL CAPS for UI copy. The one exception is tiny mono labels rendered lowercase ("parsing…").
- **Tone examples:**
  - Empty/hint: "Ask a question about this PDF." · "No PDFs yet — upload one above."
  - Action: "Sign in" · "Create account" · "+ Upload" · "Send"
  - Status: "Ready · 24 pp" · "Parsing…" · "Chat unlocks when parsing completes"
  - Value prop (auth): "Talk to your documents." / "Upload a PDF, let it parse, then ask anything — every answer cites the exact page it came from."
- **Numbers & units:** pages abbreviate to "pp" ("24 pp"); citations read "p. 12"; money is plain ("$48.2M"). Mono font for anything numeric-technical (page refs, key caps).
- **Punctuation:** ellipsis "…" (real glyph) for in-progress states; em dash "—" for asides. No exclamation marks in-product.
- **Emoji:** none. Not part of the brand.

---

## VISUAL FOUNDATIONS

**Overall vibe:** premium, focused, document-forward. A single soft-pink theme with one confident soft light-pink accent; quiet neutrals; generous breathing room around a tight, legible core. It should feel like a calm pro tool, not a flashy consumer app.

- **Color:** soft pink-tinted papers (`--paper-200/100/50`, app surfaces) under near-black warm text. **One** brand accent — soft light pink (`#ff9ec7`) — used for primary actions, links, active states, and the brand mark. Accent fills carry dark ink (`--accent-ink` `#3a0a1e`) so labels stay legible. Status green (`#5bc98a`) for "ready" is the only other hue. Avoid introducing new accent colors; if you need emphasis, use weight, the accent, or `--accent-soft` fills.
- **Type:** **Space Grotesk** for display/headings and brand wordmark (600/700, tight letter-spacing −0.01 to −0.02em); **Plus Jakarta Sans** for body and UI; **IBM Plex Mono** for metadata, page citations, key caps, and the "parsing…" pill. Headlines are set tight (line-height ~1.18); body relaxed (~1.58).
- **Backgrounds:** flat color, never photographic. The signature texture is a **diagonal stripe** (`--stripe`, 135° repeating gradient) standing in for a document page — used on PDF card thumbnails and the auth brand panel. The auth panel also carries one soft, blurred accent **glow blob** (large radius, `blur(120px)`, low opacity) — used sparingly, never more than one per view.
- **Cards:** flat `--surface` fill, **1px `--border`**, radius **16px**, no heavy drop shadow at rest. Elevation comes from borders and translucency, not big shadows. On hover, a card gets an **accent border** + a **2px lift** (`translateY(-2px)`) over `--dur-fast`.
- **Borders & dividers:** hairline `--border` (ink at ~10%). Borders do most of the structural work.
- **Shadows:** restrained and reserved for true overlays — the **slide-in panel** (`--shadow-panel`) and the **auth card** (`--shadow-modal`). Resting surfaces use borders, not shadows.
- **Transparency & blur:** sticky top bar and scrim use translucent fills + `backdrop-filter` blur (`--blur-bar` 14px on bars, `--blur-scrim` 2px on the scrim). Use blur only for layering (bars over content, scrim over the app) — never decoratively.
- **Radii:** chips/pills 20px; cards/tiles 16px; auth card 22px; inputs & primary buttons 10–11px; chat composer 14px; avatars/dots fully round. Chat bubbles tuck one corner toward the sender (`--bubble-user` / `--bubble-bot`).
- **Animation:** purposeful and quick. Panel slides in from the right (`--dur-base` 0.22s, `--ease-out`); scrim fades (0.18s); cards transition border+transform (0.15s); the "parsing…" pill pulses opacity (1.6s loop). No bounces, no spring overshoot, no decorative motion.
- **Hover states:** surfaces → accent border + slight lift; buttons → `--accent-hover` (a slightly deeper pink); ghost/secondary → `--surface-2` fill. **Press:** subtle — keep it to color, avoid large scale changes.
- **Focus:** `--focus-ring` (pink at ~55%) as a 2px ring on inputs/controls. Always visible for keyboard users.
- **Layout rules:** sticky translucent top bar (height ~62px); content centered at `--content-max` 1180px with 32px gutters; library grid is a 3-column `1fr` grid with 18px gaps and the upload tile as the first cell. The chat panel is a fixed-right overlay, 480px wide (max 94vw), over a dimming scrim.
- **Density:** medium. Comfortable tap targets (buttons ~36–44px tall), but information-dense library cards and metadata.

---

## ICONOGRAPHY
- The current app uses **inline SVG icons** drawn in a thin 1.5px stroke style (see `UploadDropzone` PdfIcon, `ChatPanel` LockIcon in the codebase) — a Heroicons-outline aesthetic.
- **Recommendation for Canvas:** standardize on **[Lucide](https://lucide.dev)** (outline, ~1.75px stroke) — it matches the existing thin-stroke look and is CDN/npm available. Substitute the current bespoke SVGs for the nearest Lucide glyph (e.g. `file-text`, `lock`, `upload`, `arrow-up`, `x`, `plus`). **This is a substitution — flag it** and confirm before standardizing.
- The mocks use a few **text glyphs as placeholders** — "+", "↑", "✕", "▾". Replace these with real icons in production.
- **No icon font, no emoji, no unicode-as-icon** in production. The brand "logo" is a rounded-square monogram **"A"** in `--accent` with `--accent-ink` text, Space Grotesk 700 — not an illustrated mark.
- Real PDF thumbnails (server-rendered first page) should replace the stripe placeholder when available; keep the stripe as the fallback/loading state.

---

## INDEX / MANIFEST
Root:
- `styles.css` — global entry (link this). `@import`s everything below.
- `tokens/` — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `radius.css`, `effects.css`.
- `readme.md` — this guide.
- `SKILL.md` — portable skill wrapper.

Components (`components/`): `Button`, `IconButton`, `Input`, `Badge`, `StatusDot`, `Avatar`, `CitationChip`, `PdfCard`, `UploadTile`, `ChatBubble`. Each has `<Name>.jsx`, `<Name>.d.ts`, `<Name>.prompt.md`, and a `@dsCard` preview HTML.

UI kit (`ui_kits/app/`): full-screen recreations — `AuthScreen`, `LibraryScreen`, `ChatPanel` — composed in an interactive `index.html` (auth → library → open chat → send). This is the visual reference for the redesign.

Guidelines (`guidelines/`): standalone HTML specimen cards for the foundations (colors, type, spacing, radius, effects).
