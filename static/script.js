/* ═══════════════════════════════════════════
   SpendSense — script.js
   Global: mobile sidebar, stat animations,
           calculator widget, flash dismiss
═══════════════════════════════════════════ */

/* ── Mobile sidebar ───────────────────────── */
document.addEventListener('click', e => {
  const sb = document.getElementById('sidebar');
  if (sb && sb.classList.contains('open')
      && !sb.contains(e.target)
      && !e.target.closest('.hamburger')) {
    sb.classList.remove('open');
  }
});

/* ── Page-load animations ─────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  /* stat cards stagger in */
  document.querySelectorAll('.stat-card').forEach((c, i) => {
    c.style.opacity    = '0';
    c.style.transform  = 'translateY(14px)';
    c.style.transition = `opacity .35s ease ${i * .08}s, transform .35s ease ${i * .08}s`;
    requestAnimationFrame(() => {
      c.style.opacity   = '1';
      c.style.transform = 'translateY(0)';
    });
  });

  /* auto-dismiss flash messages */
  document.querySelectorAll('.flash').forEach(f => {
    setTimeout(() => { f.style.opacity = '0'; f.style.transition = 'opacity .4s'; }, 4000);
    setTimeout(() => f.remove(), 4500);
  });
});

/* ══════════════════════════════════════════
   CALCULATOR
══════════════════════════════════════════ */
let calcState = {
  display: '0',
  expr:    '',
  op:      null,
  prev:    null,
  fresh:   false,   // next digit starts a new number
  hasResult: false,
};

function toggleCalculator() {
  const w = document.getElementById('calcWidget');
  if (!w) return;
  const isOpen = w.classList.contains('open');
  if (isOpen) {
    w.classList.remove('open');
    /* brief hide animation */
    w.style.animation = 'none';
    w.style.display   = 'none';
  } else {
    w.style.display   = 'flex';
    w.style.animation = '';
    /* force reflow for animation */
    void w.offsetWidth;
    w.classList.add('open');
  }

  /* highlight nav button */
  const btn = document.getElementById('calcNavBtn');
  if (btn) btn.style.color = isOpen ? '' : 'var(--cyan)';
}

function calcUpdateDisplay() {
  const disp  = document.getElementById('calcDisplay');
  const expr  = document.getElementById('calcExpr');
  if (!disp) return;

  disp.textContent = calcState.display;
  disp.className   = 'calc-display';
  if (calcState.hasResult) disp.classList.add('result');
  if (calcState.display === 'Error') disp.classList.add('error');

  if (expr) {
    expr.textContent = calcState.expr || '\u00a0';
  }
}

function calcInput(key) {
  const s = calcState;

  /* ── AC / Clear ── */
  if (key === 'AC' || key === 'C') {
    calcState = { display:'0', expr:'', op:null, prev:null, fresh:false, hasResult:false };
    calcUpdateDisplay(); return;
  }

  /* ── Toggle sign ── */
  if (key === '+/-') {
    if (s.display !== '0' && s.display !== 'Error') {
      s.display = s.display.startsWith('-') ? s.display.slice(1) : '-' + s.display;
    }
    calcUpdateDisplay(); return;
  }

  /* ── Percent ── */
  if (key === '%') {
    const n = parseFloat(s.display);
    if (!isNaN(n)) {
      s.display = String(n / 100);
      s.hasResult = false;
    }
    calcUpdateDisplay(); return;
  }

  /* ── Decimal dot ── */
  if (key === '.') {
    if (s.fresh) { s.display = '0.'; s.fresh = false; }
    else if (!s.display.includes('.')) { s.display += '.'; }
    calcUpdateDisplay(); return;
  }

  /* ── Digits ── */
  if ('0123456789'.includes(key)) {
    if (s.hasResult) {
      /* after = pressed, start fresh */
      s.display = key; s.hasResult = false; s.expr = '';
    } else if (s.fresh || s.display === '0') {
      s.display = key; s.fresh = false;
    } else {
      if (s.display.replace('-','').length < 14) s.display += key;
    }
    calcUpdateDisplay(); return;
  }

  /* ── Operators: ÷ × − + ── */
  const opMap = { '÷':'/', '×':'*', '−':'-', '+':'+' };
  if (opMap[key] !== undefined) {
    const cur = parseFloat(s.display);
    if (s.op && s.prev !== null && !s.fresh) {
      /* chain calculation */
      const res = doCalc(s.prev, s.op, cur);
      s.display  = formatResult(res);
      s.prev     = res;
    } else {
      s.prev = cur;
    }
    s.op         = opMap[key];
    s.expr       = `${s.display} ${key}`;
    s.fresh      = true;
    s.hasResult  = false;
    calcUpdateDisplay(); return;
  }

  /* ── Equals ── */
  if (key === '=') {
    if (s.op === null || s.prev === null) { calcUpdateDisplay(); return; }
    const cur = parseFloat(s.display);
    const res = doCalc(s.prev, s.op, cur);
    s.expr      = `${s.prev} ${Object.keys(opMap).find(k=>opMap[k]===s.op)||s.op} ${cur} =`;
    s.display   = formatResult(res);
    s.op        = null;
    s.prev      = null;
    s.fresh     = true;
    s.hasResult = true;
    calcUpdateDisplay(); return;
  }
}

function doCalc(a, op, b) {
  switch (op) {
    case '+': return a + b;
    case '-': return a - b;
    case '*': return a * b;
    case '/': return b === 0 ? 'Error' : a / b;
    default:  return b;
  }
}

function formatResult(val) {
  if (val === 'Error') return 'Error';
  if (isNaN(val) || !isFinite(val)) return 'Error';
  /* avoid floating point mess like 0.1+0.2 */
  const rounded = Math.round(val * 1e10) / 1e10;
  return String(rounded);
}

/* Keyboard support for calculator */
document.addEventListener('keydown', e => {
  const w = document.getElementById('calcWidget');
  if (!w || !w.classList.contains('open')) return;
  /* don't hijack input fields */
  if (['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) return;

  const keyMap = {
    '0':'0','1':'1','2':'2','3':'3','4':'4',
    '5':'5','6':'6','7':'7','8':'8','9':'9',
    '.':'.', ',':'.', 'Enter':'=', '=':'=',
    '+':'+', '-':'−', '*':'×', '/':'÷',
    'Backspace':'AC', 'Escape':'AC', '%':'%',
  };
  if (keyMap[e.key]) {
    e.preventDefault();
    calcInput(keyMap[e.key]);
  }
});

/* ── Draggable calculator ─────────────────── */
(function makeDraggable() {
  let dragging = false, ox = 0, oy = 0;
  document.addEventListener('mousedown', e => {
    const handle = document.getElementById('calcDragHandle');
    if (!handle || !handle.contains(e.target)) return;
    const w = document.getElementById('calcWidget');
    if (!w || !w.classList.contains('open')) return;
    dragging = true;
    const rect = w.getBoundingClientRect();
    ox = e.clientX - rect.left;
    oy = e.clientY - rect.top;
    w.style.transition = 'none';
    e.preventDefault();
  });
  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const w = document.getElementById('calcWidget');
    if (!w) return;
    const x = Math.max(0, Math.min(e.clientX - ox, window.innerWidth  - w.offsetWidth));
    const y = Math.max(0, Math.min(e.clientY - oy, window.innerHeight - w.offsetHeight));
    w.style.left   = x + 'px';
    w.style.top    = y + 'px';
    w.style.bottom = 'auto';
    w.style.right  = 'auto';
  });
  document.addEventListener('mouseup', () => { dragging = false; });
})();
