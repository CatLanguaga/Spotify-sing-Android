# Design System: Spotify Sync Manager
**Project:** Spotify Sync Manager — Desktop utility GUI for curating and syncing Spotify playlists to Android via ADB.

---

## 1. Visual Theme & Atmosphere

Utilitarian darkness with a single pulse of life. The interface is dense, focused, and unapologetically technical — built for someone who knows what they're doing. It borrows the unmistakable accent green from Spotify but strips away all the marketing softness, leaving only the raw utility of a developer tool. Think: terminal meets music player. Every pixel earns its place. Whitespace is spent deliberately, not generously. The mood is **precise, controlled, and quietly confident** — the kind of tool that runs in the background while you do other things, but demands your full attention when something needs a decision.

---

## 2. Color Palette & Roles

| Descriptive Name | Hex | Functional Role |
|---|---|---|
| Void Black | `#0D0D0D` | App shell background — the deepest layer |
| Charcoal Surface | `#111111` | Main panel backgrounds, sidebar |
| Lifted Slate | `#1A1A1A` | Cards, table rows, elevated containers |
| Hover Ash | `#222222` | Interactive row highlight on hover |
| Hairline Gray | `#2A2A2A` | Dividers, input borders, table separators |
| Spotify Pulse Green | `#1DB954` | Primary CTAs, active nav items, approved states, progress bars |
| Green Tint Wash | `rgba(29,185,84,0.10)` | Tinted badge backgrounds, selected states, approved card accents |
| Alert Crimson | `#E22D44` | Missing tracks, rejected items, error log lines, destructive actions |
| Crimson Wash | `rgba(226,45,68,0.10)` | Rejected card background tint |
| Amber Warning | `#F59B23` | Dubious/low-score matches, warning log lines |
| Amber Wash | `rgba(245,155,35,0.10)` | Warning badge backgrounds |
| Pure White | `#FFFFFF` | Primary headings, key track titles |
| Silver Secondary | `#B3B3B3` | Artist names, descriptions, secondary metadata |
| Fog Muted | `#666666` | Timestamps, column headers, placeholder text |
| Terminal Background | `#090909` | Log output area — slightly deeper than void |

**Language Badge Colors** (each badge uses its color at 10% opacity for background):

| Language | Color | Badge Background |
|---|---|---|
| JP — Japanese | Hot Pink `#FF6B9D` | `rgba(255,107,157,0.10)` |
| KR — Korean | Soft Violet `#A29BFE` | `rgba(162,155,254,0.10)` |
| EN — English | Sky Blue `#74B9FF` | `rgba(116,185,255,0.10)` |
| ES — Spanish | Warm Yellow `#FDCB6E` | `rgba(253,203,110,0.10)` |
| CN — Chinese | Coral Red `#FF7675` | `rgba(255,118,117,0.10)` |
| RU — Russian | Mint Teal `#55EFC4` | `rgba(85,239,196,0.10)` |

**Score Color Scale:**

| Range | Color | Label |
|---|---|---|
| 85–100% | Spotify Pulse Green `#1DB954` | High confidence |
| 65–84% | Amber Warning `#F59B23` | Review recommended |
| 0–64% | Alert Crimson `#E22D44` | Likely mismatch |

---

## 3. Typography Rules

**UI Font:** `-apple-system, Inter, Segoe UI, system-ui, sans-serif` — clean and legible at small sizes, never decorative. Base size is 13px with 1.5 line-height.

- **Page titles:** 17px, weight 700, letter-spacing -0.02em — tight and assertive
- **Section headings:** 10px, weight 700, uppercase, letter-spacing 0.08em — used as column headers and section labels in muted gray
- **Track names / primary content:** 12.5–13px, weight 500–600
- **Metadata / secondary text:** 11–11.5px, weight 400, in Silver Secondary
- **Timestamps and badges:** 10–11px, weight 600 for badges, monospace font

**Terminal Font:** `JetBrains Mono, Fira Code, Cascadia Code, Consolas, monospace` — used exclusively in the Process Monitor log output and for file paths, score values, and timestamps where data precision matters.

---

## 4. Component Stylings

**Buttons:**
- Primary (Green): Spotify Pulse Green background, black text, 5–6px radius, 7px vertical / 14px horizontal padding, weight 600. Brightness increases on hover via `filter: brightness(1.12)`.
- Ghost/Default: Lifted Slate background, Silver text, 1px Hairline Gray border, same radius. Used for secondary actions.
- Tinted Green: Green Tint Wash background, Spotify Green text, 1px semi-transparent green border. Used for "approve" states and queue add actions.
- Tinted Red: Crimson Wash background, Alert Crimson text, 1px red border. Used for "reject" states.
- Disabled: 40% opacity, non-interactive cursor.
- Icon buttons: 32×32px square, 6px radius, ghost style, single emoji or SVG icon centered.

