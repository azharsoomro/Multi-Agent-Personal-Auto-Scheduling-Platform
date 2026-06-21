'use strict';

const API    = '';
const WS_URL = `ws://${location.host}/ws`;

let ws           = null;
let wsRetryDelay = 1000;
let agents       = {};
let metricsHistory = [];

const AGENT_META = {
  ai_times:        { emoji: '📺', title: 'AI-Times',        desc: 'Daily AI YouTube digest' },
  mailman:         { emoji: '📬', title: 'Mailman',          desc: 'Gmail classifier & labeler' },
  wallstreet_wolf: { emoji: '🐺', title: 'Wallstreet Wolf',  desc: 'Stock tracker & market report' },
  hacker_digest:   { emoji: '🔥', title: 'Hacker Digest',    desc: 'Top HN stories summarized' },
};

const CAT_COLORS = {
  urgent:          '#ef4444', action_required: '#f97316',
  follow_up:       '#eab308', newsletter:      '#6366f1',
  notification:    '#06b6d4', personal:        '#22c55e',
  other:           '#94a3b8',
};
const CAT_LABELS = {
  urgent: 'Urgent', action_required: 'Action Required', follow_up: 'Follow-Up',
  newsletter: 'Newsletter', notification: 'Notification', personal: 'Personal', other: 'Other',
};

// ── DOM helpers ─────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const fmt  = d => d ? new Date(d).toLocaleString()  : '—';
const fmtR = d => {
  if (!d) return 'Never';
  const s = Math.floor((Date.now() - new Date(d)) / 1000);
  if (s < 60)   return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  return `${Math.floor(s/3600)}h ago`;
};

// ── Clock ───────────────────────────────────────────────────────────────────
setInterval(() => { $('clock').textContent = new Date().toUTCString().slice(17,25) + ' UTC'; }, 1000);

// ── Tab navigation ──────────────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    $(`tab-${tab}`).classList.add('active');
    $('pageTitle').textContent = link.textContent.trim();
    const loaders = {
      scheduler: loadScheduler, aitimes: loadAITimes,
      mailman: loadMailman, wallstreet: loadWallstreet,
      hacker: loadHacker, logs: loadLogs,
    };
    if (loaders[tab]) loaders[tab]();
  });
});

$('logAgentFilter').addEventListener('change', loadLogs);

// ── Resource alarm ──────────────────────────────────────────────────────────
const ALARM_THRESHOLD = 90;
const ALARM_ACTIONS = {
  cpu:  'High CPU — consider pausing scheduled agents or closing background applications.',
  ram:  'High RAM — Qwen3 model may be loading large context; close unused apps or reduce batch size.',
  disk: 'Low disk space — clear old log files, database WAL files, or Ollama model cache.',
};

function checkAlarm(m) {
  const alarms = [];
  if (m.cpu_pct  > ALARM_THRESHOLD) alarms.push({ res: 'cpu',  val: m.cpu_pct.toFixed(1) });
  if (m.ram_pct  > ALARM_THRESHOLD) alarms.push({ res: 'ram',  val: m.ram_pct.toFixed(1) });
  if (m.disk_pct > ALARM_THRESHOLD) alarms.push({ res: 'disk', val: m.disk_pct.toFixed(1) });

  _resourceOk = alarms.length === 0;
  renderHealthList(_ollamaRunning, _resourceOk);

  const banner = $('alarmBanner');
  if (!banner) return;
  if (!alarms.length) { banner.style.display = 'none'; return; }

  banner.style.display = 'flex';
  banner.innerHTML = alarms.map(a => `
    <div class="alarm-item">
      <span class="alarm-icon">⚠️</span>
      <strong>${a.res.toUpperCase()} at ${a.val}%</strong>
      &nbsp;—&nbsp;${ALARM_ACTIONS[a.res]}
    </div>`).join('');

  // Flash metric card red
  ['cpu','ram','disk'].forEach(r => {
    const card = $(`mc-${r}`);
    if (card) card.classList.toggle('metric-alarm', alarms.some(a => a.res === r));
  });
}

// ── WebSocket ────────────────────────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    wsRetryDelay = 1000;
    $('wsBadge').textContent = '● Live';
    $('wsBadge').classList.add('live');
  };
  ws.onmessage = ({ data }) => handleEvent(JSON.parse(data));
  ws.onclose = () => {
    $('wsBadge').textContent = '● Reconnecting…';
    $('wsBadge').classList.remove('live');
    setTimeout(connectWS, wsRetryDelay);
    wsRetryDelay = Math.min(wsRetryDelay * 2, 16000);
  };
}

function handleEvent(msg) {
  const { event, data, agents: agentData } = msg;
  if (event === 'init') {
    updateMetrics(data.metrics || {});
    updateLLMStats(data.llm_stats || {});
    updateOllama(data.ollama_running);
    agents = agentData || {};
    renderAgentCards(); renderAgentDetails();
    return;
  }
  if (event === 'metrics') {
    updateMetrics(data);
    metricsHistory.push({ cpu: data.cpu_pct, ram: data.ram_pct, disk: data.disk_pct });
    if (metricsHistory.length > 60) metricsHistory.shift();
    drawChart();
    return;
  }
  if (['agent_started','agent_finished','agent_error','agent_crashed','trigger'].includes(event)) {
    pushFeedItem(event, data);
    refreshAgentStatus();
    return;
  }
}

