/* ============================================================
   Thermography Compliance AI — Main Application JS
   Dashboard, Inspections, Equipment, Alerts, Upload, AI Chat
   ============================================================ */

'use strict';

// ── State ──────────────────────────────────────────────────
const STATE = {
  currentSection: 'dashboard',
  inspectionsPage: 1,
  inspectionsTotal: 0,
  chatHistory: [],
  isStreaming: false,
  selectedFile: null,
  dashboardData: null,
};

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  checkAIStatus();
  setInterval(checkAIStatus, 30000);
  navigateTo('dashboard');
  setupNavigation();
});

function setupNavigation() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const section = item.dataset.section;
      if (section) navigateTo(section);
    });
  });
}

function navigateTo(section) {
  STATE.currentSection = section;

  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });

  // Update sections
  document.querySelectorAll('.content-section').forEach(el => {
    el.classList.remove('active');
  });
  const target = document.getElementById(`section-${section}`);
  if (target) target.classList.add('active');

  // Update breadcrumb
  const labels = {
    dashboard: 'Dashboard', inspections: 'Inspection History',
    equipment: 'Equipment Registry', alerts: 'Critical Alerts',
    upload: 'Upload & Scan', reports: 'Compliance Reports', ai: 'AI Assistant'
  };
  document.getElementById('breadcrumb').textContent = labels[section] || section;

  // Load section data
  const loaders = {
    dashboard: loadDashboard,
    inspections: loadInspections,
    equipment: loadEquipment,
    alerts: loadAlerts,
    reports: loadReportsSummary,
  };
  if (loaders[section]) loaders[section]();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── Clock ──────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('header-time');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-US', { hour12: false }) + ' UTC';
  }
}

