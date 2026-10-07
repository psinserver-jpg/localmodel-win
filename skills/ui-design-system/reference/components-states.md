---
name: components-states
description: Paste-ready CSS and JS for inputs, cards, badges, modal dialog, toasts, tables, tabs, and spinner/skeleton with every state (hover, focus-visible, active, disabled, loading, error, empty).
triggers: [input, form field, text field, select, checkbox, modal, dialog, toast, snackbar, table, tabs, tab panel, badge, chip, spinner, skeleton, empty state, error state, loading state, disabled, 입력창, 폼, 모달, 토스트, 테이블, 표, 탭, 뱃지, 스피너, 로딩, 빈 상태, 에러 상태, 비활성]
---
# Components with all states
Requires the tokens from `tokens-and-base.md`. Example copy is Korean; translate to the user's language.

## Input + field message
```html
<div class="field">
  <label for="email">이메일</label>
  <input id="email" type="email" autocomplete="email" placeholder="name@company.com" aria-describedby="email-msg">
  <p class="field__msg" id="email-msg">로그인에 사용하는 주소를 입력해 주세요.</p>
</div>
```
```css
.field { display: grid; gap: var(--space-2); margin-bottom: var(--space-4); }
.field label { font-weight: 600; font-size: var(--fs-sm); }
.field input, .field select, .field textarea {
  min-height: var(--control-h); padding: 0 var(--control-px); font-size: 1rem;
  background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}
.field textarea { padding-block: var(--space-3); min-height: 7rem; resize: vertical; }
.field input::placeholder { color: var(--text-faint); }
.field input:hover { border-color: var(--text-muted); }
.field input:focus-visible { outline: none; border-color: var(--primary); box-shadow: var(--ring); }
.field input:disabled { background: var(--surface-2); color: var(--text-faint); cursor: not-allowed; }
.field__msg { margin: 0; font-size: var(--fs-sm); color: var(--text-muted); }
.field:has(input[aria-invalid="true"]) input { border-color: var(--danger); }
.field:has(input[aria-invalid="true"]) .field__msg { color: var(--danger); }
.field:has(input[aria-invalid="true"]) .field__msg::before { content: "\26A0\FE0E "; }
```
Fallback for no `:has()`: put the class `.is-error` on `.field` from JS and style `.field.is-error input`.

## Button variants and loading
```css
.btn--secondary { background: var(--primary-soft); color: var(--primary); }
.btn--danger { background: var(--danger); color: var(--surface); }
.btn--sm { min-height: 36px; padding: 0 var(--space-3); font-size: var(--fs-sm); }
.btn[aria-busy="true"] { position: relative; color: transparent; pointer-events: none; }
.btn[aria-busy="true"]::after {
  content: ""; position: absolute; inset: 0; margin: auto; width: 1.1rem; height: 1.1rem;
  border: 2px solid var(--on-primary); border-right-color: transparent; border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```
JS: `btn.setAttribute('aria-busy','true'); btn.disabled = true; await save(); btn.removeAttribute('aria-busy'); btn.disabled = false;`

## Badge / chip
```css
.badge { display: inline-flex; align-items: center; gap: .35em; padding: .15rem .6rem; border-radius: var(--radius-full);
  font-size: .8125rem; font-weight: 600; background: var(--surface-2); color: var(--text-muted); }
.badge--success { background: var(--success-soft); color: var(--success); }
.badge--danger { background: var(--danger-soft); color: var(--danger); }
.badge--warning { background: var(--warning-soft); color: var(--warning); }
.badge--info { background: var(--info-soft); color: var(--info); }
.badge--dot::before { content: ""; width: .5em; height: .5em; border-radius: 50%; background: currentColor; }
```

## Modal with native dialog
```html
<button class="btn" id="openModal" type="button">삭제하기</button>
<dialog id="confirm" aria-labelledby="confirm-title">
  <form method="dialog">
    <h2 id="confirm-title">이 항목을 삭제할까요?</h2>
    <p>삭제하면 되돌릴 수 없어요.</p>
    <div class="dialog__actions">
      <button class="btn btn--ghost" value="cancel">취소</button>
      <button class="btn btn--danger" value="ok">삭제</button>
    </div>
  </form>
</dialog>
<script>
const dlg = document.getElementById('confirm');
document.getElementById('openModal').addEventListener('click', () => dlg.showModal());
dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close('cancel'); });
dlg.addEventListener('close', () => { if (dlg.returnValue === 'ok') console.log('deleted'); });
</script>
```
```css
dialog { border: 0; padding: var(--space-6); border-radius: var(--radius-lg); background: var(--surface); color: var(--text);
  box-shadow: var(--shadow-3); width: min(100% - 2rem, 28rem); overscroll-behavior: contain; }
dialog::backdrop { background: var(--overlay); backdrop-filter: blur(2px); }
dialog[open] { animation: pop var(--dur-slow) var(--ease); }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(.98); } }
.dialog__actions { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-6); }
body:has(dialog[open]) { overflow: hidden; }
```
`<dialog>` gives focus trap, Esc, and focus return for free; do not rebuild it with divs.