**Cards / Queue Items:**
- Background: Lifted Slate (`#1A1A1A`)
- Border: 1px Hairline Gray by default; switches to semi-transparent green border when approved, red border when rejected
- Radius: 8px
- No drop shadow — separation is achieved purely through background color contrast
- Approved items: 2px solid Spotify Green top accent bar
- Rejected items: 45% opacity

**Table Rows (Compare View):**
- No card treatment — rows sit directly on Charcoal Surface
- Alternating backgrounds not used — separation via subtle bottom border `rgba(255,255,255,0.04)`
- Hover: background shifts to Hover Ash `#222222` with smooth 0.1s transition
- Two-column grid, equal width, divided by a 1px Hairline Gray vertical border

**Score / Language / Status Badges:**
- Shape: Subtly rounded rectangle (3px radius), not pill-shaped
- Score badge: monospace font, weight 700, color-coded text on matching tint background
- Language badge: 10px, weight 700, uppercase, monospace
- Status badge: 11px, weight 500, descriptive text ("✓ Existe", "— Falta", "? Dudoso")

**Input Fields:**
- Background: Lifted Slate `#1A1A1A`
- Border: 1px Hairline Gray `#2A2A2A` default; transitions to semi-transparent Spotify Green on focus
- Radius: 5px
- Text: Pure White at 12px
- No drop shadow, flat appearance

**Range Sliders:**
- `accent-color: #1DB954` — thumb and fill track take Spotify Green
- Label above shows current value colored by the score scale (green/amber/red)

**Progress Bars:**
- Height: 3px (in compare header) or 4px (in monitor toolbar)
- Track: Hairline Gray
- Fill: Spotify Green
- Radius: 2px

**Modal (YouTube Search):**
- Backdrop: `rgba(0,0,0,0.72)` with `backdrop-filter: blur(6px)`
- Modal card: Charcoal Surface `#111111`, 12px radius, 1px `#333` border
- Box shadow: `0 32px 96px rgba(0,0,0,0.7)` — heavy, deep, luxurious
- Appears with a subtle `fadeIn` animation (opacity 0→1, translateY 4→0px, 150ms)

**Sidebar Navigation:**
- Width: 60px, fixed, icon-only
- Background: Near-black `#080808` — slightly deeper than surface
- Nav items: 46×46px, 9px radius, icon centered
- Active state: Green Tint Wash background, icon in Spotify Green
- Hover state (inactive): Hover Ash background
- Logo mark: 34px circle in Spotify Green with Spotify-style sound-wave SVG in black
- ADB status dot: 8px circle, Spotify Green, pulsing animation, labeled "ADB" in 8px monospace below

**Terminal / Log Output:**
- Background: Terminal Background `#090909`
- Font: JetBrains Mono, 11.5px, 1.75 line-height
- Log line layout: three columns — timestamp (muted, 56px fixed), level badge (bold, 58px fixed), message text
- Colors per level:
  - `[INFO]` label: Spotify Green `#1DB954` · message: muted green `#A8C9A8`
  - `[WARNING]` label: Amber `#F59B23` · message: warm amber `#E0C87A`
  - `[ERROR]` label: Crimson `#E22D44` · message: light red `#FF8A9A`
- Auto-scrolls to bottom as new lines arrive

---

## 5. Layout Principles

**Shell:** Fixed 60px left sidebar + full-height main content area. No top navigation bar. The sidebar is the only persistent navigation element.

**Density:** High. This is a data-heavy utility tool. Rows are compact (38–42px height) with just enough padding to be comfortably tappable. Section headers are minimal — 10px uppercase labels, not H2s.

**Spacing rhythm:** 8px base unit. Common spacings: 4px (tight gaps between inline elements), 8px (badge internal padding, small gaps), 12px (card internal padding), 16px (row horizontal padding), 20–22px (page header padding), 24–28px (column gaps in settings).

**Two-column layouts:** Used in the Compare View (Spotify ↔ Phone, 50/50 split) and Settings (Config / Filters, each ~460px in a 920px max-width container).

**Scrolling:** Only the content area scrolls — the sidebar and page headers are always visible. Custom scrollbar: 5px width, transparent track, Hairline Gray thumb that darkens on hover.

**Stat strips:** Horizontal row of tight stat cards (padding 7px 12px) with large monospace number + small label below. Cards use Lifted Slate background with Hairline Gray border.

**Visual hierarchy:** Achieved through background color layering (Void → Surface → Elevated), text color stepping (White → Silver → Fog), and accent color application (green for positive, red for negative, amber for ambiguous).

**Animations:** Kept minimal and functional — `fadeIn` for modals, `blink` for live indicators, smooth `width` transitions for progress bars. No decorative motion.