// ── Radial gauge helpers ─────────────────────────────────────────────────────
const MINI_CIRC  = 2 * Math.PI * 38;   // infra mini gauges, r=38
const DONUT_CIRC = 2 * Math.PI * 50;   // donut charts, r=50
function setGauge(arcId, pct) {
  const arc = $(arcId);
  if (!arc) return;
  const clamped = Math.max(0, Math.min(100, pct));
  arc.style.strokeDashoffset = MINI_CIRC * (1 - clamped / 100);
  let col = '';
  if (clamped > 90) col = '#f43f5e';
  else if (clamped > 78) col = '#f59e0b';
  arc.style.stroke = col || '';
}
function setDonut(arcId, pct) {
  const arc = $(arcId);
  if (!arc) return;
  const clamped = Math.max(0, Math.min(100, pct));
  arc.style.strokeDashoffset = DONUT_CIRC * (1 - clamped / 100);
}

// ── System metrics ───────────────────────────────────────────────────────────
let llmSparkData = [];
function updateMetrics(m) {
  if (!m || !Object.keys(m).length) return;
  const cpu  = m.cpu_pct  ?? 0;
  const ram  = m.ram_pct  ?? 0;
  const disk = m.disk_pct ?? 0;

  $('cpuVal').textContent  = `${cpu.toFixed(0)}%`;
  $('ramVal').textContent  = `${ram.toFixed(0)}%`;
  $('diskVal').textContent = `${disk.toFixed(0)}%`;

  setGauge('cpuArc',  cpu);
  setGauge('ramArc',  ram);
  setGauge('diskArc', disk);

  if (m.ram_used_gb)  $('ramSub').textContent  = `${m.ram_used_gb} / ${m.ram_total_gb} GB`;
  if (m.disk_used_gb) $('diskSub').textContent = `${m.disk_used_gb} / ${m.disk_total_gb} GB`;
  if ($('cpuSub')) $('cpuSub').textContent = 'Processor load';

  if (m.threads && $('threadsVal')) $('threadsVal').textContent = m.threads;

  checkAlarm(m);
}

function updateLLMStats(s) {
  $('llmVal').textContent = s.total ?? '0';
  $('llmAvg').textContent = `avg ${s.avg_ms ?? '—'} ms / call`;
  if ($('llmCallsFoot')) $('llmCallsFoot').textContent = `${s.total ?? 0} total`;
  if ($('heroLLM')) $('heroLLM').textContent = `${s.total ?? 0}`;
  // sparkline: track avg latency over time
  if (s.avg_ms) {
    llmSparkData.push(s.avg_ms);
    if (llmSparkData.length > 40) llmSparkData.shift();
    drawLLMSpark();
  }
}

function drawLLMSpark() {
  const c = $('llmSpark');
  if (!c || llmSparkData.length < 2) return;
  const ctx = c.getContext('2d');
  const W = c.width = c.offsetWidth;
  const H = c.height = 40;
  ctx.clearRect(0, 0, W, H);
  const max = Math.max(...llmSparkData) * 1.1 || 1;
  const n = llmSparkData.length;
  const pts = llmSparkData.map((v, i) => ({ x: (i/(n-1))*W, y: H - (v/max)*H*0.9 - 2 }));
  // fill
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, 'rgba(16,185,129,0.35)');
  grad.addColorStop(1, 'rgba(16,185,129,0)');
  ctx.beginPath(); ctx.moveTo(pts[0].x, H);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[n-1].x, H); ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();
  // line
  ctx.beginPath(); ctx.strokeStyle = '#10b981'; ctx.lineWidth = 1.5;
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke();
}

// ── Number formatting ─────────────────────────────────────────────────────────
function fmtNum(n) {
  if (n >= 1e9) return (n/1e9).toFixed(1).replace(/\.0$/,'') + 'B';
  if (n >= 1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'') + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'') + 'K';
  return `${n}`;
}
function setDelta(id, pct) {
  const el = $(id);
  if (!el) return;
  const up = pct >= 0;
  el.className = `kpi-delta ${up ? 'up' : 'down'}`;
  el.textContent = `${Math.abs(pct)}%`;
}

