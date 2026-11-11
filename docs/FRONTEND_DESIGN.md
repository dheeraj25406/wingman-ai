# Wingman AI — Enterprise Frontend Design System & Architecture

The frontend is built to feel like an authoritative, precision-engineered enterprise observability tool inspired by Datadog, Linear, Grafana, and Sentry.

## 1. Design Token System & Palette

```css
:root {
  --bg-app: #0D1117;          /* Base dark background */
  --bg-sidebar: #111720;      /* Left-rail navigation */
  --bg-surface: #151D27;      /* Primary content surfaces/cards */
  --bg-surface-raised: #1A2430; /* Hover & elevated elements */
  --border-subtle: #222C38;   /* Subtle divider borders */
  --border-strong: #293442;   /* Focus/active borders */

  --text-primary: #E6EDF3;    /* Main headlines and data points */
  --text-secondary: #929EAD;  /* Descriptions, column headers */
  --text-muted: #647184;      /* Timestamps, IDs, disabled */

  --accent: #65A9FF;          /* Primary functional blue */
  --success: #35B88A;         /* Verified, healthy, approved */
  --warning: #E8B45B;         /* Degraded, high latency, caution */
  --critical: #E16B73;        /* Outage, connection failure, 5xx */
}
```

### Typography
- **UI & Prose**: `Inter, system-ui, -apple-system, sans-serif`
- **Code, Hashes, Metrics & IDs**: `Geist Mono, JetBrains Mono, monospace`
- **Scale**: Restrained type scale (12px caption, 13px table text, 14px body, 16px section headers, 20px page titles).

### Spacing & Elevation
- 8px baseline grid (padding: 8px, 12px, 16px, 24px).
- Tight, disciplined border-radii: 4px for buttons and badges, 6px for cards and dialogs.
- No heavy gradient glows, glassmorphism, or decorative cartoonish animations.

---

## 2. Navigation & Page Structure

Left fixed navigation rail (collapsed or 240px wide):
1. **Overview** (`/`): Health metrics, global throughput, active incidents, service status grid.
2. **Incidents** (`/incidents`): Filterable incident table with status badges and ML confidence tags.
3. **Investigation** (`/incidents/:id`): Deep-dive split-view with:
   - Header: Status, severity, affected services, MTTR timer.
   - Left pane: Interactive timeline, anomalous telemetry charts, trace waterfall preview, raw logs.
   - Right pane: Ranked root-cause hypotheses with evidence badges, runbook citations, and human approval remediation card.
4. **Service Map** (`/services`): React Flow node-edge graph showing live traffic flow, latency, error status, and upstream/downstream propagation.
5. **Model Intelligence** (`/models`): ML model cards, feature importances, ROC/PR curves, confusion matrix.
6. **AI Evaluation** (`/evaluations`): Benchmark suite history, Top-1/Top-3 accuracy breakdown, latency vs token cost, failure inspector.
7. **Fault Lab** (`/fault-lab`): Interactive fault injection controls with intensity sliders, duration pickers, and live telemetry preview.
8. **Settings** (`/settings`): Gemini configuration check, integration health, safety mode toggles.

---

## 3. Component Architecture & Tech Stack
- **Framework**: React 18 with Vite.
- **State & Server Cache**: TanStack Query (React Query) v5 with 3-second polling for active incidents and real-time fault states.
- **Routing**: React Router v6.
- **Icons**: Lucide React.
- **Charts**: Recharts (dark-themed, strict color-coded series).
- **Topology**: React Flow (@xyflow/react) with custom service nodes.
- **Forms & Validation**: Zod.
