'use strict';

// ── Config ─────────────────────────────────────────────────────────────────
const API = '';   // same origin
const WS_URL = `ws://${location.host}/ws`;

// ── State ──────────────────────────────────────────────────────────────────
let ws = null;
let wsRetryDelay = 1000;
let agents = {};
let metricsHistory = [];
let chartCtx = null;

const AGENT_META = {
  ai_times:        { emoji: '📺', title: 'AI-Times',        desc: 'Daily AI YouTube digest' },
  mailman:         { emoji: '📬', title: 'Mailman',          desc: 'Gmail classifier & labeler' },
  wallstreet_wolf: { emoji: '🐺', title: 'Wallstreet Wolf',  desc: 'Stock tracker & market report' },
  hacker_digest:   { emoji: '🔥', title: 'Hacker Digest',    desc: 'Top HN stories summarized' },
};

// ── DOM helpers ────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const fmt = d => d ? new Date(d).toLocaleString() : '—';
const fmtRel = d => {
  if (!d) return 'Never';
  const s = Math.floor((Date.now() - new Date(d)) / 1000);
  if (s < 60)  return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  return `${Math.floor(s/3600)}h ago`;
};

// ── Clock ──────────────────────────────────────────────────────────────────
setInterval(() => {
  $('clock').textContent = new Date().toUTCString().slice(17, 25) + ' UTC';
}, 1000);

// ── Tab navigation ─────────────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    $(`tab-${tab}`).classList.add('active');
    $('pageTitle').textContent = link.textContent.trim();
    if (tab === 'scheduler') loadScheduler();
    if (tab === 'stocks')    loadStocks();
    if (tab === 'emails')    loadEmails();
    if (tab === 'logs')      loadLogs();
  });
});

$('logAgentFilter').addEventListener('change', loadLogs);

// ── WebSocket ──────────────────────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    wsRetryDelay = 1000;
    const badge = $('wsBadge');
    badge.textContent = '● Live';
    badge.classList.add('live');
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    handleEvent(msg);
  };

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
    renderAgentCards();
    renderAgentDetails();
    return;
  }

  if (event === 'metrics') {
    updateMetrics(data);
    metricsHistory.push({ cpu: data.cpu_pct, ram: data.ram_pct, disk: data.disk_pct });
    if (metricsHistory.length > 30) metricsHistory.shift();
    drawChart();
    return;
  }

  if (event === 'agent_started' || event === 'agent_finished' || event === 'agent_error') {
    pushFeedItem(event, data);
    refreshAgentStatus();
    return;
  }
}

// ── System metrics ─────────────────────────────────────────────────────────
function updateMetrics(m) {
  if (!m || !Object.keys(m).length) return;
  $('cpuVal').textContent  = `${m.cpu_pct?.toFixed(1)}%`;
  $('ramVal').textContent  = `${m.ram_pct?.toFixed(1)}%`;
  $('diskVal').textContent = `${m.disk_pct?.toFixed(1)}%`;
  $('cpuBar').style.width  = `${m.cpu_pct}%`;
  $('ramBar').style.width  = `${m.ram_pct}%`;
  $('diskBar').style.width = `${m.disk_pct}%`;
}

function updateLLMStats(s) {
  $('llmVal').textContent = s.total ?? '—';
  $('llmAvg').textContent = `avg ${s.avg_ms ?? '—'} ms`;
}

function updateOllama(running) {
  const dot = $('ollamaDot');
  const lbl = $('ollamaLabel');
  dot.className = 'status-dot ' + (running ? 'ok' : 'err');
  lbl.textContent = running ? 'Ollama ✓' : 'Ollama offline';
}

// ── Agent cards (dashboard) ────────────────────────────────────────────────
function renderAgentCards() {
  const container = $('agentCards');
  container.innerHTML = Object.entries(agents).map(([name, info]) => {
    const meta = AGENT_META[name] || { emoji: '🤖', title: name, desc: '' };
    const status = info.running ? 'running' : (info.last_status || 'never');
    return `
    <div class="agent-card">
      <div class="agent-dot ${status}"></div>
      <div class="agent-info">
        <div class="agent-name">${meta.emoji} ${meta.title}</div>
        <div class="agent-meta">${fmtRel(info.last_run)} &bull; ${info.last_msg || status}</div>
      </div>
      <button class="btn-trigger" onclick="triggerAgent('${name}', false)"
              ${info.running ? 'disabled' : ''}>▶ Run</button>
    </div>`;
  }).join('');
}