// ── Dashboard operations stats ────────────────────────────────────────────────
let _lastStats = null;
async function loadDashStats() {
  try {
    const s = await fetch(`${API}/api/dashboard/stats`).then(r => r.json());
    _lastStats = s;

    // KPI cards
    if ($('kpiRuns'))    $('kpiRuns').textContent    = fmtNum(s.total_runs);
    setDelta('kpiRunsDelta', s.runs_delta);
    if ($('kpiSuccess')) $('kpiSuccess').textContent = `${s.success_rate}%`;
    setDelta('kpiSuccessDelta', s.success_delta);
    if ($('kpiSuccessSub')) $('kpiSuccessSub').textContent = `${s.success_runs}/${s.total_runs} runs`;
    if ($('kpiTokens'))  $('kpiTokens').textContent  = fmtNum(s.est_tokens);
    if ($('kpiLLMcalls')) { const e=$('kpiLLMcalls'); e.className='kpi-delta up'; e.textContent = `${s.llm_calls}`; }
    if ($('kpiResp'))    $('kpiResp').textContent    = `${s.avg_duration_s}s`;

    // Cost optimization
    if ($('costVal'))   $('costVal').textContent   = `$${s.cost_avoided.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`;
    if ($('cloudCost')) $('cloudCost').textContent = `$${s.cost_avoided.toFixed(2)}`;
    if ($('costSub'))   $('costSub').textContent   = `100% on-premise · ${s.llm_calls} LLM calls @ $${s.cost_per_call}/call avoided`;
    if ($('cfTokens'))  $('cfTokens').textContent  = fmtNum(s.est_tokens);
    if ($('cfEmails'))  $('cfEmails').textContent  = s.total_classified;
    if ($('cfData'))    $('cfData').textContent    = fmtNum(s.total_stocks + s.total_videos + s.total_stories);

    // Model performance donut (success rate)
    setDonut('modelArc', s.success_rate);
    if ($('modelVal')) $('modelVal').textContent = `${s.success_rate}%`;
    if ($('modelStats')) $('modelStats').innerHTML = `
      <div class="dl-row"><span class="dl-left"><span class="dl-dot" style="background:#4ade80"></span>Successful</span><span class="dl-val">${s.success_runs}</span></div>
      <div class="dl-row"><span class="dl-left"><span class="dl-dot" style="background:#f43f5e"></span>Failed</span><span class="dl-val">${s.failed_runs}</span></div>
      <div class="dl-row"><span class="dl-left"><span class="dl-dot" style="background:#a78bfa"></span>Avg latency</span><span class="dl-val">${s.llm_avg_ms} ms</span></div>
      <div class="dl-row"><span class="dl-left"><span class="dl-dot" style="background:#22d3ee"></span>Model</span><span class="dl-val">Qwen3 8B</span></div>`;

    // System health donut
    const health = Math.max(0, Math.min(100, Math.round(100 - (s.failed_runs / Math.max(1,s.total_runs)) * 100)));
    setDonut('healthArc', health);
    if ($('healthVal')) $('healthVal').textContent = `${health}%`;
  } catch (e) { /* ignore */ }
}

// ── System health operational list (uses live status) ─────────────────────────
function renderHealthList(ollamaRunning, resourceOk) {
  const el = $('healthList');
  if (!el) return;
  const item = (label, ok) =>
    `<div class="op-row"><span class="op-left"><span class="dl-dot" style="background:${ok?'#4ade80':'#f43f5e'}"></span>${label}</span>
     <span class="op-badge ${ok?'':'down'}">${ok?'Operational':'Down'}</span></div>`;
  el.innerHTML =
    item('LLM Engine (Ollama)', ollamaRunning) +
    item('Database (SQLite)', true) +
    item('Scheduler', true) +
    item('Resources', resourceOk);
}

// ── Top performing agents (with sparklines) ───────────────────────────────────
async function renderTopAgents() {
  const el = $('topAgents');
  if (!el) return;
  try {
    const perf = await fetch(`${API}/api/dashboard/agent-perf`).then(r => r.json());
    perf.sort((a, b) => b.runs - a.runs);
    el.innerHTML = perf.map(p => {
      const meta = AGENT_META[p.agent] || { emoji:'🤖', title:p.agent };
      const colors = { ai_times:'#3b82f6', mailman:'#ec4899', wallstreet_wolf:'#10b981', hacker_digest:'#f97316' };
      const col = colors[p.agent] || '#6366f1';
      const sid = `spark-${p.agent}`;
      return `
      <div class="ta-row" onclick="triggerAgent('${p.agent}',true)">
        <div class="ta-ic" style="background:${col}22">${meta.emoji}</div>
        <div class="ta-info">
          <div class="ta-name">${meta.title}</div>
          <div class="ta-meta">${p.runs} runs</div>
        </div>
        <canvas class="ta-spark" id="${sid}"></canvas>
        <div class="ta-rate" style="color:${col}">${p.success_rate}%</div>
      </div>`;
    }).join('');
    // draw sparklines after DOM insert
    perf.forEach(p => {
      const colors = { ai_times:'#3b82f6', mailman:'#ec4899', wallstreet_wolf:'#10b981', hacker_digest:'#f97316' };
      drawSparkline(`spark-${p.agent}`, p.spark, colors[p.agent] || '#6366f1');
    });
  } catch (e) { /* ignore */ }
}

function drawSparkline(id, data, color) {
  const c = $(id);
  if (!c || !data || data.length < 1) return;
  const W = c.width = 80, H = c.height = 30;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  if (data.length === 1) data = [data[0], data[0]];
  const max = Math.max(...data), min = Math.min(...data);
  const range = (max - min) || 1;
  const pts = data.map((v, i) => ({ x: (i/(data.length-1))*W, y: H - ((v-min)/range)*(H-6) - 3 }));
  // gradient fill
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, color + '55'); g.addColorStop(1, color + '00');
  ctx.beginPath(); ctx.moveTo(pts[0].x, H);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length-1].x, H); ctx.closePath();
  ctx.fillStyle = g; ctx.fill();
  // line
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 1.6;
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke();
}

