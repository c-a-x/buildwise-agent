# BuildWise AI Agent · Unified Interface Design System

> Source of truth for the 2026-08-08 unified “Architectural Operations Console” refresh.

## Design intent

BuildWise is a construction-site operations platform, not a generic AI showcase. The interface should feel like a mature project-control product: warm, precise, information-dense, and calm under pressure. Visual emphasis comes from asymmetric composition, editorial headings, architectural grids, solid color blocks, and restrained material texture.

Avoid AI-default visual language: no purple/blue AI gradients, neon glow, decorative particles, robot illustrations, emoji icons, excessive glass blur, or card-everything layouts.

## Global tokens

```css
:root {
  --navy-950: #0b1728;
  --navy-900: #10233d;
  --navy-850: #18304f;
  --primary: #0f6e70;
  --primary-deep: #0b5c60;
  --primary-soft: #e4f0ed;
  --cyan: #3caea5;
  --accent: #a85c0a;
  --accent-soft: #fff0d9;
  --bg: #f7f6f1;
  --surface: #fffdf9;
  --surface-soft: #f0efe8;
  --surface-muted: #e8e8e0;
  --text: #1d2a3a;
  --text-soft: #455568;
  --muted: #5c6b79;
  --muted-light: #7a8792;
  --line: #d9ded9;
  --success: #247a59;
  --success-bg: #e5f3eb;
  --warning: #a85c0a;
  --warning-bg: #fff0d9;
  --danger: #b43f3f;
  --danger-bg: #fde8e5;
  --critical: #8f1d2a;
  --critical-bg: #f8dfe3;
  --shadow-sm: 0 1px 2px rgb(29 42 58 / 6%);
  --shadow-md: 0 8px 24px rgb(29 42 58 / 8%);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --scroll-track: #e8e8e0;
  --scroll-thumb: #0f6e70;
  --scroll-thumb-hover: #0b5c60;
  --ease: 200ms ease;
}
```

## Typography

- Body: system Chinese stack (`PingFang SC`, `Microsoft YaHei`, `Segoe UI`, sans-serif); no remote font dependency.
- Headings: 600–800 weight, tight tracking only for display headings.
- Body: 14–16px, line-height 1.5–1.75.
- Data: tabular numerals; use monospace only for IDs, timestamps, provider states, and trace data.
- Scale: 12 / 14 / 16 / 18 / 24 / 32 / 42px.

## Layout grammar

- Desktop content max width: 1440px; use 32–48px gutters at large widths and 14–20px on phones.
- Use 4/8px spacing rhythm: 4, 8, 12, 16, 24, 32, 48.
- Page headers use a vertical primary marker, strong title, short description, and one visually dominant action.
- Dashboard layout is asymmetric: one wide analytical region plus narrower decision panels.
- Use solid surfaces and 1px rules. Use the architectural SVG grid only as a quiet page texture, never as decoration behind dense text.
- Radius is restrained: 8px for cards/controls, 12px for grouped surfaces, 16px only for feature panels.

## Interaction rules

- Primary CTA per screen: one.
- All interactive targets: minimum 44×44px with at least 8px separation.
- Icon-only controls must have `aria-label`; use the existing SVG `AppIcon` family.
- Focus rings are always visible; never remove browser focus without replacement.
- Loading over 1s uses a skeleton/progress state; errors include recovery action near the source.
- Status must be communicated by text/icon plus color, never color alone.
- Motion is 150–300ms, uses transform/opacity, and respects `prefers-reduced-motion`.
- Drawer/scrim layers use explicit z-index tokens and provide an obvious close action.
- Scrollbars are thin and quiet: warm track, mineral-green thumb, darker hover state; dark navigation surfaces use cyan thumb.
- Native select controls keep keyboard/mobile behavior, while the closed control uses the same 44px height, 8px radius, border, focus ring, and mineral-green chevron.

## Semantic status mapping

| Meaning | Token | UI treatment |
|---|---|---|
| normal / complete | `--success` | text + check/status icon + pale green surface |
| review / pending | `--warning` | text + clock/review icon + pale amber surface |
| danger / high risk | `--danger` | text + warning icon + pale red surface |
| critical | `--critical` | text + critical label + stronger border |
| simulated / offline | `--navy-850` | explicit “模拟/离线” label, never implied |

## Page composition

- Auth: dark field-operations panel + quiet warm form surface; use grid texture and process steps, not glowing AI art.
- Dashboard: six KPI tiles, one dark anchor tile, trend chart, risk mix, work-order flow, recent analysis, due-soon list, anomaly panel.
- Safety/quality: evidence first, clear review banner, visible simulated/draft state, one confirm action.
- Work orders: scan-friendly table/list, risk and deadline visible, draft confirmation clearly separated from execution.
- Reports/knowledge: editorial document layout with readable measure and provenance metadata.
- Green/placeholder modules: formal status, input requirements, reference provenance, and history—not invented compliance claims.
- Error/empty/loading: same state component, same icon language, clear next action.

## Responsive checkpoints

- 375px: one-column content, drawer navigation, no horizontal scroll, 16px minimum body text for inputs.
- 768px: stacked secondary panels, preserved primary action, tables use contained overflow.
- 1024px: two-column analytical layouts where content remains readable.
- 1440px: full asymmetric operations grid and stable 1440px content measure.

## Delivery checklist

- No emoji or mixed icon families.
- No decorative gradients, neon glow, or unpurposeful blur.
- No raw per-component color decisions outside the semantic token system.
- Keyboard navigation, labels, focus, reduced motion, and error recovery verified.
- Visual QA performed at 375 / 768 / 1024 / 1440px.
- Frontend tests, type-check, production build, and backend tests pass.
