/* OmniHub demo — wires the static UI to the live FastAPI backend.
 *
 * Architecture:
 *   - Two views in one document, toggled by setView().
 *   - Home view fetches /api/catalog and renders 25 picker tiles.
 *   - Run view connects to /api/run/stream (Server-Sent Events) and
 *     advances the 5-stage animated pipeline as events arrive.
 *
 * The backend's stream is paced (~0.5s, 6s, 5s, 4s, 4s, 2.5s) so the
 * animation timing is server-driven — we just react to events.
 */

// -------- Config --------
const API_BASE = ''; // same origin (FastAPI serves the static demo + /api together)

// Production data-pipeline mapping. Surfaced in the Ingest stage so the
// pitcher can point at each source and credibly claim "this is how we get
// the data." For the prototype the data is synthetic, but the connector
// taxonomy mirrors what the MVP pipeline will use.
const CONNECTORS = {
  // External
  'X / Twitter':           'X API v2 · Apify scraper',
  'Reddit':                'Reddit Official API',
  'Hacker News':           'Algolia HN Search API',
  'App Store reviews':     'App Store Connect API',
  'Google Play reviews':   'Play Console feedback API',
  'GitHub Issues':         'GitHub App webhook',
  'GitHub Issues (own)':   'GitHub App webhook',
  'Walmart Connect Forum': 'Forum scraper · weekly digest',
  'Developer Discord':     'Discord bot · webhook events',
  'G2 reviews':            'G2 Reviews export',
  // Internal
  'Zendesk':               'Zendesk webhook subscription',
  'Intercom':              'Intercom Events API',
  'Slack (internal)':      'Slack OAuth · Events API',
  'Jira (dev logs)':       'Jira webhook · REST API',
  'Datadog (alerts)':      'Datadog webhook integration',
  'Trust & Safety':        'Internal T&S queue',
  'Risk & Fraud':          'Risk pipeline · Kafka topic',
  'Compliance & Privacy':  'OneTrust · GRC webhook',
};
function connectorFor(name) { return CONNECTORS[name] || 'API integration'; }

// Stable hash → "12s ago" / "1m 4s ago". Same source name + count always
// produces the same value, so replays don't jitter the freshness display.
function fetchedAgoFor(sourceName, count) {
  let h = 17;
  const s = sourceName + ':' + count;
  for (let i = 0; i < s.length; i++) h = ((h * 31) + s.charCodeAt(i)) | 0;
  const sec = 4 + (Math.abs(h) % 175);  // 4..178s
  if (sec < 60) return sec + 's ago';
  return Math.floor(sec / 60) + 'm ' + (sec % 60) + 's ago';
}

// -------- DOM helpers --------
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const el = (tag, attrs, ...children) => {
  const node = document.createElement(tag);
  // attrs may be null/undefined (when the call site only wants children) — guard.
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') node.className = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
  }
  for (const c of children) {
    if (c == null) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
};

// -------- Animation utilities --------
const easeOutCubic = t => 1 - Math.pow(1 - t, 3);

