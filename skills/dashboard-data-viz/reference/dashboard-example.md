---
name: dashboard-example
description: Complete runnable admin dashboard in one HTML file - sidebar, topbar, KPI cards, plain-SVG line chart, sortable sticky table, loading and empty states, light and dark theme, Korean formatting.
triggers: [full dashboard, admin dashboard, dashboard example, admin layout, kpi cards, sortable table, sticky header, skeleton, empty state, dark dashboard, sidebar layout, 대시보드 예제, 관리자 대시보드, 전체 대시보드, 정렬 테이블, 스켈레톤, 빈 상태, 다크 대시보드]
---
# Complete small dashboard (single file, no libraries)

Adapt names and numbers to the user's business; keep data in `DATA`.

```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>매출 대시보드</title>
<style>
:root { color-scheme: light dark; --bg:#f4f6fb; --surface:#fff; --border:#e5e7eb; --text:#0f172a; --muted:#64748b; --zebra:#f8fafc;
  --primary:#2563eb; --up:#047857; --up-bg:#d1fae5; --down:#b91c1c; --down-bg:#fee2e2; --grid:#e5e7eb; }
@media (prefers-color-scheme: dark) { :root { --bg:#0b0f19; --surface:#131a2a; --border:#243049; --text:#e6eaf2; --muted:#94a3b8; --zebra:#0f1624;
  --primary:#60a5fa; --up:#6ee7b7; --up-bg:#064e3b; --down:#fca5a5; --down-bg:#7f1d1d; --grid:#243049; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); word-break: keep-all;
  font: 15px/1.5 "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
.shell { display: grid; grid-template-columns: 240px minmax(0, 1fr); min-height: 100vh; }
.side { background: var(--surface); border-right: 1px solid var(--border); padding: 20px 12px; position: sticky; top: 0; height: 100vh; }
.brand { font-weight: 800; font-size: 18px; padding: 0 12px 16px; }
.side a { display: flex; align-items: center; min-height: 44px; padding: 0 12px; border-radius: 8px; color: var(--muted); text-decoration: none; font-weight: 600; }
.side a[aria-current="page"] { background: color-mix(in srgb, var(--primary) 14%, transparent); color: var(--primary); }
.top { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 64px; padding: 0 24px; border-bottom: 1px solid var(--border); background: var(--surface); }
.top h1 { font-size: 18px; margin: 0; }
select, button { font: inherit; color: var(--text); background: var(--surface); border: 1px solid var(--border); border-radius: 8px; min-height: 40px; padding: 0 12px; }
main { padding: 24px; display: grid; gap: 16px; min-width: 0; }
.kpis { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; min-width: 0; }
.card h2 { font-size: 14px; color: var(--muted); font-weight: 600; margin: 0 0 8px; }
.val { font-size: 28px; font-weight: 800; font-variant-numeric: tabular-nums; }
.chip { display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.chip.up { color: var(--up); background: var(--up-bg); } .chip.down { color: var(--down); background: var(--down-bg); }
.grid2 { display: grid; gap: 16px; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); }
.chart svg { display: block; width: 100%; height: auto; }
.chart text { font-size: 11px; fill: var(--muted); }
.wrap { max-height: 360px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 16px; text-align: left; white-space: nowrap; }
th { position: sticky; top: 0; background: var(--surface); border-bottom: 1px solid var(--border); font-size: 13px; color: var(--muted); }
th button { all: unset; cursor: pointer; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr:nth-child(even) { background: var(--zebra); }
.skel { height: 1em; border-radius: 6px; background: linear-gradient(90deg, var(--border), var(--zebra), var(--border)); background-size: 200% 100%; animation: sh 1.2s linear infinite; }
@keyframes sh { to { background-position: -200% 0; } }
.empty { padding: 40px; text-align: center; color: var(--muted); }
@media (max-width: 900px) { .shell { grid-template-columns: 1fr; } .side { position: static; height: auto; display: flex; overflow-x: auto; padding: 8px; border-right: 0; border-bottom: 1px solid var(--border); }
  .brand { display: none; } .grid2 { grid-template-columns: 1fr; } main { padding: 16px; } }
</style></head>
<body>
<div class="shell">
  <nav class="side" aria-label="주 메뉴"><div class="brand">모아스토어</div>
    <a href="#" aria-current="page">대시보드</a><a href="#">주문</a><a href="#">상품</a><a href="#">고객</a></nav>
  <div>
    <header class="top"><h1>매출 현황</h1>
      <label>기간 <select id="range"><option value="3">3개월</option><option value="6" selected>6개월</option><option value="0">빈 상태 테스트</option></select></label></header>
    <main>
      <section class="kpis" id="kpis" aria-live="polite"></section>
      <section class="grid2">
        <div class="card chart"><h2>월별 매출 추이</h2><div id="chart"></div></div>
        <div class="card"><h2>카테고리 비중</h2><div id="share"></div></div>
      </section>
      <section class="card"><h2>최근 주문</h2><div id="tbl"></div></section>
    </main>
  </div>
</div>
<script>
// sample data
const DATA = {
  months: ['4월', '5월', '6월', '7월', '8월', '9월'],
  sales: [12400000, 15800000, 14100000, 19600000, 22300000, 26800000],
  share: [['의류', 42], ['잡화', 27], ['뷰티', 19], ['기타', 12]],
  orders: [
    { id: 'A-1042', name: '김서연', item: '린넨 셔츠', amount: 59000, date: '2025-09-28' },
    { id: 'A-1041', name: '이준호', item: '캔버스 백팩', amount: 89000, date: '2025-09-27' },
    { id: 'A-1040', name: '박지민', item: '시카 크림 50ml', amount: 32000, date: '2025-09-27' },
  ],
};
const won = new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 });
const pct = new Intl.NumberFormat('ko-KR', { style: 'percent', maximumFractionDigits: 1, signDisplay: 'exceptZero' });
const $ = (id) => document.getElementById(id);
const COLORS = ['#2563eb', '#f59e0b', '#10b981', '#8b5cf6'];

function kpi(title, value, delta) {
  const cls = delta >= 0 ? 'up' : 'down';
  const arrow = delta >= 0 ? '▲ ' : '▼ ';
  return '<div class="card"><h2>' + title + '</h2><span class="val">' + value + '</span><span class="chip ' + cls + '">' + arrow + pct.format(delta) + '</span></div>';
}
function renderKpis(n) {
  const s = DATA.sales.slice(-n);
  const total = s.reduce((a, b) => a + b, 0);
  const last = s[s.length - 1], prev = s[s.length - 2] || last;
  $('kpis').innerHTML = kpi('매출', won.format(last), last / prev - 1) + kpi('기간 합계', compact.format(total) + '원', 0.082) +
    kpi('주문 수', '655건', 0.21) + kpi('환불률', '1.8%', -0.004);
}
function renderChart(n) {
  const labels = DATA.months.slice(-n), vals = DATA.sales.slice(-n);
  const W = 560, H = 260, m = { l: 48, r: 12, t: 12, b: 28 };
  const max = Math.ceil(Math.max(...vals) / 5000000) * 5000000;
  const x = (i) => m.l + (i * (W - m.l - m.r)) / (vals.length - 1);
  const y = (v) => m.t + (H - m.t - m.b) * (1 - v / max);
  let g = '';
  for (let i = 0; i <= 4; i++) {
    const v = (max / 4) * i;
    g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="var(--grid)"/><text x="' + (m.l - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + compact.format(v) + '</text>';
  }
  const pts = vals.map((v, i) => x(i) + ',' + y(v)).join(' ');
  const area = 'M' + x(0) + ',' + y(0) + ' L' + pts.replace(/ /g, ' L') + ' L' + x(vals.length - 1) + ',' + y(0) + ' Z';
  const dots = vals.map((v, i) => '<circle cx="' + x(i) + '" cy="' + y(v) + '" r="4" fill="var(--surface)" stroke="#2563eb" stroke-width="2.5"><title>' + labels[i] + ' ' + won.format(v) + '</title></circle><text x="' + x(i) + '" y="' + (H - 8) + '" text-anchor="middle">' + labels[i] + '</text>').join('');
  $('chart').innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="월별 매출 선 차트, 최근 ' + n + '개월"><path d="' + area + '" fill="#2563eb" fill-opacity=".1"/>' + g +
    '<polyline points="' + pts + '" fill="none" stroke="#2563eb" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>' + dots + '</svg>';
}
function renderShare() {
  const tot = DATA.share.reduce((a, s) => a + s[1], 0);
  $('share').innerHTML = DATA.share.map((s, i) => '<div style="margin:0 0 12px"><div style="display:flex;justify-content:space-between"><span>' + s[0] + '</span><b>' + Math.round((s[1] / tot) * 100) + '%</b></div>' +
    '<div style="height:8px;border-radius:4px;background:var(--grid)"><div style="height:8px;border-radius:4px;width:' + (s[1] / tot) * 100 + '%;background:' + COLORS[i] + '"></div></div></div>').join('');
}
let sortKey = 'date', sortDir = 'desc';
function renderTable() {
  const k = sortDir === 'asc' ? 1 : -1;
  const rows = [...DATA.orders].sort((a, b) => (typeof a[sortKey] === 'number' ? a[sortKey] - b[sortKey] : String(a[sortKey]).localeCompare(String(b[sortKey]), 'ko')) * k);
  if (!rows.length) { $('tbl').innerHTML = '<div class="empty">아직 주문이 없어요.<br>첫 주문이 들어오면 여기에 표시됩니다.</div>'; return; }
  const cols = [['id', '주문번호'], ['name', '고객'], ['item', '상품'], ['amount', '금액'], ['date', '주문일']];
  const th = cols.map((c) => '<th class="' + (c[0] === 'amount' ? 'n' : '') + '" aria-sort="' + (sortKey === c[0] ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none') + '"><button data-k="' + c[0] + '">' + c[1] + (sortKey === c[0] ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '') + '</button></th>').join('');
  const body = rows.map((r) => '<tr><td>' + r.id + '</td><td>' + r.name + '</td><td>' + r.item + '</td><td class="n">' + won.format(r.amount) + '</td><td>' + r.date + '</td></tr>').join('');
  $('tbl').innerHTML = '<div class="wrap"><table><thead><tr>' + th + '</tr></thead><tbody>' + body + '</tbody></table></div>';
}
$('tbl').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-k]');
  if (!b) return;
  sortDir = sortKey === b.dataset.k && sortDir === 'asc' ? 'desc' : 'asc';
  sortKey = b.dataset.k;
  renderTable();
});
function load(n) {
  $('kpis').innerHTML = '<div class="card"><div class="skel" style="width:50%"></div><div class="skel" style="height:2em;margin-top:12px"></div></div>';
  setTimeout(() => {
    if (n === 0) {
      $('kpis').innerHTML = '<div class="card empty" style="grid-column:1/-1">선택한 기간에 데이터가 없어요. 기간을 바꿔 보세요.</div>';
      $('chart').innerHTML = '<div class="empty">표시할 데이터가 없어요</div>';
      return;
    }
    renderKpis(n); renderChart(n); renderShare(); renderTable();
  }, 400);
}
$('range').addEventListener('change', (e) => load(Number(e.target.value)));
load(6);
</script>
</body></html>
```
Notes: chip arrows keep status readable without color. Swap the setTimeout for a real `fetch(...)` and render an error card with a "다시 시도" button on failure.