// ── Full dashboard refresh ────────────────────────────────────────────────────
async function loadDashboard() {
  await loadDashStats();
  await renderTopAgents();
}

let _ollamaRunning = true, _resourceOk = true;
function updateOllama(running) {
  _ollamaRunning = running;
  if ($('ollamaDot'))   $('ollamaDot').className = 'status-dot ' + (running ? 'ok' : 'err');
  if ($('ollamaLabel')) $('ollamaLabel').textContent = running ? 'Ollama ✓ Qwen3' : 'Ollama offline';
  if ($('ollamaDot2'))   $('ollamaDot2').className = 'status-dot ' + (running ? 'ok' : 'err');
  if ($('ollamaLabel2')) $('ollamaLabel2').textContent = running ? 'Qwen3 · Local' : 'Ollama offline';
  renderHealthList(_ollamaRunning, _resourceOk);
}

// ── Agent cards ──────────────────────────────────────────────────────────────
function renderAgentCards() {
  const el = $('agentCards');
  if (!el) return;
  el.innerHTML = Object.entries(agents).map(([name, info]) => {
    const meta   = AGENT_META[name] || { emoji: '🤖', title: name, desc: '' };
    const status = info.running ? 'running' : (info.last_status || 'never');
    const statusTxt = info.running ? 'Running…' : status;
    return `
    <div class="feature-card ${name}">
      <div class="fc-head">
        <div class="fc-icon">${meta.emoji}</div>
        <div class="fc-title-wrap">
          <div class="fc-title">${meta.title}</div>
          <div class="fc-status-line">
            <span class="fc-dot ${status}"></span>
            ${statusTxt} &bull; ${fmtR(info.last_run)}
          </div>
        </div>
      </div>
      <div class="fc-msg">${info.last_msg || meta.desc}</div>
      <button class="fc-run" onclick="triggerAgent('${name}',false)"
              ${info.running ? 'disabled' : ''}>
        ${info.running ? '⏳ Running…' : '▶ Run Now'}
      </button>
    </div>`;
  }).join('');
}

function renderAgentDetails() {
  $('agentDetailCards').innerHTML = Object.entries(agents).map(([name, info]) => {
    const meta   = AGENT_META[name] || { emoji: '🤖', title: name, desc: '' };
    const status = info.running ? 'running' : (info.last_status || 'never');
    return `
    <div class="agent-detail-card">
      <div class="agent-detail-header">
        <div class="agent-emoji">${meta.emoji}</div>
        <div>
          <div class="agent-detail-title">${meta.title}</div>
          <div class="agent-detail-sub">${meta.desc}</div>
        </div>
        <div style="margin-left:auto"><span class="badge badge-${status}">${status}</span></div>
      </div>
      <div class="agent-detail-body">
        <div class="agent-stat"><span class="stat-key">Last Run</span>
          <span class="stat-val">${fmt(info.last_run)}</span></div>
        <div class="agent-stat"><span class="stat-key">Duration</span>
          <span class="stat-val">${info.duration_s ? info.duration_s + 's' : '—'}</span></div>
        <div class="agent-stat"><span class="stat-key">Last Message</span>
          <span class="stat-val" style="max-width:200px;text-align:right">${info.last_msg || '—'}</span></div>
      </div>
      <div class="agent-detail-actions">
        <button class="btn-run" onclick="triggerAgent('${name}',false)"
                ${info.running ? 'disabled' : ''}>▶ Run Now</button>
        <button class="btn-run-force" onclick="triggerAgent('${name}',true)"
                title="Force run even if resources are constrained">⚡ Force</button>
      </div>
    </div>`;
  }).join('');

  // Agents KPI strip
  const names = Object.keys(agents);
  if ($('agTotal'))  $('agTotal').textContent  = names.length;
  if ($('agActive')) $('agActive').textContent = names.filter(n => agents[n].running).length;
  if (_lastStats) {
    if ($('agRuns'))    $('agRuns').textContent    = fmtNum(_lastStats.total_runs);
    if ($('agSuccess')) $('agSuccess').textContent = `${_lastStats.success_rate}%`;
  }
}