## Toast
```html
<div id="toasts" class="toasts" role="status" aria-live="polite"></div>
<script>
function toast(message, kind = 'info', ms = 4000) {
  const box = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast toast--' + kind;
  el.textContent = message;
  box.append(el);
  setTimeout(() => { el.classList.add('is-leaving'); setTimeout(() => el.remove(), 200); }, ms);
}
toast('저장했어요', 'success');
</script>
```
```css
.toasts { position: fixed; inset: auto 1rem 1rem auto; z-index: var(--z-toast); display: grid; gap: var(--space-2); max-width: min(24rem, calc(100vw - 2rem)); }
.toast { padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm); background: var(--text); color: var(--bg);
  box-shadow: var(--shadow-2); border-left: 4px solid var(--primary); animation: toast-in var(--dur) var(--ease); }
.toast--success { border-left-color: var(--success); }
.toast--danger { border-left-color: var(--danger); }
.toast.is-leaving { opacity: 0; transform: translateX(8px); transition: all 200ms var(--ease); }
@keyframes toast-in { from { opacity: 0; transform: translateY(8px); } }
```
Errors that need action should stay until dismissed (ms = 0 and add a close button).

## Table with empty state
```html
<div class="table-wrap">
  <table class="table">
    <thead><tr><th scope="col">주문번호</th><th scope="col">상태</th><th scope="col" class="num">금액</th></tr></thead>
    <tbody>
      <tr><td>#20418</td><td><span class="badge badge--success badge--dot">배송 완료</span></td><td class="num">38,000원</td></tr>
      <tr><td>#20419</td><td><span class="badge badge--warning badge--dot">결제 대기</span></td><td class="num">124,500원</td></tr>
    </tbody>
  </table>
</div>
<p class="empty" hidden>아직 주문이 없어요. 첫 주문을 받으면 여기에 표시돼요.</p>
```
```css
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface); }
.table { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); }
.table th, .table td { padding: var(--space-3) var(--space-4); text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
.table th { position: sticky; top: 0; background: var(--surface-2); font-weight: 600; color: var(--text-muted); }
.table tbody tr:hover { background: var(--surface-2); }
.table tbody tr:last-child td { border-bottom: 0; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.empty { text-align: center; padding: var(--space-12) var(--space-4); color: var(--text-muted); }
```

## Tabs (keyboard accessible)
```html
<div class="tabs">
  <div role="tablist" aria-label="설정">
    <button role="tab" id="t1" aria-controls="p1" aria-selected="true">계정</button>
    <button role="tab" id="t2" aria-controls="p2" aria-selected="false" tabindex="-1">알림</button>
  </div>
  <div role="tabpanel" id="p1" aria-labelledby="t1">계정 설정 내용</div>
  <div role="tabpanel" id="p2" aria-labelledby="t2" hidden>알림 설정 내용</div>
</div>
<script>
document.querySelectorAll('[role="tablist"]').forEach((list) => {
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const select = (tab) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
    tab.focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => select(t));
    t.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') select(tabs[(i + 1) % tabs.length]);
      if (e.key === 'ArrowLeft') select(tabs[(i - 1 + tabs.length) % tabs.length]);
    });
  });
});
</script>
```
```css
[role="tablist"] { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--border); overflow-x: auto; }
[role="tab"] { min-height: var(--control-h); padding: 0 var(--space-4); background: none; border: 0; border-bottom: 2px solid transparent;
  color: var(--text-muted); font-weight: 600; cursor: pointer; white-space: nowrap; }
[role="tab"]:hover { color: var(--text); }
[role="tab"][aria-selected="true"] { color: var(--primary); border-bottom-color: var(--primary); }
[role="tabpanel"] { padding: var(--space-6) 0; }
```

## Skeleton
```css
.skeleton { background: linear-gradient(90deg, var(--surface-2) 25%, var(--surface-3) 50%, var(--surface-2) 75%);
  background-size: 200% 100%; animation: shimmer 1.4s linear infinite; border-radius: var(--radius-sm); min-height: 1em; }
@keyframes shimmer { to { background-position: -200% 0; } }
```
Use skeletons for content areas > 400ms; spinners for button actions. Reserve the final size to avoid layout shift.