function countUp(node, from, to, duration = 1100, decimals = 0) {
  const start = performance.now();
  const diff = to - from;
  function frame(now) {
    const t = Math.min(1, (now - start) / duration);
    const v = from + diff * easeOutCubic(t);
    node.textContent = decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString();
    if (t < 1) requestAnimationFrame(frame);
    else node.textContent = decimals ? to.toFixed(decimals) : Math.round(to).toLocaleString();
  }
  requestAnimationFrame(frame);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// -------- View routing --------
const views = { home: $('#home'), run: $('#run') };
function setView(name) {
  for (const [k, node] of Object.entries(views)) {
    node.classList.toggle('active', k === name);
    if (name === 'home' && k === 'home') node.style.display = '';
    if (name === 'run'  && k === 'home') node.style.display = 'none';
    if (name === 'run'  && k === 'run')  node.style.display = '';
    if (name === 'home' && k === 'run')  node.style.display = 'none';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// -------- Backend health probe (truthful pill) --------
async function probeBackend() {
  const pill     = $('#backendPill');
  const pillText = $('#backendPillText');
  try {
    const r = await fetch(`${API_BASE}/api/health`, { cache: 'no-store' });
    if (!r.ok) throw new Error('health ' + r.status);
    const j = await r.json();
    pill.dataset.state = 'ok';
    pillText.textContent = 'Backend connected · v' + (j.version || '?');
    return true;
  } catch (err) {
    pill.dataset.state = 'down';
    pillText.textContent = 'Backend unreachable';
    return false;
  }
}

// -------- Catalog (home view) --------
async function loadCatalog() {
  renderSkeletonTiles(15);
  let companies;
  try {
    const r = await fetch(`${API_BASE}/api/catalog`);
    if (!r.ok) throw new Error(`catalog HTTP ${r.status}`);
    companies = (await r.json()).companies;
  } catch (err) {
    const pageOrigin = location.origin === 'null' ? location.href : location.origin;
    const isFile = location.protocol === 'file:';
    $('#tileGrid').innerHTML = `
      <div style="grid-column:1/-1;background:#FEE2E2;border:1px solid #FCA5A5;border-radius:14px;padding:22px 26px;color:#991B1B;line-height:1.6;font-size:13.5px;">
        <div style="font-weight:700;margin-bottom:8px;font-size:15px;">Can't reach the OmniHub backend.</div>
        <div>This page is loaded from <code style="background:#FECACA;padding:2px 6px;border-radius:4px;font-family:var(--mono);">${pageOrigin}</code>${isFile ? ' (a local file — JavaScript fetch() can\'t reach a server from here)' : ''}.</div>
        <div style="margin-top:8px;">The API lives at <code style="background:#FECACA;padding:2px 6px;border-radius:4px;font-family:var(--mono);">http://127.0.0.1:8000/api/...</code>. Open <a href="http://127.0.0.1:8000/" style="color:#7F1D1D;text-decoration:underline;font-weight:600;">http://127.0.0.1:8000/</a> in your browser instead — that's the URL that has both the demo UI and the API on the same origin.</div>
      </div>`;
    console.error('catalog fetch failed:', err);
    return;
  }
  // Rendering is intentionally outside the network try/catch so render bugs
  // surface as themselves, not as fake "backend unreachable" messages.
  try {
    renderCatalog(companies);
  } catch (err) {
    $('#tileGrid').innerHTML = `
      <div style="grid-column:1/-1;background:#FEF3C7;border:1px solid #FCD34D;border-radius:14px;padding:22px 26px;color:#92400E;line-height:1.6;font-size:13.5px;">
        <div style="font-weight:700;margin-bottom:8px;font-size:15px;">Render error</div>
        <div>The catalog loaded fine, but the tile renderer threw: <code style="background:#FDE68A;padding:2px 6px;border-radius:4px;font-family:var(--mono);">${String(err)}</code></div>
      </div>`;
    console.error('catalog render failed:', err);
  }
}

function renderSkeletonTiles(n) {
  const grid = $('#tileGrid');
  grid.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const tile = el('div', { class: 'tile skeleton-tile' },
      el('div', { class: 'skeleton', style: { width: '42px', height: '42px', borderRadius: '10px' } }),
      el('div', { class: 'skeleton', style: { height: '20px', width: '80%' } }),
      el('div', { class: 'skeleton', style: { height: '14px', width: '60%' } }),
      el('div', { class: 'skeleton', style: { height: '40px' } }),
    );
    grid.appendChild(tile);
  }
}

function renderCatalog(companies) {
  const grid = $('#tileGrid');
  grid.innerHTML = '';
  for (const c of companies) {
    const tile = el('button', {
      class: 'tile',
      type: 'button',
      onclick: () => startRun(c.domain),
    },
      el('div', { class: 'tile-mark', style: { background: c.mark.bg } }, c.mark.char),
      el('div', null,
        el('div', { class: 'tile-name' }, c.name),
        el('div', { class: 'tile-tag' }, c.tagline),
      ),
      el('div', { class: 'tile-mini' },
        el('div', null, el('b', null, c.top_score_preview.toFixed(1)), 'top RICE++'),
        el('div', null, el('b', null, c.industry), 'industry'),
      ),
      el('span', { class: 'go' }, '→'),
    );
    grid.appendChild(tile);
  }
}

// -------- Run flow --------
let currentEventSource = null;
let currentRun = null;

const STAGE_NAMES = ['Ingest', 'Cluster', 'Score', 'Recommend', 'Sync'];
const STAGE_TITLES = [
  '§ 01 · Omnichannel ingestion',
  '§ 02 · Theme clustering',
  '§ 03 · RICE++ scoring',
  '§ 04 · Recommended epic',
  '§ 05 · Sync to Jira / Confluence',
];

function startRun(domain) {
  domain = (domain || '').trim();
  if (!domain) return;

  // Reset run state
  resetRunUI();
  $('#domainPill').textContent = domain;
  setView('run');

  // Close any existing stream
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  const url = `${API_BASE}/api/run/stream?domain=${encodeURIComponent(domain)}`;
  const source = new EventSource(url);
  currentEventSource = source;

  source.addEventListener('company',   ev => handleCompany(JSON.parse(ev.data)));
  source.addEventListener('ingest',    ev => handleIngest(JSON.parse(ev.data)));
  source.addEventListener('cluster',   ev => handleCluster(JSON.parse(ev.data)));
  source.addEventListener('score',     ev => handleScore(JSON.parse(ev.data)));
  source.addEventListener('recommend', ev => handleRecommend(JSON.parse(ev.data)));
  source.addEventListener('sync',      ev => handleSync(JSON.parse(ev.data)));
  source.addEventListener('done',      ev => handleDone(JSON.parse(ev.data)));

  source.onerror = () => {
    // EventSource auto-retries; we close on completion via 'done'.
    if (source.readyState === EventSource.CLOSED) return;
  };
}

function resetRunUI() {
  // Stage rail
  $$('.stage-chip').forEach((c, i) => {
    c.classList.toggle('active', i === 0);
    c.classList.remove('done');
  });
  $$('.stage').forEach((s, i) => s.classList.toggle('active', i === 0));
  $('#boardTitle').textContent = STAGE_TITLES[0];
  $('#liveDot').classList.remove('idle');
  $('#liveDot').textContent = 'LIVE';
  $('#progText').textContent = '00 / 05';
  $('#progFill').style.width = '0%';
  $('#errorBanner').classList.remove('shown');
  $('#finale').classList.remove('shown');

  // Stage 1
  $('#sourceList').innerHTML = '';
  $('#stream').innerHTML = '';
  $('#counter').textContent = '0';
  $('#pctPos').textContent = '—';
  $('#pctNeu').textContent = '—';
  $('#pctNeg').textContent = '—';
  const hb = $('#healthBadge');
  if (hb) {
    hb.classList.remove('healthy');
    $('#healthText').textContent = 'awaiting feed…';
  }

  // Stage 2
  $('#galaxySvg').innerHTML = '';
  $('#epicList').innerHTML = '';

  // Stage 3
  $$('#riceBars .trackfill').forEach(f => f.style.width = '0%');
  $$('#riceBars .val').forEach(v => v.textContent = '0');
  $('#scoreNum').textContent = '0.0';
  $('#scoreBand').style.setProperty('--pct', '0%');
  $('#scoreVerdict').textContent = '—';
  $('#scoreTitle').textContent = '—';
  $('#scoreDesc').textContent = '—';

  // Stage 4
  $('#recTitle').textContent = '—';
  $('#recWhy').textContent = '—';
  $('#recReco').textContent = '—';
  $('#acceptList').innerHTML = '';
  $('#quoteList').innerHTML = '';

  // Stage 5
  ['jiraTicket', 'confTicket'].forEach(id => $('#' + id).classList.remove('created'));
  $('#jiraStatus').textContent = 'Pending sync…';
  $('#confStatus').textContent = 'Pending sync…';

  currentRun = { ingest: null, top_epic: null, sync: null };
}

function setStage(stageIndex, totalDone) {
  $$('.stage-chip').forEach((c, i) => {
    c.classList.toggle('active', i === stageIndex);
    c.classList.toggle('done', i < stageIndex);
  });
  $$('.stage').forEach((s, i) => s.classList.toggle('active', i === stageIndex));
  $('#boardTitle').textContent = STAGE_TITLES[stageIndex];
  $('#progText').textContent = `${String(totalDone).padStart(2, '0')} / 05`;
  $('#progFill').style.width = `${(totalDone / 5) * 100}%`;
}

// -------- Stage 1: Ingest --------
function handleCompany(co) {
  $('#coName').textContent = co.name;
  $('#coIndustry').textContent = co.industry;
  $('#tierPill').textContent = co.tier === 'catalog' ? 'tier · catalog' : 'tier · synthetic';
}

function handleIngest(ingest) {
  currentRun.ingest = ingest;

  // Sources — light up sequentially over ~5s. Each row shows the source
  // name + production connector ("via Reddit Official API") + freshness.
  const list = $('#sourceList');
  list.innerHTML = '';
  ingest.sources.forEach(src => {
    const li = el('li', null,
      el('span', { class: 'sd' }),
      el('div', { class: 'sn-block' },
        el('div', { class: 'sn-row' },
          el('span', { class: 'sn' }, src.name),
          el('span', { class: 'sc' }, '0'),
        ),
        el('div', { class: 'connector' },
          el('span', { class: 'sk' }, src.category),
          el('span', null, '· via ' + connectorFor(src.name)),
          el('span', { class: 'fetched' }, fetchedAgoFor(src.name, src.count)),
        ),
      ),
    );
    list.appendChild(li);
  });

  // Health badge — flip from "awaiting feed…" to "N/N healthy" as soon as
  // the ingest event has resolved a real source list.
  const n = ingest.sources.length;
  const healthBadge = $('#healthBadge');
  $('#healthText').textContent = `${n}/${n} healthy`;
  healthBadge.classList.add('healthy');
  // Stagger lighting + counter ramp
  const items = $$('#sourceList li');
  const totalDuration = 5500;
  items.forEach((li, i) => {
    const delay = (i * totalDuration) / Math.max(items.length, 1);
    setTimeout(() => {
      li.classList.add('lit');
      const target = ingest.sources[i].count;
      countUp($('.sc', li), 0, target, 900);
    }, delay);
  });

  // Master counter — ramps over the ingest stage's full duration
  countUp($('#counter'), 0, ingest.signal_count, totalDuration + 300);

  // Sentiment percentages — fill in after a brief pause
  setTimeout(() => {
    $('#pctPos').textContent = ingest.sentiment_pct.positive + '%';
    $('#pctNeu').textContent = ingest.sentiment_pct.neutral + '%';
    $('#pctNeg').textContent = ingest.sentiment_pct.negative + '%';
  }, 1100);

  // Live signal stream — prepend each sample on a stagger
  const stream = $('#stream');
  stream.innerHTML = '';
  const maxVisible = 8;
  const samples = ingest.stream_samples;
  // Spread the stream across the same window the counter is counting.
  const streamWindow = totalDuration - 300;
  const tick = streamWindow / Math.max(samples.length, 1);
  samples.forEach((s, i) => {
    setTimeout(() => {
      const sigEl = el('div', { class: `sig ${s.sentiment === 'positive' ? 'pos' : s.sentiment === 'negative' ? 'neg' : 'neu'}` },
        el('span', { class: 'src' }, s.source),
        el('span', { class: 'sent' }, s.sentiment === 'positive' ? '▲' : s.sentiment === 'negative' ? '▼' : '◆'),
        el('span', { class: 'txt' }, s.text),
        el('span', { class: 'ts' }, fakeTime(i)),
      );
      // Newest goes on top — column-reverse handles the visual order
      stream.appendChild(sigEl);
      // Trim
      while (stream.children.length > maxVisible) stream.removeChild(stream.firstChild);
    }, 200 + i * tick);
  });
}

function fakeTime(i) {
  // Realistic-looking timestamps, descending
  const base = new Date();
  base.setMinutes(base.getMinutes() - i);
  return base.toTimeString().slice(0, 5);
}

// -------- Stage 2: Cluster --------
function handleCluster(clusters) {
  setStage(1, 1);

  // Build a dot-galaxy: 130 dots seed in random positions, then fly to cluster centroids.
  const svg = $('#galaxySvg');
  svg.innerHTML = '';

  const W = 800, H = 500;
  const padding = 60;

  // Cluster centroids — top cluster gets the prominent left position
  const topIdx = clusters.findIndex(c => c.is_top);
  const ordered = clusters.slice();
  if (topIdx > 0) {
    const [topItem] = ordered.splice(topIdx, 1);
    ordered.unshift(topItem);
  }

  const centroids = ordered.map((c, i) => {
    if (i === 0) return { x: 230, y: 230, r: 100, top: true, cluster: c };
    // Distribute the rest in a loose orbit on the right
    const ringR = 130;
    const angle = (i - 1) / Math.max(ordered.length - 1, 1) * Math.PI * 2 - Math.PI * 0.6;
    return {
      x: 540 + Math.cos(angle) * ringR,
      y: 260 + Math.sin(angle) * ringR * 0.7,
      r: 50 + 10 * Math.random(),
      top: false,
      cluster: c,
    };
  });

  const totalDots = 130;
  // Allocate dots by cluster signal_count proportionally
  const totalSignals = ordered.reduce((s, c) => s + c.signal_count, 0);
  const allocations = ordered.map(c => Math.max(8, Math.round((c.signal_count / totalSignals) * totalDots)));

  // Create rings + labels for each centroid
  centroids.forEach((cen, i) => {
    const ring = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
    ring.setAttribute('cx', cen.x);
    ring.setAttribute('cy', cen.y);
    ring.setAttribute('rx', cen.r);
    ring.setAttribute('ry', cen.r * 0.78);
    ring.setAttribute('class', cen.top ? 'ring top' : 'ring');
    svg.appendChild(ring);

    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', cen.x);
    label.setAttribute('y', cen.y - cen.r * 0.78 - 10);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('class', cen.top ? 'label top' : 'label');
    label.textContent = truncate(cen.cluster.title, 38);
    svg.appendChild(label);

    setTimeout(() => {
      ring.classList.add('lit');
      label.classList.add('lit');
    }, 900 + i * 120);
  });

  // Dots: seed random, then transition to centroid
  const dots = [];
  centroids.forEach((cen, ci) => {
    const count = allocations[ci];
    for (let j = 0; j < count; j++) {
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const startX = padding + Math.random() * (W - padding * 2);
      const startY = padding + Math.random() * (H - padding * 2);
      dot.setAttribute('cx', startX);
      dot.setAttribute('cy', startY);
      dot.setAttribute('r', 2.4);
      dot.setAttribute('class', cen.top ? 'dot top' : 'dot');
      svg.appendChild(dot);
      dots.push({ dot, target: cen, startX, startY });
    }
  });

  // Phase 1: fade in dots (~600ms)
  dots.forEach((d, i) => {
    setTimeout(() => d.dot.classList.add('lit'), 60 + (i * 4));
  });

  // Phase 2: fly to centroid (~1.4s after fade-in starts)
  setTimeout(() => {
    dots.forEach(d => {
      const tx = d.target.x + (Math.random() - 0.5) * d.target.r * 1.4;
      const ty = d.target.y + (Math.random() - 0.5) * d.target.r * 1.1;
      d.dot.setAttribute('cx', tx);
      d.dot.setAttribute('cy', ty);
    });
  }, 1100);

  // Render epic list with stagger
  const list = $('#epicList');
  list.innerHTML = '';
  ordered.forEach((c, i) => {
    const node = el('div', {
      class: 'epic' + (c.is_top ? ' top' : ''),
      style: { 'animation-delay': `${1700 + i * 180}ms` },
    },
      el('div', null,
        el('div', { class: 't' }, c.title),
        el('div', { class: 'meta' }, `${c.signal_count.toLocaleString()} signals`),
      ),
      el('span', { class: 'rice' }, c.rice_score.toFixed(1)),
    );
    list.appendChild(node);
  });
}

function truncate(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }

// -------- Stage 3: Score --------
function handleScore(rice) {
  setStage(2, 2);

  // Pre-fill title/desc from currentRun if recommend hasn't arrived yet — defer if not.
  // (recommend event arrives 4s after score, so this is fine — leave —)
  $('#scoreTitle').textContent = currentRun.top_epic_title || 'Computing top epic…';
  $('#scoreDesc').textContent  = currentRun.top_epic_rationale || 'OmniHub cross-references reach with effort, then weights for urgency, strategic fit, and risk-inverse.';

  // Stagger the bars
  const order = ['reach', 'impact', 'confidence', 'effort', 'urgency', 'strategy', 'risk_inv'];
  order.forEach((k, i) => {
    const v = rice[k];
    const bar = document.querySelector(`.rice-bar[data-k="${k}"]`);
    if (!bar) return;
    setTimeout(() => {
      // For "effort" lower is better, but visually we still fill to its value (with accent color)
      bar.querySelector('.trackfill').style.width = v + '%';
      countUp(bar.querySelector('.val'), 0, v, 750);
    }, 120 + i * 200);
  });

  // Composite count-up + band gauge
  setTimeout(() => {
    countUp($('#scoreNum'), 0, rice.composite, 1300, 1);
    $('#scoreBand').style.setProperty('--pct', rice.composite + '%');
  }, 600);
}

// -------- Stage 4: Recommend --------
function handleRecommend(epic) {
  setStage(3, 3);

  // Backfill the score-stage title/desc retrospectively if the user lingers there
  currentRun.top_epic_title = epic.title;
  currentRun.top_epic_rationale = epic.rationale;
  $('#scoreTitle').textContent = epic.title;
  $('#scoreDesc').textContent  = epic.rationale;
  $('#scoreVerdict').textContent = epic.verdict;

  $('#recKicker').textContent = `Epic · Priority 1 · Score ${epic.rice.composite}`;
  $('#recTitle').textContent  = epic.title;
  $('#recWhy').textContent    = epic.rationale;
  $('#recReco').textContent   = epic.recommendation;

  const al = $('#acceptList');
  al.innerHTML = '';
  epic.acceptance_criteria.forEach((c, i) => {
    const li = el('li', { style: { 'animation-delay': `${i * 110}ms`, animation: 'epicIn .45s cubic-bezier(.25,.8,.25,1) both' } }, c);
    al.appendChild(li);
  });

  const ql = $('#quoteList');
  ql.innerHTML = '';
  epic.evidence.forEach((q, i) => {
    const node = el('div', {
      class: 'quote',
      style: { 'animation-delay': `${i * 220 + 120}ms` },
    },
      el('div', { class: 'q' }, '“' + q.quote + '”'),
      el('div', { class: 'src' }, q.source),
    );
    ql.appendChild(node);
  });
}

// -------- Stage 5: Sync --------
function handleSync(sync) {
  setStage(4, 4);

  const epicTitle = currentRun.top_epic_title || 'Recommended epic';

  // Jira card
  $('#jiraId').textContent      = sync.jira.id;
  $('#jiraProj').textContent    = sync.jira.project;
  $('#jiraTitle').textContent   = epicTitle;
  $('#jiraDesc').textContent    = 'Auto-created epic with linked acceptance criteria and evidence quotes. Story points estimated from RICE++ effort weight.';
  $('#jiraPts').textContent     = sync.jira.story_points;
  setTimeout(() => {
    $('#jiraStatus').textContent = '✓ Created · ' + sync.jira.id;
    $('#jiraTicket').classList.add('created');
  }, 700);

  // Confluence card
  $('#confSpace').textContent   = 'space · ' + sync.confluence.space;
  $('#confTitle').textContent   = sync.confluence.title;
  $('#confLinked').textContent  = sync.confluence.linked_jira;
  setTimeout(() => {
    $('#confStatus').textContent = '✓ Draft published';
    $('#confTicket').classList.add('created');
  }, 1700);

  currentRun.sync = sync;
}

// -------- Done --------
function handleDone(meta) {
  setStage(4, 5);
  $$('.stage-chip').forEach(c => c.classList.add('done'));

  if (currentRun.ingest) {
    $('#finSignals').textContent = currentRun.ingest.signal_count.toLocaleString();
    $('#finTime').textContent    = currentRun.ingest.runtime_seconds + 's';
  }
  setTimeout(() => $('#finale').classList.add('shown'), 600);

  $('#liveDot').classList.add('idle');
  $('#liveDot').textContent = 'COMPLETE';

  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
}

// -------- Manual stage navigation (chips clickable to replay-jump) --------
$$('.stage-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const idx = parseInt(chip.dataset.stage, 10);
    if (Number.isNaN(idx)) return;
    setStage(idx, idx + 1);
  });
});

// -------- Wiring --------
$('#urlForm').addEventListener('submit', e => {
  e.preventDefault();
  const v = $('#urlInput').value.trim();
  if (v) startRun(v);
});

$('#backLink').addEventListener('click', e => {
  e.preventDefault();
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
  setView('home');
});

$('#replayBtn').addEventListener('click', () => {
  const dom = $('#domainPill').textContent;
  if (dom && dom !== 'domain') startRun(dom);
});

// -------- Methodology modal --------
const modal = $('#modalBackdrop');
function openModal() {
  modal.classList.add('shown');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}
function closeModal() {
  modal.classList.remove('shown');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}
$('#methodologyBtn').addEventListener('click', openModal);
$('#methodologyFootnote').addEventListener('click', openModal);
$('#modalClose').addEventListener('click', closeModal);
modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modal.classList.contains('shown')) closeModal();
});

// -------- Boot --------
probeBackend();
loadCatalog();
setView('home');

// Allow direct linking to ?domain=stripe.com
const params = new URLSearchParams(location.search);
const initialDomain = params.get('domain');
if (initialDomain) {
  // Wait a tick so home view is ready, then jump
  setTimeout(() => startRun(initialDomain), 200);
}