// ── Agent detail cards (agents tab) ───────────────────────────────────────
function renderAgentDetails() {
  const container = $('agentDetailCards');
  container.innerHTML = Object.entries(agents).map(([name, info]) => {
    const meta = AGENT_META[name] || { emoji: '🤖', title: name, desc: '' };
    const status = info.running ? 'running' : (info.last_status || 'never');
    const badgeCls = `badge badge-${status}`;
    return `
    <div class="agent-detail-card">
      <div class="agent-detail-header">
        <div class="agent-emoji">${meta.emoji}</div>
        <div>
          <div class="agent-detail-title">${meta.title}</div>
          <div class="agent-detail-sub">${meta.desc}</div>
        </div>
        <div style="margin-left:auto"><span class="${badgeCls}">${status}</span></div>
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
        <button class="btn-run" onclick="triggerAgent('${name}', false)"
                ${info.running ? 'disabled' : ''}>▶ Run Now</button>
        <button class="btn-run-force" onclick="triggerAgent('${name}', true)"
                title="Force run even if resources are constrained">⚡ Force</button>
      </div>
    </div>`;
  }).join('');
}

async function triggerAgent(name, force) {
  const res = await fetch(`${API}/api/agents/${name}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  const data = await res.json();
  pushFeedItem('trigger', { agent: name, status: data.status, reason: data.reason });
  setTimeout(refreshAgentStatus, 800);
}

async function refreshAgentStatus() {
  const res = await fetch(`${API}/api/agents`);
  agents = await res.json();
  renderAgentCards();
  renderAgentDetails();
}

// ── Live feed ──────────────────────────────────────────────────────────────
function pushFeedItem(event, data) {
  const feed = $('liveFeed');
  const ts = new Date().toLocaleTimeString();
  const text = event === 'agent_started'  ? `▶ ${data.agent} started` :
               event === 'agent_finished' ? `✓ ${data.agent} done — ${data.result?.summary || ''}` :
               event === 'agent_error'    ? `✗ ${data.agent} error: ${data.error}` :
               event === 'trigger'        ? `→ ${data.agent} trigger: ${data.status} ${data.reason || ''}` :
               JSON.stringify(data);
  const div = document.createElement('div');
  div.className = `feed-item ${event}`;
  div.innerHTML = `<div class="feed-ts">${ts}</div><div class="feed-text">${text}</div>`;
  feed.prepend(div);
  if (feed.children.length > 50) feed.removeChild(feed.lastChild);
}

// ── Resource chart (canvas) ────────────────────────────────────────────────
function drawChart() {
  const canvas = $('resourceChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = 120;
  ctx.clearRect(0, 0, W, H);

  const n = metricsHistory.length;
  if (n < 2) return;

  const drawLine = (key, color) => {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    metricsHistory.forEach((m, i) => {
      const x = (i / (n - 1)) * W;
      const y = H - (m[key] / 100) * H;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  };

  // Grid lines
  [25, 50, 75].forEach(pct => {
    const y = H - (pct / 100) * H;
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255,255,255,.06)';
    ctx.lineWidth = 1;
    ctx.moveTo(0, y); ctx.lineTo(W, y);
    ctx.stroke();
    ctx.fillStyle = 'rgba(148,163,184,.5)';
    ctx.font = '10px sans-serif';
    ctx.fillText(`${pct}%`, 4, y - 2);
  });

  drawLine('cpu',  '#6366f1');
  drawLine('ram',  '#06b6d4');
  drawLine('disk', '#f97316');

  // Legend
  const legend = [['CPU', '#6366f1'], ['RAM', '#06b6d4'], ['Disk', '#f97316']];
  legend.forEach(([label, color], i) => {
    ctx.fillStyle = color;
    ctx.fillRect(W - 160 + i * 52, 8, 10, 10);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px sans-serif';
    ctx.fillText(label, W - 147 + i * 52, 17);
  });
}

// ── Scheduler tab ──────────────────────────────────────────────────────────
async function loadScheduler() {
  const res = await fetch(`${API}/api/scheduler/jobs`);
  const jobs = await res.json();
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
}

async function updateCron(agentName) {
  const cron = $(`cron-${agentName}`).value.trim();
  if (!cron) return;
  const res = await fetch(`${API}/api/scheduler/${agentName}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cron })
  });
  if (res.ok) { loadScheduler(); }
  else { alert('Invalid cron expression'); }
}