async function triggerAgent(name, force) {
  const res  = await fetch(`${API}/api/agents/${name}/trigger`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  const data = await res.json();
  pushFeedItem('trigger', { agent: name, status: data.status, reason: data.reason });
  setTimeout(refreshAgentStatus, 800);
}

async function refreshAgentStatus() {
  const res = await fetch(`${API}/api/agents`);
  agents = await res.json();
  renderAgentCards(); renderAgentDetails();
}

// ── Live feed ────────────────────────────────────────────────────────────────
function pushFeedItem(event, data) {
  const feed = $('liveFeed');
  const ts   = new Date().toLocaleTimeString();
  const icons = { agent_started:'▶', agent_finished:'✓', agent_error:'✗',
                  agent_crashed:'💥', trigger:'→', metrics:'📊' };
  const text =
    event === 'agent_started'  ? `▶ ${data.agent} started` :
    event === 'agent_finished' ? `✓ ${data.agent} done — ${data.result?.summary || ''}` :
    event === 'agent_error'    ? `✗ ${data.agent} error: ${data.error}` :
    event === 'agent_crashed'  ? `💥 ${data.agent} crashed — auto-recovered` :
    event === 'trigger'        ? `→ ${data.agent}: ${data.status} ${data.reason || ''}` :
    JSON.stringify(data);
  const div = document.createElement('div');
  div.className = `feed-item ${event}`;
  div.innerHTML = `<div class="feed-ts">${ts}</div><div class="feed-text">${text}</div>`;
  feed.prepend(div);
  if (feed.children.length > 50) feed.removeChild(feed.lastChild);
}

// ── Resource chart (filled area) ─────────────────────────────────────────────
function drawChart() {
  const canvas = $('resourceChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const PAD = 6;
  const W   = canvas.width  = canvas.offsetWidth;
  const H   = canvas.height = 220;
  ctx.clearRect(0, 0, W, H);
  const n = metricsHistory.length;
  const plotH = H - PAD * 2;
  const yOf = v => PAD + plotH - (v / 100) * plotH;

  // horizontal grid
  [0, 25, 50, 75, 100].forEach(pct => {
    const y = yOf(pct);
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255,255,255,0.045)';
    ctx.lineWidth = 1;
    ctx.moveTo(34, y); ctx.lineTo(W, y); ctx.stroke();
    ctx.fillStyle = 'rgba(148,163,184,0.35)';
    ctx.font = '9px system-ui';
    ctx.fillText(`${pct}%`, 6, y + 3);
  });

  if (n < 2) return;

  const series = [
    { key: 'cpu',  stroke: '#818cf8', glow: 'rgba(129,140,248,0.45)', c0: 'rgba(129,140,248,0.28)' },
    { key: 'ram',  stroke: '#22d3ee', glow: 'rgba(34,211,238,0.40)',  c0: 'rgba(34,211,238,0.22)'  },
    { key: 'disk', stroke: '#fb923c', glow: 'rgba(251,146,60,0.35)',  c0: 'rgba(251,146,60,0.16)'  },
  ];

  const xOf = i => 34 + (i / (n - 1)) * (W - 38);

  series.forEach(({ key, stroke, c0 }) => {
    const pts = metricsHistory.map((m, i) => ({ x: xOf(i), y: yOf(m[key]) }));

    // smooth path via quadratic midpoints
    const trace = () => {
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) {
        const xc = (pts[i-1].x + pts[i].x) / 2;
        const yc = (pts[i-1].y + pts[i].y) / 2;
        ctx.quadraticCurveTo(pts[i-1].x, pts[i-1].y, xc, yc);
      }
      ctx.lineTo(pts[pts.length-1].x, pts[pts.length-1].y);
    };

    // gradient fill
    const grad = ctx.createLinearGradient(0, PAD, 0, H);
    grad.addColorStop(0, c0);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.beginPath();
    trace();
    ctx.lineTo(pts[pts.length-1].x, H - PAD);
    ctx.lineTo(pts[0].x, H - PAD);
    ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();

    // glowing line
    ctx.beginPath(); trace();
    ctx.strokeStyle = stroke; ctx.lineWidth = 2.4;
    ctx.shadowColor = stroke; ctx.shadowBlur = 8;
    ctx.lineJoin = 'round'; ctx.stroke();
    ctx.shadowBlur = 0;

    // end dot
    const last = pts[pts.length-1];
    ctx.beginPath(); ctx.arc(last.x, last.y, 3, 0, Math.PI*2);
    ctx.fillStyle = stroke; ctx.fill();
  });
}

// ── Scheduler tab ─────────────────────────────────────────────────────────────
async function loadScheduler() {
  const jobs  = await fetch(`${API}/api/scheduler/jobs`).then(r => r.json());
  const tbody = document.querySelector('#schedulerTable tbody');
  tbody.innerHTML = jobs.map(j => {
    const agentName = j.id.replace('agent_', '');
    return `<tr>
      <td><strong>${agentName}</strong></td>
      <td>${j.next_run ? new Date(j.next_run).toLocaleString() : '—'}</td>
      <td><code style="font-size:11px;color:#94a3b8">${j.trigger}</code></td>
      <td>
        <input class="cron-input" id="cron-${agentName}" placeholder="* * * * *">
        <button class="btn-sm" onclick="updateCron('${agentName}')">Save</button>
      </td>
    </tr>`;
  }).join('');

  // Scheduler KPI strip
  if ($('schJobs')) $('schJobs').textContent = jobs.length;
  const upcoming = jobs.filter(j => j.next_run).sort((a,b) => new Date(a.next_run) - new Date(b.next_run))[0];
  if ($('schNext'))  $('schNext').textContent  = upcoming ? fmtR(upcoming.next_run).replace('ago','').trim() || new Date(upcoming.next_run).toLocaleDateString() : '—';
  if ($('schAgent')) {
    const an = upcoming ? upcoming.id.replace('agent_','') : '—';
    const meta = AGENT_META[an];
    $('schAgent').textContent = meta ? meta.title : an;
  }
  // Show next run as a friendly time
  if ($('schNext') && upcoming) {
    $('schNext').textContent = new Date(upcoming.next_run).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  }
}

