# Wingman AI — Enterprise Frontend Design System & Architecture

## 1. Design Philosophy
Wingman AI is art-directed as a precision developer infrastructure tool inspired by **Linear**, **Raycast**, **Sentry**, and **Vercel**.
- **No generic AI SaaS aesthetics**: Zero blue primary accents, zero neon gradients, zero glassmorphism, and no rounded-card clutter.
- **Intentional Monochromatic Palette**: High information density with restrained, functional color coding.
- **Craftsmanship over Decoration**: Hairline borders, flat surfaces, editorial tabular data, and monospaced technical values.

---

## 2. Color System Token Specification

| Token | Hex Value | Semantic Usage |
|---|---|---|
| `bg-app` | `#090909` | Base canvas background |
| `bg-sidebar` | `#0C0C0C` | Left navigation rail |
| `bg-surface` | `#111111` | Primary editorial surfaces and tables |
| `bg-raised` | `#171717` | Technical stat chips, controls, inputs |
| `bg-hover` | `#1D1D1D` | Table row and interactive hover states |
| `border-subtle` | `#1B1B1B` | Secondary dividers and subtle bounds |
| `border-primary` | `#252525` | Primary structural borders |
| `border-strong` | `#303030` | Focused elements and active selections |
| `text-primary` | `#EAE8E3` | Primary headlines, data points, and active labels |
| `text-secondary` | `#A09E98` | Secondary labels, descriptions, and table headers |
| `text-muted` | `#686761` | Timestamps, units, and structural metadata |
| `status-coral` | `#D66A61` | Critical alerts (P1), 5xx errors, active faults |
| `status-amber` | `#D6A65D` | Warning alerts (P2), latency degradations, investigating |
| `status-sage` | `#75A98B` | Operational baseline, verified healthy, approved |
| `status-neutral` | `#AAA69E` | Secondary metadata and technical tags |

---

## 3. Typography & Micro-Layouts
- **Font Stack**:
  - UI Prose: `Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`
  - Technical Metrics, IDs & Timestamps: `JetBrains Mono, Geist Mono, SFMono-Regular, monospace`
- **Border Radii**: Strictly bounded to 2px–6px (`rounded-sm`).
- **Data Densities**: Flat surfaces with full-width tables instead of isolated rounded boxes.