// ── API Helper ─────────────────────────────────────────────
async function api(path, opts = {}) {
  try {
    const res = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API error [${path}]:`, err);
    return null;
  }
}

// ── Dashboard ──────────────────────────────────────────────
async function loadDashboard() {
  const data = await api('/dashboard/stats');
  if (!data) return;
  STATE.dashboardData = data;

  // KPI values
  animateCount('kpi-critical-val', data.critical_alerts);
  animateCount('kpi-serious-val', data.serious_alerts);
  setText('kpi-compliance-val', `${data.avg_compliance_score}%`);
  animateCount('kpi-total-val', data.total_inspections);
  animateCount('kpi-equipment-val', data.equipment_monitored);
  animateCount('kpi-open-val', data.open_alerts);
  setText('kpi-monthly', `${data.inspections_this_month} this month`);
  setText('kpi-compliance-trend', data.compliance_trend || 'NFPA 70B Score');

  // Remove shimmer
  document.querySelectorAll('.kpi-card').forEach(el => el.classList.remove('loading-shimmer'));

  // Nav badges
  const critEl = document.getElementById('nav-critical-count');
  const alertsEl = document.getElementById('nav-alerts-count');
  if (critEl) { critEl.textContent = data.critical_alerts; critEl.style.display = data.critical_alerts > 0 ? 'inline' : 'none'; }
  if (alertsEl) { alertsEl.textContent = data.open_alerts; alertsEl.style.display = data.open_alerts > 0 ? 'inline' : 'none'; }

  // Severity bars
  renderSeverityBars(data.severity_distribution, data.total_inspections);

  // Compliance gauge
  updateGauge(data.avg_compliance_score);

  // Recent alerts
  loadRecentAlerts();
}

function renderSeverityBars(dist, total) {
  const container = document.getElementById('severity-bars');
  if (!container || !dist) return;
  const colors = { Critical: '#ef4444', Serious: '#f97316', Moderate: '#eab308', Minor: '#3b82f6', Normal: '#22c55e' };
  container.innerHTML = Object.entries(colors).map(([sev, color]) => {
    const count = dist[sev] || 0;
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    return `
      <div class="sev-bar-row">
        <span class="sev-label">${sev}</span>
        <div class="sev-bar-track">
          <div class="sev-bar" style="width:0%;background:${color}" data-target="${pct}"></div>
        </div>
        <span class="sev-count">${count}</span>
      </div>`;
  }).join('');

  // Animate bars
  requestAnimationFrame(() => {
    document.querySelectorAll('.sev-bar[data-target]').forEach(bar => {
      setTimeout(() => { bar.style.width = bar.dataset.target + '%'; }, 100);
    });
  });
}

function updateGauge(score) {
  const arc = document.getElementById('gauge-arc');
  const text = document.getElementById('gauge-text');
  const badge = document.getElementById('compliance-badge');
  if (!arc) return;

  const circumference = 251.2;
  const offset = circumference - (score / 100) * circumference;
  arc.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)';
  arc.style.strokeDashoffset = offset;
  if (text) text.textContent = `${score}%`;

  const status = score >= 90 ? 'Excellent' : score >= 75 ? 'Good' : score >= 60 ? 'Fair' : score >= 40 ? 'Poor' : 'Critical';
  if (badge) {
    badge.textContent = status;
    badge.className = 'chart-badge' + (score < 60 ? ' danger' : '');
  }
}

async function loadRecentAlerts() {
  const data = await api('/dashboard/recent-alerts');
  const container = document.getElementById('dashboard-alerts-list');
  if (!container) return;
  if (!data || !data.alerts || data.alerts.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted);font-size:12px;padding:12px">No critical alerts found.</p>';
    return;
  }
  const sevColors = { Critical: '#ef4444', Serious: '#f97316' };
  container.innerHTML = data.alerts.slice(0, 5).map(a => `
    <div class="alert-row" onclick="navigateTo('alerts')">
      <div class="alert-sev-dot" style="background:${sevColors[a.severity] || '#f97316'}"></div>
      <div class="alert-info">
        <div class="alert-eq">${a.equipment_name || 'Unknown'}</div>
        <div class="alert-detail">${a.location || ''} · ${a.standard || 'NFPA 70B'}</div>
      </div>
      <div class="alert-delta-t">ΔT ${a.delta_t || '—'}°C</div>
    </div>`).join('');
}

// ── Inspections ────────────────────────────────────────────
async function loadInspections() {
  const severity = document.getElementById('filter-severity')?.value || '';
  const status = document.getElementById('filter-status')?.value || '';
  const page = STATE.inspectionsPage;

  let url = `/inspections/?page=${page}&limit=20`;
  if (severity) url += `&severity=${severity}`;
  if (status) url += `&status=${encodeURIComponent(status)}`;

  const data = await api(url);
  const tbody = document.getElementById('inspections-tbody');
  if (!tbody) return;

  if (!data || !data.inspections || data.inspections.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="loading-cell">No inspections found.</td></tr>';
    return;
  }

  STATE.inspectionsTotal = data.total;
  tbody.innerHTML = data.inspections.map(ins => `
    <tr onclick="downloadReport('${ins.inspection_id}')" style="cursor:pointer" title="Click to download report">
      <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">${ins.inspection_id || '—'}</td>
      <td style="color:var(--text-primary);font-weight:500">${ins.equipment_name || '—'}</td>
      <td>${ins.location || '—'}</td>
      <td>${ins.inspector || '—'}</td>
      <td style="font-family:var(--font-mono);color:var(--thermal-serious)">${ins.hotspot_temp || '—'}°C</td>
      <td style="font-family:var(--font-mono);color:var(--thermal-accent)">ΔT ${ins.delta_t || '—'}°C</td>
      <td><span class="sev-badge ${ins.severity}">${ins.severity || '—'}</span></td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="flex:1;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden">
            <div style="height:100%;width:${ins.compliance_score || 0}%;background:${scoreColor(ins.compliance_score)};border-radius:2px"></div>
          </div>
          <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-secondary);width:28px">${ins.compliance_score || 0}%</span>
        </div>
      </td>
      <td><span class="status-badge ${(ins.status || '').replace(' ', '-')}">${ins.status || '—'}</span></td>
      <td style="color:var(--text-muted);font-size:11px">${formatDate(ins.timestamp)}</td>
    </tr>`).join('');

  renderPagination(data.page, data.pages);
}

function renderPagination(current, total) {
  const container = document.getElementById('inspections-pagination');
  if (!container || total <= 1) { if (container) container.innerHTML = ''; return; }
  let html = '';
  if (current > 1) html += `<button class="page-btn" onclick="goPage(${current - 1})">← Prev</button>`;
  const start = Math.max(1, current - 2), end = Math.min(total, current + 2);
  for (let i = start; i <= end; i++) {
    html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
  }
  if (current < total) html += `<button class="page-btn" onclick="goPage(${current + 1})">Next →</button>`;
  container.innerHTML = html;
}

function goPage(page) {
  STATE.inspectionsPage = page;
  loadInspections();
}

async function downloadReport(inspectionId) {
  const a = document.createElement('a');
  a.href = `/api/reports/generate/${inspectionId}`;
  a.download = `report_${inspectionId}.txt`;
  a.click();
}

// ── Equipment ──────────────────────────────────────────────
async function loadEquipment() {
  const data = await api('/equipment/');
  const grid = document.getElementById('equipment-grid');
  if (!grid) return;

  const equipment = data?.equipment || [];
  if (equipment.length === 0) {
    grid.innerHTML = '<p style="color:var(--text-muted)">No equipment found.</p>';
    return;
  }

  const icons = {
    'Electrical Panel': '⚡', 'Power Transformer': '🔌', 'Motor Control Center': '⚙️',
    'Switchgear': '🔧', 'Induction Motor': '🔄', 'UPS': '🔋', 'Bus Duct': '📡', 'HVAC Motor': '🌀'
  };

  grid.innerHTML = equipment.map(eq => {
    const health = eq.health_score || 85;
    const hColor = health >= 80 ? '#22c55e' : health >= 60 ? '#eab308' : health >= 40 ? '#f97316' : '#ef4444';
    return `
      <div class="eq-card" onclick="showEquipmentDetail('${eq.id}')">
        <div class="eq-card-header">
          <div class="eq-type-icon">${icons[eq.type] || '⚙️'}</div>
          <span class="eq-criticality crit-${eq.criticality}">${eq.criticality}</span>
        </div>
        <div class="eq-name">${eq.name}</div>
        <div class="eq-type">${eq.type}</div>
        <div class="eq-location">📍 ${eq.location}</div>
        <div class="eq-health-bar">
          <div class="eq-health-fill" style="width:${health}%;background:${hColor}"></div>
        </div>
        <div class="eq-health-label">
          <span>Health Score</span>
          <span style="color:${hColor};font-weight:600">${health}%</span>
        </div>
      </div>`;
  }).join('');
}

async function showEquipmentDetail(id) {
  const data = await api(`/equipment/${id}`);
  if (!data) return;
  // Navigate to inspections filtered by equipment
  navigateTo('inspections');
  setTimeout(() => loadInspections(), 100);
}

// ── Alerts ─────────────────────────────────────────────────
async function loadAlerts() {
  const data = await api('/inspections/critical');
  const container = document.getElementById('alerts-container');
  if (!container) return;

  const alerts = data?.inspections || [];
  if (alerts.length === 0) {
    container.innerHTML = `
      <div class="glass-card" style="padding:40px;text-align:center;color:var(--text-muted)">
        <div style="font-size:48px;margin-bottom:16px">✅</div>
        <div style="font-size:16px;font-weight:600;color:var(--thermal-normal)">No Critical Alerts</div>
        <div style="margin-top:8px">All equipment operating within acceptable parameters</div>
      </div>`;
    return;
  }

  container.innerHTML = alerts.map(a => `
    <div class="alert-card ${a.severity}">
      <div class="alert-card-icon">${a.severity === 'Critical' ? '🔥' : '⚡'}</div>
      <div class="alert-card-body">
        <div class="alert-card-header">
          <span class="alert-card-title">${a.equipment_name || '—'}</span>
          <span class="sev-badge ${a.severity}">${a.severity}</span>
          <span class="status-badge ${(a.status || '').replace(' ', '-')}">${a.status || '—'}</span>
        </div>
        <div class="alert-finding">${a.finding || '—'}</div>
        <div class="alert-recommendation">→ ${a.recommendation || '—'}</div>
        <div class="alert-card-meta">
          <div class="alert-meta-item">📍 ${a.location || '—'}</div>
          <div class="alert-meta-item">🌡️ Hotspot: ${a.hotspot_temp || '—'}°C</div>
          <div class="alert-meta-item">ΔT: ${a.delta_t || '—'}°C</div>
          <div class="alert-meta-item">📋 ${a.standard || 'NFPA 70B'}</div>
          <div class="alert-meta-item">🕐 ${formatDate(a.timestamp)}</div>
        </div>
      </div>
      <div class="alert-card-actions">
        <button class="btn-report" onclick="downloadReport('${a.inspection_id}')">⬇ Report</button>
        <span style="font-family:var(--font-mono);font-size:18px;font-weight:800;color:${a.severity === 'Critical' ? '#ef4444' : '#f97316'}">ΔT ${a.delta_t}°C</span>
      </div>
    </div>`).join('');
}

// ── Reports Summary ────────────────────────────────────────
async function loadReportsSummary() {
  const data = await api('/reports/summary');
  const el = document.getElementById('reports-summary');
  if (!el || !data) return;
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px">
      <div class="glass-card" style="padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:800;color:var(--text-primary)">${data.total_reports || 0}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">TOTAL REPORTS</div>
      </div>
      <div class="glass-card" style="padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:800;color:#ef4444">${data.critical_findings || 0}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">CRITICAL FINDINGS</div>
      </div>
      <div class="glass-card" style="padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:800;color:#22c55e">${data.avg_compliance || 0}%</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">AVG COMPLIANCE</div>
      </div>
    </div>
    <p style="color:var(--text-muted);margin-top:16px;font-size:12px">
      Go to <strong style="color:var(--thermal-accent)">Inspection History</strong> and click any row to download its compliance report.
    </p>`;
}

