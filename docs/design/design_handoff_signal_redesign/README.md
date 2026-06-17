# Handoff: Insight Engine — "Signal" Redesign (Desktop + Mobile)

## Overview
A full visual redesign of Insight Engine that moves the app off the generic shadcn
indigo theme onto a distinctive **editorial "Signal" system**: warm paper canvas,
near-black ink, a single bold vermilion accent reserved strictly for actions, and
JetBrains Mono for all metadata/numbers. It covers the core flow
(URL → style select → generate → editor) plus Library and Dashboard, on both
desktop and mobile (bottom-tab layout).

## About the Design Files
The files in this bundle are **design references created in HTML** — interactive
prototypes that demonstrate the intended look, layout, and behavior. They are
**not production code to copy directly**. The task is to **recreate these designs
in the existing Next.js + Tailwind v4 + shadcn codebase**, using its established
component patterns (the `frontend/components/**` library, shadcn primitives, the
`globals.css` token system). The fastest path is to swap design tokens (see
`globals.signal.css.patch.css`) and then adjust a handful of components to match
the Signal patterns described below.

Open the prototypes in a browser to interact with them:
- `Insight Engine Redesign.dc.html` — static design board: token system + the main
  flow in 3 directions (A/B/C) + editor, dashboard, library, onboarding.
- `Insight Engine Prototype.dc.html` — **clickable desktop prototype** of Direction A
  (the approved one): full state machine, animated generation pipeline.
- `Insight Engine Mobile.dc.html` — **clickable mobile prototype** (iPhone frame,
  bottom tab bar).

> **Approved direction: A — "Editorial Command."** Build to A. B and C in the board
> are alternatives, kept only for reference.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, and interactions are
specified. Recreate the UI pixel-accurately using the codebase's existing libraries
(shadcn components, Tailwind tokens). Exact values are in **Design Tokens** below and
in the CSS patch file.

---

## Design Tokens

Apply `globals.signal.css.patch.css` (drop-in replacement for the `:root` / `.dark`
blocks in `frontend/app/globals.css`). Summary:

### Colors
| Token | Old (indigo) | New (Signal) | Use |
|---|---|---|---|
| `--background` | `#ffffff` | **`#FAF8F4`** Paper | app canvas |
| `--foreground` | `#111827` | **`#17150F`** Ink | primary text |
| `--primary` | `#4F46E5` | **`#EA4E20`** Vermilion | actions ONLY |
| `--card` | `#ffffff` | `#ffffff` | cards (white on paper) |
| `--secondary` / `--muted` | `#F3F4F6` | **`#F1EEE7`** Wash | fills |
| `--muted-foreground` | `#6B7280` | `#6E6A60` | secondary text |
| `--accent` | `#EEF2FF` | `#FBE9E3` | accent surface |
| `--accent-foreground` | `#4F46E5` | `#EA4E20` | accent text |
| `--border` / `--input` | `#E5E7EB` | `#E5E0D7` / `#DAD4C9` | hairlines |
| `--ring` | indigo 0.3 | `rgba(234,78,32,0.35)` | focus |
| `--sidebar` | `#F8FAFC` | `#F1EEE7` | sidebar panel |
| `--sidebar-primary` | `#4F46E5` | **`#17150F`** | "새 분석" btn = ink |
| `--radius` | `0.625rem` | **`0.2rem`** | sharper corners |

**Source-type colors** (badges + dots, not tokens — small inline map):
`YouTube #FF0033 · arXiv #7C5CFF · RSS #F59E0B · Web #2D7FF9 · Podcast #1FA672`.

**Chart palette:** `#EA4E20, #1FA672, #F59E0B, #7C5CFF, #2D7FF9`.

### Typography
- **Sans:** Pretendard (already wired). Headings 600–700, tight tracking
  (`letter-spacing: -0.02em` on large display, `-0.01em` on H2).
  Display sizes desktop: hero 38px/700, page H1 34px/700, section H2 21px/600.
  Mobile: hero 30px/700, H1 25px/700, H2 18px/600.
- **Mono:** JetBrains Mono (already wired). **Use for ALL of:** metadata lines,
  timestamps, token counts, percentages, step labels, uppercase section eyebrows,
  KPI numbers, table times, credit count. Typical: 9–11px, `letter-spacing 0.04–0.18em`,
  `text-transform: uppercase` for eyebrows/labels.
- Body copy: 15–15.5px, `line-height 1.75`, `color: foreground/0.82`.

### Spacing / Radius / Shadow
- Radius: 2–5px everywhere (`--radius` 0.2rem). Pills/chips use `border-radius: 100px`.
- **No gradients. No soft drop-shadows on cards** — use `1px solid --border` instead.
- The ONE deliberate shadow = **hard offset** on primary CTA & hero input:
  `box-shadow: 3px 3px 0 rgba(23,21,15,0.18)` (buttons),
  `4px 4px 0 rgba(23,21,15,0.10)` (hero URL field, which also has a `1.5px solid #17150F` border).

