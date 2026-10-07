---
name: dashboard-data-viz
description: Dashboards and data visualisation - admin layout (sidebar, topbar, grid), KPI cards, sortable tables, filters, empty/loading/error states, chart choice and accessible colors, plain SVG or Chart.js, Intl number formatting. Use for dashboards, admin panels, charts and analytics screens.
triggers: [dashboard, admin, admin panel, analytics, kpi, metrics, chart, charts, chart.js, graph, data table, sortable table, sidebar, report, statistics, data visualization, data viz, stat card, sparkline, donut, pie chart, 대시보드, 관리자, 관리자 페이지, 통계, 차트, 그래프, 표, 테이블, 지표, 매출, 분석, 데이터 시각화, 사이드바]
priority: 48
---
# Dashboard and data visualisation

Answer first, decoration last: a dashboard exists so a person can see "is it good or bad, and why" in 5 seconds.

## Layout rules
1. Shell: CSS grid `grid-template-columns: 240px 1fr` (sidebar | main); sidebar collapses to a top bar / drawer under 900px. Topbar 64px with title, date-range filter, user menu. Main `padding: 24px`, content `max-width: 1440px`.
2. Top row = 3-4 KPI cards (`repeat(auto-fit, minmax(220px, 1fr))`, gap 16px). Then 1 wide primary chart (2/3 width) + 1 side chart (1/3). Then a table. Order by importance, top-left first.
3. Card: radius 12px, 1px border, padding 20px, title 14px muted, value 28-32px bold with `font-variant-numeric: tabular-nums`, delta chip (green up `#047857` on `#d1fae5`, red down `#b91c1c` on `#fee2e2`) with an arrow AND a sign (not color alone), optional sparkline.
4. Every data region has 4 states: loading (skeleton shimmer), empty ("아직 데이터가 없어요" + action), error (message + "다시 시도" button), data. Build all four.
5. Dark theme: bg `#0b0f19`, surface `#131a2a`, border `#243049`, text `#e6eaf2`, muted `#94a3b8`; lighten series colors. Use `color-scheme: light dark` and token swap in `@media (prefers-color-scheme: dark)`.
6. Korean: `word-break: keep-all`, font Pretendard stack, numbers tabular, units in labels (원, 명, %).

## Chart choice
- Trend over time: line (>8 points) or column (<=8). Compare categories: horizontal bar sorted descending (long Korean labels fit). Part of whole: stacked bar or donut with <=5 slices + center total; NEVER pie with >5 slices. Correlation: scatter. Distribution: histogram. One number: KPI card, not a chart.
- Bars start at 0. Lines may not. No 3D, no dual axes unless unavoidable (then label both axes with color + text), no gradient fills that hide values.
- Label directly (end of line, value on bar) instead of legends when <=4 series. Max 5-6 series.
- Color: sequential single-hue for magnitude; categorical palette (colorblind-safe, Okabe-Ito based): `#2563eb #f59e0b #10b981 #ef4444 #8b5cf6 #64748b`. Dark mode: `#60a5fa #fbbf24 #34d399 #f87171 #a78bfa #94a3b8`. Pair color with shape/label so grayscale still works. Gridlines light `#e5e7eb`, no chart border.
- Add `role="img"` + `aria-label` summary on charts, and offer the numbers in a table (`<details><summary>표로 보기</summary>`).

## Number formatting (Intl)
```js
const won = new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1, signDisplay: 'exceptZero' });
const date = new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' });
console.log(won.format(1250000), compact.format(1250000), pct.format(0.123), date.format(new Date(2025, 2, 14)));
```
Output: `₩1,250,000`, `125만`, `+12.3%`, `3월 14일 (금)`. Use `compact` in axes, full `won` in tables/tooltips.

## Sortable table (core)
```js
function sortRows(rows, key, dir) {
  const k = dir === 'asc' ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = a[key], y = b[key];
    return (typeof x === 'number' && typeof y === 'number') ? (x - y) * k : String(x).localeCompare(String(y), 'ko') * k;
  });
}
```
Table CSS: `thead th { position: sticky; top: 0; background: var(--surface); }` inside a wrapper with `max-height: 420px; overflow: auto`; `tbody tr:nth-child(even) { background: var(--zebra); }`; numbers `text-align: right`; header buttons carry `aria-sort`; row height 44-48px; hover row highlight.

## Pitfalls
- Chart.js canvas needs a wrapper with `position: relative; height: 320px` plus `maintainAspectRatio: false`, or it grows forever / collapses to 0.
- Call `chart.destroy()` before re-creating on the same canvas; update with `chart.data = ...; chart.update()`.
- CDN: `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>`; offer a plain SVG fallback if the page must work offline.
- Never fake data silently: keep sample data in one `const DATA` object at the top, with realistic Korean names/amounts, and say it is sample data in a code comment.
- Flex/grid children holding tables or charts need `min-width: 0`, else the page scrolls sideways.
- See reference/dashboard-example.md (complete runnable dashboard, plain SVG charts, dark theme) and reference/chartjs.md (Chart.js 4 line/bar/donut with responsive options).