// ── Upload & Thermal Analysis ──────────────────────────────
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.add('dragover');
}
function handleDragLeave(e) {
  document.getElementById('upload-zone').classList.remove('dragover');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) setSelectedFile(file);
}
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) setSelectedFile(file);
}

function setSelectedFile(file) {
  STATE.selectedFile = file;
  const zone = document.getElementById('upload-zone');
  const btn = document.getElementById('upload-btn');
  zone.innerHTML = `
    <div class="upload-icon">🖼️</div>
    <h3>${file.name}</h3>
    <p>${(file.size / 1024).toFixed(1)} KB · ${file.type}</p>
    <button class="btn-ghost" onclick="clearFile()">Change File</button>`;
  if (btn) btn.disabled = false;
}

function clearFile() {
  STATE.selectedFile = null;
  const zone = document.getElementById('upload-zone');
  zone.innerHTML = `
    <div class="upload-icon">⬒</div>
    <h3>Drop Thermal Image Here</h3>
    <p>Supports JPEG, PNG, TIFF — IR camera exports</p>
    <input type="file" id="file-input" accept="image/*" onchange="handleFileSelect(event)" style="display:none">
    <button class="btn-primary" onclick="document.getElementById('file-input').click()">Browse Files</button>`;
  document.getElementById('upload-btn').disabled = true;
  document.getElementById('analysis-result').style.display = 'none';
}