---

## Screens / Views

### 1. Generate — Input (primary screen)
- **Purpose:** paste source URL(s), pick output styles, choose mode, generate.
- **Layout (desktop):** left **Sidebar 236px** (wash `#F1EEE7`, hairline right border) +
  main column = **header 54px** (tab nav + credits/avatar) over a scrollable canvas
  with `padding: 52px 56px`.
- **Components:**
  - **Sidebar:** logo (26px ink square with a 9px vermilion dot) · **"+ 새 분석"** button
    (full-width, 42px, ink `#17150F` bg, paper text) · search field (white, hairline) ·
    "오늘" mono eyebrow · history rows (active row = white card w/ hairline; each row has a
    source-type dot, 12px medium title, mono `time · style` meta) · footer mono
    "POWERED BY LITELLM".
  - **Header tabs:** 생성 / 라이브러리 / 대시보드 / 캘린더, 13px. Active tab = ink + `2px solid #EA4E20`
    bottom border. Right: mono "크레딧 847", 30px ink avatar.
  - **Eyebrow:** mono `새 분석 · STEP 01`, vermilion, uppercase, `letter-spacing .16em`.
  - **Hero heading:** 38px/700 ink, two lines.
  - **URL bar:** white, `1.5px solid #17150F`, radius 4px, hard offset shadow, max-width 720px.
    Leading source-type dot (`#FF0033`), text input, "설정" mono button (wash), 46px vermilion
    "↑" submit. Helper line in mono below.
  - **URL chips** (after add): wash pills, source dot + short id + mono type + "×" remove.
  - **Style grid:** label row ("출력 스타일 14" + mono selected count in vermilion) over a
    **7-col grid, 8px gap, max-width 860px**. Each cell ~13px pad, 12px label, radius 3px.
    Selected = ink bg + paper text + 600; unselected = white + hairline + muted text.
  - **Generate row:** 50px vermilion button "콘텐츠 생성 ×N" (hard offset shadow) +
    mono segmented `개별 / 통합 / 퓨전` (active = ink fill). Disabled button = `rgba(23,21,15,0.12)`
    bg, muted text, no shadow, when 0 URLs or 0 styles.

### 2. Generate — Running (pipeline)
- **Purpose:** show generation progress.
- **Layout:** two columns — left 440px pipeline, right flexible live-preview skeleton.
- **Components:** mono eyebrow `생성 중 · STEP 02`; 34px heading "엔진이 분석하고 있어요";
  mono sub `N개 스타일 · 모드 · N개 소스`; **big mono percentage** (56px ink) + vermilion "%";
  6px wash progress track with vermilion fill (`transition: width .18s linear`).
  **4 stage rows** — 소스 수집 / 핵심 분석 / 콘텐츠 생성 / QA 검수. States: done = 20px green
  circle w/ ✓ + "완료"; active = 20px vermilion dot w/ `0 0 0 4px rgba(234,78,32,.15)` halo,
  row bg `rgba(234,78,32,.05)`, label 600; todo = hollow `1.5px` ring, muted.
  Right: white card, shimmer-pulsing skeleton bars (one bar tinted vermilion `0.18`).
- **Timing:** progress 0→100 by +2 every 55ms (~2.75s), then auto-advance to Editor.
  Active stage index = `min(3, floor(progress/25))`.

### 3. Editor (result)
- **Purpose:** read/edit the generated piece, re-spin styles, publish.
- **Layout:** sub-toolbar 56px over (document column + right rail 312px wash).
- **Components:** back "←" · source dot · 14px title · ink style badge · **"QA 통과"** green
  pill · DOCX/MD/PDF mono export buttons · vermilion **"발행"**.
  Document: max-width 680px, mono meta line `14:32 · GEMINI-3.1-FLASH · 1,840 TOKENS · 한국어`,
  34px H1, 15.5px/1.75 body, an inline highlighted span (`bg rgba(234,78,32,.16)` +
  `0 0 0 1px rgba(234,78,32,.4)`), vermilion underlined link, **vermilion left-border
  blockquote**. Rail: source thumbnail card; **"다른 스타일로"** list (click → regenerate in
  that style); **발행** channels (네이버 블로그 / WordPress, colored square + mono "MCP").

### 4. Library
- **Purpose:** browse generated content.
- **Layout (desktop):** filter bar (style count pills + "선택 N · 일괄" + grid/list toggle)
  over a **4-col card grid, 16px gap**, `padding 24px 30px`. A trailing dashed "새 분석 시작" tile.
- **Card:** white, hairline, radius 4px, 18px pad. Source dot + mono style label; 14px/600
  title (2-line clamp, 56px height); mono meta `time · tokens · status`. Click → Editor.
  Selected card = `1.5px solid #EA4E20` + vermilion check chip top-right.