async function updateCron(agentName) {
  const cron = $(`cron-${agentName}`).value.trim();
  if (!cron) return;
  const res = await fetch(`${API}/api/scheduler/${agentName}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cron })
  });
  res.ok ? loadScheduler() : alert('Invalid cron expression');
}

// ── AI-Times tab ──────────────────────────────────────────────────────────────
async function loadAITimes() {
  const [news, pers] = await Promise.all([
    fetch(`${API}/api/ai-times/videos?category=news&limit=5`).then(r => r.json()),
    fetch(`${API}/api/ai-times/videos?category=personality&limit=5`).then(r => r.json()),
  ]);
  $('newsVideos').innerHTML = news.length ? news.map(videoCard).join('') : emptyState('No videos yet — run AI-Times agent');
  $('persVideos').innerHTML = pers.length ? pers.map(videoCard).join('') : emptyState('No videos yet — run AI-Times agent');
  // KPI strip
  if ($('aitTotal')) $('aitTotal').textContent = news.length + pers.length;
  if ($('aitNews'))  $('aitNews').textContent  = news.length;
  if ($('aitPers'))  $('aitPers').textContent  = pers.length;
  if ($('aitUpdated')) {
    const latest = [...news, ...pers].map(v => v.fetched_at).sort().pop();
    $('aitUpdated').textContent = latest ? fmtR(latest) : '—';
  }
}

function videoCard(v) {
  const thumb = v.thumbnail
    ? `<img src="${v.thumbnail}" class="video-thumb" onerror="this.style.display='none'">`
    : `<div class="video-thumb-placeholder">📺</div>`;
  return `
  <div class="video-card">
    ${thumb}
    <div class="video-info">
      <a href="${v.url}" target="_blank" class="video-title">${v.title}</a>
      <div class="video-meta">
        <span class="tag-chip">${v.channel}</span>
        <span class="tag-chip muted">${v.published}</span>
      </div>
      <p class="video-desc">${v.description || ''}</p>
    </div>
  </div>`;
}

// ── Mailman tab ────────────────────────────────────────────────────────────────
async function loadMailman() {
  const [records, stats, kp] = await Promise.all([
    fetch(`${API}/api/mailman/records?limit=30`).then(r => r.json()),
    fetch(`${API}/api/mailman/stats`).then(r => r.json()),
    fetch(`${API}/api/config/key-people`).then(r => r.json()),
  ]);

  // Category bars
  const total = stats.total || 1;
  const cats  = stats.by_category || {};
  $('mailmanStats').innerHTML = Object.entries(cats).length
    ? Object.entries(cats).sort((a,b) => b[1]-a[1]).map(([cat, cnt]) => {
        const pct = Math.round((cnt / total) * 100);
        const col = CAT_COLORS[cat] || '#94a3b8';
        const lbl = CAT_LABELS[cat] || cat;
        return `
        <div class="cat-row">
          <div class="cat-label">${lbl}</div>
          <div class="cat-bar-wrap">
            <div class="cat-bar" style="width:${pct}%;background:${col}"></div>
          </div>
          <div class="cat-count">${cnt}</div>
        </div>`;
      }).join('') + `<div class="cat-total">Total processed: <strong>${total}</strong></div>`
    : emptyState('No emails classified yet — run Mailman agent');

  // Email list
  $('mailmanList').innerHTML = records.length
    ? records.map(r => {
        const col = CAT_COLORS[r.category] || '#94a3b8';
        const lbl = CAT_LABELS[r.category] || r.category;
        return `
        <div class="mail-row">
          <div class="mail-cat-dot" style="background:${col}" title="${lbl}"></div>
          <div class="mail-info">
            <div class="mail-subject">${r.subject}</div>
            <div class="mail-meta">${r.sender} &bull; ${fmtR(r.processed_at)}</div>
            ${r.summary ? `<div class="mail-summary">${r.summary}</div>` : ''}
          </div>
          <span class="cat-badge" style="background:${col}22;color:${col}">${lbl}</span>
        </div>`;
      }).join('')
    : emptyState('No emails classified yet');

  // Key-people input
  $('keyPeopleInput').value = (kp.key_people || []).join(', ');

  // KPI strip
  if ($('mmTotal'))  $('mmTotal').textContent  = stats.total || 0;
  if ($('mmUrgent')) $('mmUrgent').textContent = (cats.urgent || 0);
  if ($('mmCats'))   $('mmCats').textContent   = Object.keys(cats).length;
}

async function saveKeyPeople() {
  const raw = $('keyPeopleInput').value;
  const list = raw.split(',').map(s => s.trim()).filter(Boolean);
  await fetch(`${API}/api/config/key-people`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key_people: list })
  });
  pushFeedItem('trigger', { agent: 'mailman', status: `Key people saved: ${list.length} entries` });
}

// ── Wallstreet tab ────────────────────────────────────────────────────────────
async function loadWallstreet() {
  const [stocks, commentary, metals, fx] = await Promise.all([
    fetch(`${API}/api/stocks?limit=200`).then(r => r.json()),
    fetch(`${API}/api/wallstreet/commentary`).then(r => r.json()),
    fetch(`${API}/api/wallstreet/metals`).then(r => r.json()),
    fetch(`${API}/api/wallstreet/fx`).then(r => r.json()),
  ]);

  // Deduplicate — latest per ticker
  const latest = {};
  stocks.forEach(s => { if (!latest[s.ticker]) latest[s.ticker] = s; });
  const sorted = Object.values(latest).sort((a,b) => b.change_pct - a.change_pct);

  // Commentary card
  const card = $('wsCommentary');
  if (commentary.commentary) {
    card.style.display = 'block';
    card.innerHTML = `
      <div class="commentary-header">🤖 AI Market Commentary
        <span class="commentary-ts">${fmtR(commentary.created_at)}</span>
      </div>
      <div class="commentary-body">${commentary.commentary}</div>`;
  }

  // KPI strip
  const gainers = sorted.filter(s => s.change_pct > 0).length;
  const losers  = sorted.filter(s => s.change_pct < 0).length;
  const avgChg  = sorted.length ? (sorted.reduce((a,s)=>a+s.change_pct,0)/sorted.length) : 0;
  if ($('wsTracked')) $('wsTracked').textContent = sorted.length;
  if ($('wsGainers')) $('wsGainers').textContent = gainers;
  if ($('wsLosers'))  $('wsLosers').textContent  = losers;
  if ($('wsAvg'))     $('wsAvg').textContent     = `${avgChg>=0?'+':''}${avgChg.toFixed(2)}%`;

  // Gainers / Losers
  const top5g = sorted.slice(0, 5);
  const top5l = [...sorted].sort((a,b) => a.change_pct - b.change_pct).slice(0, 5);
  document.querySelector('#gainersTable tbody').innerHTML   = top5g.map(stockRow).join('');
  document.querySelector('#losersTable tbody').innerHTML    = top5l.map(stockRow).join('');
  document.querySelector('#watchlistTable tbody').innerHTML = sorted.map(stockRowFull).join('');

  // Metals + FX
  $('metalsSection').innerHTML = `
    <div class="metals-section">
      <div class="metals-title">🥇 Precious Metals</div>
      ${metals.length ? metals.map(m => `
        <div class="metal-row">
          <span class="metal-label">${m.label}</span>
          <span class="metal-price">$${m.price.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</span>
          <span class="${m.change_pct>=0?'up':'down'}">${m.change_pct>=0?'+':''}${m.change_pct.toFixed(2)}%</span>
        </div>`).join('') : '<div class="muted-note">Run agent to fetch data</div>'}
    </div>
    <div class="metals-section" style="margin-top:12px">
      <div class="metals-title">💱 Currency Exchange</div>
      ${fx.length ? fx.map(f => `
        <div class="metal-row">
          <span class="metal-label">${f.label}</span>
          <span class="metal-price">${f.price.toFixed(4)}</span>
          <span class="${f.change_pct>=0?'up':'down'}">${f.change_pct>=0?'+':''}${f.change_pct.toFixed(3)}%</span>
        </div>`).join('') : '<div class="muted-note">Run agent to fetch data</div>'}
    </div>`;
}

function stockRow(s) {
  const sign = s.change_pct >= 0 ? '+' : '';
  const cls  = s.change_pct >= 0 ? 'up' : 'down';
  return `<tr>
    <td><strong>${s.ticker}</strong></td>
    <td>$${s.price.toFixed(2)}</td>
    <td class="${cls}">${sign}${s.change_pct.toFixed(2)}%</td>
  </tr>`;
}

function stockRowFull(s) {
  const sign = s.change_pct >= 0 ? '+' : '';
  const cls  = s.change_pct >= 0 ? 'up' : 'down';
  const mc   = s.market_cap ? `$${(s.market_cap/1e9).toFixed(1)}B` : '—';
  return `<tr>
    <td><strong>${s.ticker}</strong></td>
    <td>$${s.price.toFixed(2)}</td>
    <td class="${cls}">${sign}${s.change_pct.toFixed(2)}%</td>
    <td>${mc}</td>
    <td>${fmt(s.captured_at)}</td>
  </tr>`;
}

// ── Hacker Digest tab ─────────────────────────────────────────────────────────
async function loadHacker() {
  const [stories, cfg] = await Promise.all([
    fetch(`${API}/api/hacker-digest/stories?limit=10`).then(r => r.json()),
    fetch(`${API}/api/config/hacker-digest`).then(r => r.json()),
  ]);
  $('hdFetch').value  = cfg.fetch;
  $('hdCurate').value = cfg.curate;

  $('hackerStories').innerHTML = stories.length
    ? stories.map((s, i) => `
      <div class="hn-card">
        <div class="hn-rank">#${i + 1}</div>
        <div class="hn-body">
          <a href="${s.url || s.hn_url}" target="_blank" class="hn-title">${s.title}</a>
          <div class="hn-meta">
            <span class="tag-chip">▲ ${s.score}</span>
            <span class="tag-chip">💬 ${s.comments}</span>
            <span class="tag-chip muted">by ${s.by}</span>
            <a href="${s.hn_url}" target="_blank" class="hn-discuss">HN Discussion →</a>
          </div>
          ${s.takeaway ? `<div class="hn-takeaway">💡 ${s.takeaway}</div>` : ''}
        </div>
      </div>`).join('')
    : emptyState('No stories yet — run Hacker Digest agent');

  // KPI strip
  if ($('hdCount'))    $('hdCount').textContent    = stories.length;
  if ($('hdTopScore')) $('hdTopScore').textContent = stories.length ? Math.max(...stories.map(s => s.score || 0)) : '—';
  if ($('hdComments')) $('hdComments').textContent = stories.length ? stories.reduce((a,s) => a + (s.comments||0), 0) : '—';
}

async function saveHDConfig() {
  const fetch_ = parseInt($('hdFetch').value)  || 30;
  const curate = parseInt($('hdCurate').value) || 10;
  await fetch(`${API}/api/config/hacker-digest`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fetch: fetch_, curate })
  });
  pushFeedItem('trigger', { agent: 'hacker_digest', status: `Config saved: fetch ${fetch_}, curate ${curate}` });
}

// ── Logs tab ──────────────────────────────────────────────────────────────────
async function loadLogs() {
  const agent = $('logAgentFilter').value;
  const url   = `${API}/api/logs?limit=200${agent ? '&agent=' + agent : ''}`;
  const logs  = await fetch(url).then(r => r.json());
  $('logsContainer').innerHTML = logs.map(l => `
    <div class="log-row">
      <span class="log-ts">${new Date(l.ts).toLocaleTimeString()}</span>
      <span class="log-agent">${l.agent}</span>
      <span class="log-level ${l.level}">${l.level}</span>
      <span class="log-msg">${l.message}</span>
    </div>`).join('');

  // Logs KPI strip
  if ($('logTotal')) $('logTotal').textContent = logs.length;
  if ($('logInfo'))  $('logInfo').textContent  = logs.filter(l => l.level === 'INFO').length;
  if ($('logWarn'))  $('logWarn').textContent  = logs.filter(l => l.level === 'WARN').length;
  if ($('logErr'))   $('logErr').textContent   = logs.filter(l => l.level === 'ERROR').length;
}

// ── Metrics history ───────────────────────────────────────────────────────────
async function loadMetricsHistory() {
  const data = await fetch(`${API}/api/metrics/history?limit=60`).then(r => r.json());
  metricsHistory = data;
  drawChart();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function emptyState(msg) {
  return `<div class="empty-state">
    <div class="empty-icon">📭</div>
    <div class="empty-msg">${msg}</div>
  </div>`;
}

// ── Inject SVG gradient defs for radial gauges ────────────────────────────────
function injectGaugeGradients() {
  if (document.getElementById('gaugeGradDefs')) return;
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.id = 'gaugeGradDefs';
  svg.setAttribute('width', '0'); svg.setAttribute('height', '0');
  svg.style.position = 'absolute';
  svg.innerHTML = `
    <defs>
      <linearGradient id="gradCpu" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#818cf8"/><stop offset="100%" stop-color="#6366f1"/>
      </linearGradient>
      <linearGradient id="gradRam" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#22d3ee"/><stop offset="100%" stop-color="#06b6d4"/>
      </linearGradient>
      <linearGradient id="gradDisk" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#fb923c"/><stop offset="100%" stop-color="#f97316"/>
      </linearGradient>
    </defs>`;
  document.body.appendChild(svg);
  // re-apply gradient strokes (CSS fallback set solid colours)
  const map = { cpuArc:'gradCpu', ramArc:'gradRam', diskArc:'gradDisk' };
  Object.entries(map).forEach(([id, grad]) => {
    const arc = $(id);
    if (arc) arc.style.stroke = `url(#${grad})`;
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
async function init() {
  injectGaugeGradients();
  try {
    const data = await fetch(`${API}/api/status`).then(r => r.json());
    updateMetrics(data.metrics || {});
    updateLLMStats(data.llm_stats || {});
    updateOllama(data.ollama_running);
    agents = data.agents || {};
    renderAgentCards(); renderAgentDetails();
  } catch (e) {
    console.warn('Initial status fetch failed — retrying via WS', e);
  }
  await loadMetricsHistory();
  await loadDashboard();
  setInterval(refreshAgentStatus, 10000);
  setInterval(loadDashboard, 12000);
  setInterval(() => {
    const active = document.querySelector('.tab-content.active')?.id;
    if (active === 'tab-logs') loadLogs();
  }, 15000);
  connectWS();
}

window.addEventListener('resize', drawChart);
init();