async function uploadImage() {
  if (!STATE.selectedFile) return;
  const btn = document.getElementById('upload-btn');
  btn.disabled = true;
  btn.textContent = 'Analyzing...';

  const fd = new FormData();
  fd.append('file', STATE.selectedFile);
  fd.append('equipment_id', document.getElementById('upload-equipment').value);
  fd.append('inspector', document.getElementById('upload-inspector').value);
  fd.append('standard', document.getElementById('upload-standard').value);

  try {
    const res = await fetch('/api/uploads/thermal-image', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success && data.analysis) {
      showAnalysisResult(data);
    } else {
      alert('Analysis failed: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Upload failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Analyze Image';
  }
}

function showAnalysisResult(data) {
  const a = data.analysis;
  const card = document.getElementById('analysis-result');
  const content = document.getElementById('analysis-content');
  const sevColor = { Critical: '#ef4444', Serious: '#f97316', Moderate: '#eab308', Minor: '#3b82f6', Normal: '#22c55e' };
  const color = sevColor[a.severity] || '#94a3b8';

  content.innerHTML = `
    <div style="text-align:center;margin-bottom:20px">
      <span class="sev-badge ${a.severity}" style="font-size:14px;padding:6px 16px">${a.severity}</span>
      <div style="font-size:32px;font-weight:800;margin:12px 0;color:${color}">ΔT ${a.delta_t}°C</div>
      <div style="font-size:12px;color:var(--text-muted)">Compliance Score: ${a.compliance_score}/100</div>
    </div>
    <div class="analysis-row"><span class="analysis-key">Hotspot Temperature</span><span class="analysis-val" style="color:${color}">${a.hotspot_temp}°C</span></div>
    <div class="analysis-row"><span class="analysis-key">Ambient Temperature</span><span class="analysis-val">${a.ambient_temp}°C</span></div>
    <div class="analysis-row"><span class="analysis-key">Delta-T</span><span class="analysis-val" style="color:${color}">${a.delta_t}°C</span></div>
    <div class="analysis-row"><span class="analysis-key">Max Temperature</span><span class="analysis-val">${a.temp_max}°C</span></div>
    <div class="analysis-row"><span class="analysis-key">Mean Temperature</span><span class="analysis-val">${a.temp_mean}°C</span></div>
    <div class="analysis-row"><span class="analysis-key">Analysis Method</span><span class="analysis-val">${a.method}</span></div>
    <div class="analysis-row"><span class="analysis-key">Inspection ID</span><span class="analysis-val" style="font-size:11px">${data.inspection_id}</span></div>
    <div style="margin-top:16px;padding:12px;background:rgba(${a.severity==='Critical'?'239,68,68':'249,115,22'},0.08);border:1px solid rgba(${a.severity==='Critical'?'239,68,68':'249,115,22'},0.2);border-radius:8px">
      <div style="font-size:11px;font-weight:600;color:${color};margin-bottom:4px">FINDING</div>
      <div style="font-size:12px;color:var(--text-secondary)">${data.record?.finding || '—'}</div>
      <div style="font-size:11px;color:${color};margin-top:8px;font-style:italic">→ ${data.record?.recommendation || '—'}</div>
    </div>
    <button class="btn-primary btn-full" style="margin-top:16px" onclick="downloadReport('${data.inspection_id}')">⬇ Download Report</button>`;
  card.style.display = 'block';
}

// ── AI Assistant ───────────────────────────────────────────
async function checkAIStatus() {
  try {
    const data = await api('/ai/status');
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    const badge = document.getElementById('ai-model-badge');

    if (data?.ollama_available) {
      if (dot) { dot.className = 'status-dot online'; }
      if (text) text.textContent = 'AI Online · Llama 3';
      if (badge) badge.textContent = `⬡ ${data.model} · ${data.mcp_tools} MCP tools`;
    } else {
      if (dot) { dot.className = 'status-dot offline'; }
      if (text) text.textContent = 'AI Offline (fallback)';
      if (badge) badge.textContent = '⬡ Offline Mode';
    }
  } catch (e) {
    const dot = document.getElementById('status-dot');
    if (dot) dot.className = 'status-dot offline';
  }
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function sendSuggestion(btn) {
  const text = btn.textContent.replace(/^[^\w]+/, '').trim();
  document.getElementById('chat-input').value = text;
  sendMessage();
}

async function sendMessage() {
  if (STATE.isStreaming) return;
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // Add user message
  appendMessage('user', message);
  STATE.chatHistory.push({ role: 'user', content: message });

  // Hide suggestions
  const suggestions = document.getElementById('suggested-prompts');
  if (suggestions) suggestions.style.display = 'none';

  // Start streaming
  STATE.isStreaming = true;
  document.getElementById('chat-send-btn').disabled = true;

  // Show typing indicator
  const typingId = showTypingIndicator();

  try {
    await streamAIResponse(message, typingId);
  } catch (e) {
    removeTypingIndicator(typingId);
    appendMessage('assistant', `**Error:** ${e.message}`);
  } finally {
    STATE.isStreaming = false;
    document.getElementById('chat-send-btn').disabled = false;
    hideMCPIndicator();
  }
}

async function streamAIResponse(message, typingId) {
  const res = await fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: STATE.chatHistory.slice(-10)
    })
  });

  if (!res.ok) throw new Error(`Server error: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let assistantText = '';
  let msgEl = null;
  let removedTyping = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;

      try {
        const event = JSON.parse(jsonStr);

        if (event.type === 'tool_start') {
          showMCPIndicator(event.tool);
        } else if (event.type === 'tool_result') {
          updateMCPIndicator(event.tool, event.summary);
          setTimeout(hideMCPIndicator, 2000);
        } else if (event.type === 'text') {
          if (!removedTyping) {
            removeTypingIndicator(typingId);
            removedTyping = true;
          }
          assistantText += event.content;
          if (!msgEl) {
            msgEl = appendMessage('assistant', '');
          }
          updateMessageContent(msgEl, assistantText);
          scrollChat();
        } else if (event.type === 'done') {
          break;
        }
      } catch (e) { /* skip malformed events */ }
    }
  }

  if (!removedTyping) removeTypingIndicator(typingId);
  if (assistantText) {
    STATE.chatHistory.push({ role: 'assistant', content: assistantText });
  }
  scrollChat();
}

function appendMessage(role, content) {
  const container = document.getElementById('chat-container');
  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
  div.innerHTML = `
    <div class="msg-avatar">${isUser ? 'YOU' : 'AI'}</div>
    <div class="msg-content">
      <div class="msg-bubble">${isUser ? escHtml(content) : renderMarkdown(content)}</div>
      <div class="msg-time">${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</div>
    </div>`;
  container.appendChild(div);
  scrollChat();
  return div;
}

function updateMessageContent(msgEl, text) {
  const bubble = msgEl.querySelector('.msg-bubble');
  if (bubble) bubble.innerHTML = renderMarkdown(text);
}

function showTypingIndicator() {
  const container = document.getElementById('chat-container');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'chat-message assistant-message';
  div.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content">
      <div class="msg-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>`;
  container.appendChild(div);
  scrollChat();
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showMCPIndicator(tool) {
  const indicator = document.getElementById('mcp-indicator');
  const nameEl = document.getElementById('mcp-tool-name');
  if (indicator) {
    indicator.style.display = 'flex';
    if (nameEl) nameEl.textContent = `⬡ MCP: ${tool}() → MongoDB`;
  }
}

function updateMCPIndicator(tool, summary) {
  const nameEl = document.getElementById('mcp-tool-name');
  if (nameEl) nameEl.textContent = `✓ ${tool} — data retrieved`;
}

function hideMCPIndicator() {
  const indicator = document.getElementById('mcp-indicator');
  if (indicator) indicator.style.display = 'none';
}

function scrollChat() {
  const container = document.getElementById('chat-container');
  if (container) container.scrollTop = container.scrollHeight;
}

function clearChat() {
  STATE.chatHistory = [];
  const container = document.getElementById('chat-container');
  if (!container) return;
  container.innerHTML = `
    <div class="chat-message assistant-message">
      <div class="msg-avatar">AI</div>
      <div class="msg-content">
        <div class="msg-bubble">
          <p>Chat cleared. How can I help you with thermography analysis or compliance monitoring?</p>
        </div>
        <div class="msg-time">${new Date().toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit'})}</div>
      </div>
    </div>`;
  const suggestions = document.getElementById('suggested-prompts');
  if (suggestions) suggestions.style.display = 'flex';
}

// ── Markdown Renderer ──────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  let html = escHtml(text);

  // Code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`);
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  // Tables
  html = html.replace(/\|(.+)\|\n\|[-|: ]+\|\n((?:\|.+\|\n?)*)/g, (_, header, rows) => {
    const ths = header.split('|').filter(s => s.trim()).map(h => `<th>${h.trim()}</th>`).join('');
    const trs = rows.trim().split('\n').map(row => {
      const tds = row.split('|').filter(s => s.trim()).map(d => `<td>${d.trim()}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  });
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h4 style="margin:8px 0 4px;color:var(--text-primary)">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 style="margin:10px 0 6px;color:var(--text-primary)">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 style="margin:12px 0 8px;color:var(--text-primary)">$1</h2>');
  // Lists
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\n<ul>/g, '');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = `<p>${html}</p>`;
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<[hupot])/g, '$1');
  html = html.replace(/(<\/[hupot][^>]*>)<\/p>/g, '$1');

  return html;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Utilities ──────────────────────────────────────────────
function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el || target === undefined) return;
  const start = 0;
  const duration = 800;
  const startTime = performance.now();
  const update = (now) => {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + (target - start) * ease);
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function formatDate(ts) {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
  } catch { return '—'; }
}

function scoreColor(score) {
  if (!score) return '#475569';
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#3b82f6';
  if (score >= 55) return '#eab308';
  if (score >= 40) return '#f97316';
  return '#ef4444';
}
