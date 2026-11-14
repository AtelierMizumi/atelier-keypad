// Revision switcher and the rapid-trigger demo.
const REVS = {
  0: { model: 'assets/atelier6k.glb', poster: 'assets/pcb-iso.png' },
  1: { model: 'assets/atelier6k-rev1.glb', poster: 'assets/rev1-pcb-top.png' },
  2: { model: null },
};
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const show = document.querySelector('.show');
const model = document.getElementById('model');
const concept = document.getElementById('concept');
const numeral = document.querySelector('.numeral');

function wake(article) {
  // Heavy embeds load only when their revision is opened.
  for (const f of article.querySelectorAll('iframe[data-src]')) {
    f.src = f.dataset.src;
    f.removeAttribute('data-src');
  }
  for (const k of article.querySelectorAll('div[data-sources]')) {
    const fresh = document.createElement('kicanvas-embed');
    fresh.className = k.className;
    fresh.setAttribute('controls', 'full');
    fresh.setAttribute('theme', 'kicad');
    for (const src of k.dataset.sources.split(' ')) {
      const s = document.createElement('kicanvas-source');
      s.setAttribute('src', src);
      fresh.appendChild(s);
    }
    k.replaceWith(fresh);
  }
}

function select(rev, animate) {
  if (!(rev in REVS)) rev = '0';
  document.body.dataset.rev = rev;
  numeral.textContent = rev;
  for (const a of document.querySelectorAll('.menu a')) a.setAttribute('aria-current', String(a.dataset.rev === rev));
  for (const art of document.querySelectorAll('article.rev')) {
    const on = art.dataset.rev === rev;
    art.hidden = !on;
    if (on) wake(art);
  }
  const r = REVS[rev];
  model.hidden = !r.model;
  concept.hidden = !!r.model;
  if (r.model && model.getAttribute('src') !== r.model) {
    model.setAttribute('poster', r.poster);
    model.setAttribute('src', r.model);
  }
  if (animate && !reduced) {
    show.classList.remove('wipe');
    void show.offsetWidth;
    show.classList.add('wipe');
  }
}

const fromHash = () => (location.hash.match(/^#rev([0-2])$/) || [])[1] || '0';
addEventListener('hashchange', () => select(fromHash(), true));
select(fromHash(), false);

// ------------------------------------------------------------ rapid trigger
// Two ways to decide when a key is pressed, replayed over the same travel trace:
//  fixed point - press below 2.0 mm, release above 1.8 mm (a mechanical switch);
//  rapid       - press after moving down by `sens`, release after moving up by `sens`.
const svg = document.querySelector('#rt svg');
const depthIn = document.getElementById('rt-depth');
const sensIn = document.getElementById('rt-sens');
const out = document.getElementById('rt-read');
const W = 640, H = 220, L = 44, R = 10, T = 14, B = 26, MAX = 4, N = 160;
const FIX_ON = 2.0, FIX_OFF = 1.8;
const x = (i) => L + (i / (N - 1)) * (W - L - R);
const y = (d) => T + (d / MAX) * (H - T - B);
const NS = 'http://www.w3.org/2000/svg';
const el = (name, attrs, text) => {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text) e.textContent = text;
  return e;
};

// A burst of osu! stream taps: the finger never lifts past the fixed reset point.
const trace = [];
const ease = (a, b, n) => { for (let i = 1; i <= n; i++) trace.push(a + (b - a) * (1 - Math.cos(Math.PI * i / n)) / 2); };
trace.push(0); ease(0, 3.6, 10);
for (const up of [2.3, 2.5, 2.2, 2.6]) { ease(3.6, up, 8); ease(up, 3.6, 8); }
ease(3.6, 0, 14);
while (trace.length < N) trace.unshift(0);
trace.splice(0, trace.length - N);

const grid = svg.querySelector('.rt-grid');
for (let d = 0; d <= MAX; d++) {
  grid.append(el('line', { x1: L, x2: W - R, y1: y(d), y2: y(d) }));
  grid.append(el('text', { x: 6, y: y(d) + 4 }, `${d} mm`));
}
grid.append(el('line', { x1: L, x2: W - R, y1: y(FIX_ON), y2: y(FIX_ON), style: 'stroke: var(--warn); stroke-opacity:.5' }));
grid.append(el('text', { x: L + 6, y: y(FIX_ON) - 6, style: 'fill: var(--warn)' }, 'fixed actuation 2.0 mm'));

function replay(sens) {
  const ev = [];
  let fixed = false, rapid = false, peak = 0, valley = 0;
  trace.forEach((d, i) => {
    if (!fixed && d >= FIX_ON) { fixed = true; ev.push({ i, kind: 'fixed', on: true }); }
    else if (fixed && d <= FIX_OFF) { fixed = false; ev.push({ i, kind: 'fixed', on: false }); }
    if (!rapid) {
      valley = Math.min(valley, d);
      if (d - valley >= sens && d > 0.1) { rapid = true; peak = d; ev.push({ i, kind: 'rapid', on: true }); }
    } else {
      peak = Math.max(peak, d);
      if (peak - d >= sens || d <= 0.05) { rapid = false; valley = d; ev.push({ i, kind: 'rapid', on: false }); }
    }
  });
  return { ev, fixed, rapid };
}

function draw() {
  const sens = parseFloat(sensIn.value);
  svg.querySelector('.rt-travel').setAttribute('d', trace.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d).toFixed(1)}`).join(''));
  const marks = svg.querySelector('.rt-marks');
  marks.replaceChildren();
  const { ev, fixed, rapid } = replay(sens);
  let presses = { fixed: 0, rapid: 0 };
  for (const e of ev) {
    if (e.on) presses[e.kind]++;
    const off = e.kind === 'fixed' ? 0 : 6;
    marks.append(el('line', { class: e.kind, x1: x(e.i), x2: x(e.i), y1: T + off, y2: H - B }));
    if (e.on) marks.append(el('text', { x: x(e.i) + 3, y: e.kind === 'fixed' ? H - B + 16 : T + 10, style: `fill: var(--${e.kind === 'fixed' ? 'warn' : 'cyan'})` }, '▼'));
  }
  const n = (k) => `${k} ${k === 1 ? 'press' : 'presses'}`;
  out.textContent = `Rapid trigger: ${n(presses.rapid)}, now ${rapid ? 'down' : 'up'}. Fixed point: ${n(presses.fixed)}, now ${fixed ? 'down' : 'up'}.`;
}

let live = null;
depthIn.addEventListener('input', () => {
  if (live) return;
  live = setInterval(() => {
    trace.push(parseFloat(depthIn.value));
    trace.shift();
    draw();
  }, 40);
});
sensIn.addEventListener('change', draw);
draw();