### 5. Dashboard
- **Purpose:** operations & analytics.
- **Layout:** 4 KPI cards (one is **ink-filled**: 토큰 사용 `2.4M`), then a 2fr/1fr row
  (일별 생성량 bar chart + 프로바이더 분포 bars), then a 발행 큐 table.
- **Details:** KPI numbers in **mono 38px**; chart bars wash with the peak bar vermilion;
  provider bars: Gemini bar vermilion, rest ink; queue rows have status dots
  (green 완료 / amber 재시도 / neutral 대기) + mono timestamps.

### 6. Mobile (all of the above, bottom-tab layout)
- **Frame:** iPhone — 402×872 bezel (`#0c0b08`, radius 58, 13px pad), screen radius 46,
  status bar (9:41 + signal/wifi/battery), dynamic island pill, home indicator.
- **Bottom tab bar:** 78px, 3 tabs (생성 / 라이브러리 / 대시보드) with line-icons; active = vermilion.
- **Generate:** compact header, hero 30px, full-width URL field, URL chips as full-width rows,
  **styles as wrapping toggle pills** (not a grid), mode as a full-width **segmented control**,
  sticky bottom **생성** CTA above the tab bar.
- **Running:** single column, 62px mono %, stacked stage rows.
- **Editor:** sticky top (back + title + 발행), scrolling doc, **horizontal-scroll** "다른 스타일로"
  chips, stacked publish channels.
- **Library:** stacked cards, horizontal-scroll filter pills.
- **Dashboard:** 2-col KPI grid, stacked chart + provider cards.
- **Touch targets ≥ 44px.**

---

## Interactions & Behavior
- **Add URL:** Enter key or "↑" button → parse type from string
  (youtu→YouTube, arxiv→arXiv, rss/feed→RSS, podcast/.mp3→Podcast, else Web),
  derive a short id (YouTube `v=` / `youtu.be/` id, else trimmed host+path), push chip,
  clear input. "×" removes a chip.
- **Toggle style:** click pill/cell flips selected state; selected count + button "×N" update.
- **Mode:** 개별 / 통합 / 퓨전 segmented — single select.
- **Generate:** disabled unless ≥1 URL AND ≥1 style. On click → Running, start interval timer.
- **Pipeline → Editor:** at 100%, clear timer, set step = done; `activeStyle` = first selected.
- **Deep links:** sidebar history rows and library cards open the Editor for that style.
- **"새 분석" / back "←":** reset to Generate-Input, clear timer & progress.
- **Tab nav:** switches top-level view; Generate retains its sub-state.
- **Animation:** progress bar `width transition .18s linear`; skeleton `shimmer` 1.4s
  ease-in-out infinite (respect `prefers-reduced-motion`, already handled in globals.css).

## State Management
Single view-model (mirror in React via `useReducer`/Zustand or local state):
```
tab:        'generate' | 'library' | 'dashboard'
genStep:    'input' | 'running' | 'done'      // sub-state of the generate tab
urlText:    string                            // controlled input
urls:       { id, type, color }[]
styles:     { name, on }[]                     // 14 entries
mode:       'individual' | 'merged' | 'fusion'
progress:   number 0..100                      // timer-driven
activeStyle:string                             // drives editor title/badge
```
Transitions: `addUrl/removeUrl`, `toggleStyle(i)`, `setMode`, `startGen` (timer),
`openEditor(style)`, `newAnalysis` (reset), `goGenerate/goLibrary/goDashboard`.
In the real app, `startGen` should be replaced by the actual generation API / SSE stream;
map real pipeline stages onto the 4 stage rows and drive the percentage from progress events.

## Mapping to existing code
- Tokens → `frontend/app/globals.css` (use the patch).
- Sidebar → `frontend/components/layout/Sidebar.tsx`.
- URL field → `frontend/components/input/UrlInput.tsx`.
- Pipeline → `frontend/components/agent/AgentPipeline.tsx` (reuse for the 4 stage rows).
- Editor/results, Library, Dashboard → corresponding views under `frontend/app/**` and
  `frontend/components/**`. Keep shadcn primitives; only restyle per Signal patterns.

## Assets
No raster assets. Logo is a CSS mark (ink rounded square + vermilion dot). Icons are
inline line-SVGs (tab bar, status bar) — reuse `lucide-react` equivalents:
plus-circle (생성), layout-grid (라이브러리), bar-chart (대시보드). Fonts already installed.

## Files in this bundle
- `globals.signal.css.patch.css` — token drop-in + utility notes.
- `Insight Engine Redesign.dc.html` — design board (system + A/B/C + all screens).
- `Insight Engine Prototype.dc.html` — clickable desktop prototype (Direction A).
- `Insight Engine Mobile.dc.html` — clickable mobile prototype.

> The `.dc.html` files are self-contained HTML and open directly in a browser; treat
> them as the source of truth for spacing/color/behavior when a detail isn't spelled out above.