// ── Stocks tab ─────────────────────────────────────────────────────────────
async function loadStocks() {
  const res = await fetch(`${API}/api/stocks?limit=100`);
  const stocks = await res.json();
  const tbody = document.querySelector('#stocksTable tbody');

  // Deduplicate — keep latest per ticker
  const latest = {};
  stocks.forEach(s => {
    if (!latest[s.ticker]) latest[s.ticker] = s;
  });

  tbody.innerHTML = Object.values(latest)
    .sort((a, b) => b.change_pct - a.change_pct)
    .map(s => {
      const sign = s.change_pct >= 0 ? '+' : '';
      const cls  = s.change_pct >= 0 ? 'up' : 'down';
      const arrow= s.change_pct >= 0 ? '▲' : '▼';
      return `<tr>
        <td><strong>${s.ticker}</strong></td>
        <td>$${s.price.toFixed(2)}</td>
        <td class="${cls}">${arrow} ${sign}${s.change_pct.toFixed(2)}%</td>
        <td>${fmt(s.captured_at)}</td>
      </tr>`;
    }).join('');
}

// ── Emails tab ─────────────────────────────────────────────────────────────
async function loadEmails() {
  const res = await fetch(`${API}/api/emails`);
  const emails = await res.json();
  const tbody = document.querySelector('#emailsTable tbody');
  tbody.innerHTML = emails.map(e => `<tr>
    <td>${AGENT_META[e.agent]?.emoji || '🤖'} ${e.agent}</td>
    <td>${e.subject}</td>
    <td>${e.recipient}</td>
    <td>${fmt(e.sent_at)}</td>
    <td><span class="badge ${e.success ? 'badge-success' : 'badge-failed'}">${e.success ? 'sent' : 'failed'}</span></td>
  </tr>`).join('');
}

// ── Logs tab ───────────────────────────────────────────────────────────────
async function loadLogs() {
  const agent = $('logAgentFilter').value;
  const url = `${API}/api/logs?limit=200${agent ? '&agent=' + agent : ''}`;
  const res = await fetch(url);
  const logs = await res.json();
  const container = $('logsContainer');
  container.innerHTML = logs.map(l => `
    <div class="log-row">
      <span class="log-ts">${new Date(l.ts).toLocaleTimeString()}</span>
      <span class="log-agent">${l.agent}</span>
      <span class="log-level ${l.level}">${l.level}</span>
      <span class="log-msg">${l.message}</span>
    </div>`).join('');
}

// ── Load metrics history ───────────────────────────────────────────────────
async function loadMetricsHistory() {
  const res = await fetch(`${API}/api/metrics/history?limit=30`);
  const data = await res.json();
  metricsHistory = data;
  drawChart();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
async function init() {
  // Load initial status
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    updateMetrics(data.metrics || {});
    updateLLMStats(data.llm_stats || {});
    updateOllama(data.ollama_running);
    agents = data.agents || {};
    renderAgentCards();
    renderAgentDetails();
  } catch (e) {
    console.warn('Initial status fetch failed — will retry via WS', e);
  }

  await loadMetricsHistory();

  // Periodic refresh for non-WS data
  setInterval(refreshAgentStatus, 10000);
  setInterval(() => {
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab?.id === 'tab-logs') loadLogs();
  }, 15000);

  connectWS();
}

window.addEventListener('resize', drawChart);
init();
