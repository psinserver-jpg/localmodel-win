---
name: chartjs
description: Chart.js 4 via CDN - responsive line, bar and doughnut charts with Korean formatting, dark theme colors, update and destroy patterns, and common mistakes.
triggers: [chart.js, chartjs, line chart, bar chart, doughnut, donut chart, pie chart, responsive chart, chart cdn, tooltip, legend, chart update, 차트js, 선 차트, 막대 차트, 도넛 차트, 파이 차트, 반응형 차트, 툴팁, 범례]
---
# Chart.js 4 recipes

Load: `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>` (global `Chart`). Canvas MUST sit in a sized, positioned wrapper.

## Line + bar combo, responsive, Korean formatting
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>매출 차트</title>
<style>
body { margin: 0; padding: 1rem; font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; background: #f8fafc; }
.card { max-width: 48rem; margin: 0 auto; background: #fff; border-radius: 12px; padding: 1rem; border: 1px solid #e5e7eb; }
.box { position: relative; height: 320px; }
@media (max-width: 480px) { .box { height: 260px; } }
</style></head>
<body>
<div class="card"><div class="box"><canvas id="c" role="img" aria-label="월별 매출과 주문 수 차트"></canvas></div></div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script>
const labels = ['1월', '2월', '3월', '4월', '5월', '6월'];
const sales = [12000000, 15400000, 13800000, 19200000, 21500000, 26100000];
const orders = [320, 410, 365, 498, 540, 655];
const won = new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
Chart.defaults.font.family = '"Pretendard Variable", Pretendard, system-ui, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#475569';
const chart = new Chart(document.getElementById('c'), {
  data: {
    labels,
    datasets: [
      { type: 'bar', label: '매출', data: sales, backgroundColor: '#2563eb', borderRadius: 6, yAxisID: 'y', order: 2 },
      { type: 'line', label: '주문 수', data: orders, borderColor: '#f59e0b', backgroundColor: '#f59e0b', borderWidth: 3, tension: 0.35, pointRadius: 4, yAxisID: 'y1', order: 1 },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
      tooltip: {
        callbacks: {
          label: (ctx) => ctx.dataset.label + ': ' + (ctx.dataset.yAxisID === 'y' ? won.format(ctx.parsed.y) : ctx.parsed.y.toLocaleString('ko-KR') + '건'),
        },
      },
    },
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, grid: { color: '#e5e7eb' }, ticks: { callback: (v) => compact.format(v) } },
      y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: (v) => v + '건' } },
    },
  },
});
</script>
</body></html>
```
Mixed charts: omit top-level `type`, give each dataset its own `type`. Two y axes: second one needs `grid.drawOnChartArea: false`.

## Doughnut with center total
```js
// fragment: needs Chart loaded and <canvas id="d"> in a wrapper with a fixed height
const parts = [['검색', 4200], ['광고', 2800], ['SNS', 1900], ['직접', 1100]];
const total = parts.reduce((s, p) => s + p[1], 0);
const centerText = {
  id: 'centerText',
  afterDraw(chart) {
    const { ctx, chartArea: a } = chart;
    ctx.save();
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#0f172a'; ctx.font = '700 24px sans-serif';
    ctx.fillText(total.toLocaleString('ko-KR'), (a.left + a.right) / 2, (a.top + a.bottom) / 2 - 8);
    ctx.fillStyle = '#64748b'; ctx.font = '12px sans-serif';
    ctx.fillText('총 방문', (a.left + a.right) / 2, (a.top + a.bottom) / 2 + 14);
    ctx.restore();
  },
};
new Chart(document.getElementById('d'), {
  type: 'doughnut',
  data: { labels: parts.map((p) => p[0]), datasets: [{ data: parts.map((p) => p[1]), backgroundColor: ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6'], borderWidth: 2, borderColor: '#fff' }] },
  options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom' } } },
  plugins: [centerText],
});
```

## Update, filter, theme switch
```js
// fragment: chart is an existing Chart instance
function setRange(n) {
  chart.data.labels = labels.slice(-n);
  chart.data.datasets[0].data = sales.slice(-n);
  chart.data.datasets[1].data = orders.slice(-n);
  chart.update();
}
function applyTheme(dark) {
  const text = dark ? '#cbd5e1' : '#475569';
  const grid = dark ? '#243049' : '#e5e7eb';
  Chart.defaults.color = text;
  chart.options.scales.y.grid.color = grid;
  chart.options.scales.x.ticks.color = text;
  chart.options.scales.y.ticks.color = text;
  chart.options.plugins.legend.labels.color = text;
  chart.data.datasets[0].backgroundColor = dark ? '#60a5fa' : '#2563eb';
  chart.data.datasets[1].borderColor = dark ? '#fbbf24' : '#f59e0b';
  chart.update();
}
```
If the data array changes length/identity drastically, `chart.destroy()` then `new Chart(...)`. Creating a second Chart on a canvas that already has one throws "Canvas is already in use".

## Common mistakes
- No wrapper height with `maintainAspectRatio: false` gives a 0px chart; the wrapper needs `position: relative` and a height.
- Putting `display: grid` children without `min-width: 0` makes the chart refuse to shrink on window resize.
- Loading the script AFTER your code: put the CDN script tag first.
- `tension: 0.35` smooths lines, but for finance/precise data use `tension: 0`.
- Hidden tab/`display:none` containers render at size 0; call `chart.resize()` when shown.
- Offline file:// still works with the CDN only if online; for offline mode use the plain-SVG approach from dashboard-example.md.
