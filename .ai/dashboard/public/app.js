/* ═══════════════════════════════════════════════════════════
   Workflow Dashboard — Client Application Logic
   2-second polling, dynamic rendering, inline artifact preview
   ═══════════════════════════════════════════════════════════ */

const STAGES = [
  { key: 'requirement', label: 'Requirements', short: 'REQ', icon: '📋' },
  { key: 'hld',         label: 'High-Level Design', short: 'HLD', icon: '🏗️' },
  { key: 'lld',         label: 'Low-Level Design', short: 'LLD', icon: '🔩' },
  { key: 'planning',    label: 'Planning', short: 'PLAN', icon: '📝' },
  { key: 'implementation', label: 'Implementation', short: 'IMPL', icon: '⚙️' },
  { key: 'review',      label: 'Code Review', short: 'REV', icon: '🔍' },
  { key: 'testing',     label: 'QA & Browser', short: 'QA', icon: '🧪' },
];

let state = {
  project: null,
  metrics: null,
  expandedStage: null,
  activeArtifact: null,
};

// ═══ POLLING ═══
async function poll() {
  try {
    const [projectRes, metricsRes] = await Promise.all([
      fetch('/api/state').then(r => r.json()),
      fetch('/api/metrics').then(r => r.json()),
    ]);
    state.project = projectRes;
    state.metrics = metricsRes;
    render();
  } catch (e) {
    console.warn('Poll failed:', e);
  }
}

// Start polling
poll();
setInterval(poll, 2000);

// ═══ RENDER ORCHESTRATOR ═══
function render() {
  renderPipeline();
  renderStats();
  renderStageTable();
  renderCharts();
  renderTimeline();
  renderHeaderStatus();
}

// ═══ HEADER STATUS ═══
function renderHeaderStatus() {
  const m = state.metrics;
  if (!m) return;
  
  const elapsed = formatDuration(m.elapsed_seconds);
  document.getElementById('elapsed-timer').textContent = `⏱ ${elapsed}`;
  document.getElementById('last-refresh').textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

// ═══ PIPELINE STEPPER ═══
function renderPipeline() {
  const p = state.project;
  if (!p) return;
  
  const completed = p.completed_stages || [];
  const current = p.current_stage || '';
  const track = document.getElementById('pipeline-track');
  
  let html = '';
  STAGES.forEach((s, i) => {
    const isComplete = completed.includes(s.key);
    const isActive = current === s.key;
    const circleClass = isComplete ? 'complete' : isActive ? 'active' : '';
    const numClass = isComplete ? 'complete' : isActive ? 'active' : '';
    const nameClass = isComplete ? 'complete' : isActive ? 'active' : '';
    
    html += `
      <div class="pipeline-node">
        <div class="pipeline-circle ${circleClass}">
          ${s.icon}
          <span class="pipeline-number ${numClass}">${i + 1}</span>
        </div>
        <span class="pipeline-name ${nameClass}">${s.short}</span>
      </div>
    `;
    
    if (i < STAGES.length - 1) {
      const fillClass = isComplete ? 'complete' : isActive ? 'active' : '';
      html += `
        <div class="pipeline-connector">
          <div class="pipeline-connector-fill ${fillClass}"></div>
        </div>
      `;
    }
  });
  
  track.innerHTML = html;
}

// ═══ STAT CARDS ═══
function renderStats() {
  const m = state.metrics;
  const p = state.project;
  if (!m || !p) return;
  
  const completed = (p.completed_stages || []).length;
  const passRate = completed > 0 ? Math.round((completed / STAGES.length) * 100) : 0;
  
  const grid = document.getElementById('stats-grid');
  grid.innerHTML = `
    <div class="stat-card emerald">
      <div class="stat-card-label">Total Steps</div>
      <div class="stat-card-value">${m.total_lines.toLocaleString()}</div>
      <div class="stat-card-sub">${m.planner_responses} planner responses</div>
    </div>
    <div class="stat-card blue">
      <div class="stat-card-label">Tool Calls</div>
      <div class="stat-card-value">${m.tool_calls.toLocaleString()}</div>
      <div class="stat-card-sub">${m.code_edits} code edits · ${m.commands_run} commands</div>
    </div>
    <div class="stat-card indigo">
      <div class="stat-card-label">Pipeline Duration</div>
      <div class="stat-card-value">${formatDuration(m.elapsed_seconds)}</div>
      <div class="stat-card-sub">${m.user_inputs} user interactions</div>
    </div>
    <div class="stat-card amber">
      <div class="stat-card-label">Stage Pass Rate</div>
      <div class="stat-card-value">${passRate}%</div>
      <div class="stat-card-sub">${completed} / ${STAGES.length} stages complete</div>
    </div>
  `;
}

// ═══ STAGE DETAIL TABLE ═══
function renderStageTable() {
  const p = state.project;
  if (!p) return;
  
  const stages = p.stages || {};
  const completed = p.completed_stages || [];
  const current = p.current_stage || '';
  const table = document.getElementById('stage-table');
  
  let html = `
    <div class="stage-table-header">
      <span>#</span>
      <span>Stage</span>
      <span>Status</span>
      <span>Duration</span>
      <span class="text-right">Steps</span>
      <span class="text-right">Tools</span>
      <span class="text-right">Edits</span>
      <span class="text-center">Verdict</span>
      <span></span>
    </div>
  `;
  
  STAGES.forEach((meta, i) => {
    const s = stages[meta.key];
    const isComplete = completed.includes(meta.key);
    const isActive = current === meta.key;
    const isExpanded = state.expandedStage === meta.key;
    
    // Status
    let statusBadge;
    if (isComplete) statusBadge = '<span class="badge complete">✓ Complete</span>';
    else if (isActive) statusBadge = '<span class="badge active">⟳ Active</span>';
    else statusBadge = '<span class="badge pending">· Pending</span>';
    
    // Verdict
    let verdictHtml = '<span class="text-muted">—</span>';
    if (s && s.verdict) {
      const isPass = ['APPROVED', 'ALL_PASS', 'BUILD_PASS'].includes(s.verdict);
      verdictHtml = `<span class="verdict-badge ${isPass ? 'pass' : 'fail'}">${s.verdict}</span>`;
    }
    
    const duration = s ? formatDuration(s.duration_seconds) : '—';
    const tokens = s ? s.tokens || {} : {};
    
    html += `
      <div class="stage-row" onclick="toggleStage('${meta.key}')">
        <span class="stage-row-num">${i + 1}</span>
        <span class="stage-row-name"><span class="icon">${meta.icon}</span> ${meta.label}</span>
        ${statusBadge}
        <span>${duration}</span>
        <span class="text-right text-indigo">${tokens.input ? fmtK(tokens.input) : '—'}</span>
        <span class="text-right text-emerald">${tokens.output ? fmtK(tokens.output) : '—'}</span>
        <span class="text-right text-amber">${tokens.total ? fmtK(tokens.total) : '—'}</span>
        <span class="text-center">${verdictHtml}</span>
        <span class="stage-expand ${isExpanded ? 'open' : ''}">▸</span>
      </div>
    `;
    
    // Expanded detail
    if (s) {
      html += `
        <div class="stage-detail ${isExpanded ? 'open' : ''}" id="detail-${meta.key}">
          <div class="stage-detail-grid">
            <div>
              <div class="detail-item-label">Started</div>
              <div class="detail-item-value">${new Date(s.started_at).toLocaleTimeString()}</div>
            </div>
            <div>
              <div class="detail-item-label">Completed</div>
              <div class="detail-item-value">${new Date(s.completed_at).toLocaleTimeString()}</div>
            </div>
            <div>
              <div class="detail-item-label">Artifact</div>
              <div class="detail-item-value">
                ${s.artifact
                  ? `<a href="#" onclick="event.preventDefault(); event.stopPropagation(); loadArtifact('${s.artifact}')">${s.artifact.split('/').pop()} ↗</a>`
                  : '<span class="text-muted">Source code only</span>'
                }
              </div>
            </div>
            <div>
              <div class="detail-item-label">Errors</div>
              <div class="detail-item-value" style="color: ${s.errors.length > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)'}">
                ${s.errors.length > 0 ? s.errors.length + ' errors' : '0 errors'}
              </div>
            </div>
          </div>
          <div>
            <div class="detail-item-label">Skills Used</div>
            <div class="skills-list">
              ${(s.skills_used || []).map(sk => `<span class="skill-tag">${sk}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
    }
  });
  
  table.innerHTML = html;
}

// ═══ CHARTS ═══
function renderCharts() {
  const m = state.metrics;
  if (!m || !m.step_types) return;
  
  const chartSection = document.getElementById('charts-section');
  const types = m.step_types;
  
  // Find max for scaling
  const values = [
    types.PLANNER_RESPONSE || 0,
    types.CODE_ACTION || 0,
    types.RUN_COMMAND || 0,
    types.VIEW_FILE || 0,
    types.LIST_DIRECTORY || 0,
    types.USER_INPUT || 0,
    types.ASK_QUESTION || 0,
  ];
  const maxVal = Math.max(...values, 1);
  
  const rows = [
    { label: 'PLAN', value: types.PLANNER_RESPONSE || 0, cls: 'planner' },
    { label: 'CODE', value: types.CODE_ACTION || 0, cls: 'code' },
    { label: 'CMD', value: types.RUN_COMMAND || 0, cls: 'tools' },
    { label: 'VIEW', value: types.VIEW_FILE || 0, cls: 'planner' },
    { label: 'DIR', value: types.LIST_DIRECTORY || 0, cls: 'tools' },
    { label: 'USER', value: types.USER_INPUT || 0, cls: 'code' },
    { label: 'ASK', value: types.ASK_QUESTION || 0, cls: 'planner' },
  ];
  
  let html = `
    <div class="chart-title">
      <span>Step Distribution by Type</span>
      <div class="chart-legend">
        <span><span class="chart-legend-dot" style="background:rgba(99,102,241,0.6)"></span>Planner</span>
        <span><span class="chart-legend-dot" style="background:rgba(16,185,129,0.6)"></span>Tools</span>
        <span><span class="chart-legend-dot" style="background:rgba(245,158,11,0.6)"></span>Code</span>
      </div>
    </div>
  `;
  
  rows.forEach(r => {
    const pct = (r.value / maxVal) * 100;
    html += `
      <div class="chart-row">
        <span class="chart-label">${r.label}</span>
        <div class="chart-bar-track">
          <div class="chart-bar-segment ${r.cls}" style="width:${pct}%"></div>
        </div>
        <span class="chart-value">${r.value}</span>
      </div>
    `;
  });
  
  chartSection.innerHTML = html;
}

// ═══ TIMELINE ═══
function renderTimeline() {
  const p = state.project;
  if (!p || !p.history) return;
  
  const section = document.getElementById('timeline-section');
  let html = '<div class="timeline-title">Activity Timeline</div>';
  
  const history = p.history.slice().reverse(); // Latest first
  
  history.forEach(entry => {
    const time = new Date(entry.timestamp).toLocaleTimeString();
    const dotClass = entry.event || 'completed';
    const stageLabel = STAGES.find(s => s.key === entry.stage)?.label || entry.stage;
    const eventLabel = (entry.event || entry.status || '').toUpperCase();
    
    html += `
      <div class="timeline-entry">
        <span class="timeline-dot ${dotClass}"></span>
        <span class="timeline-time">${time}</span>
        <span class="timeline-text">
          <span class="timeline-stage">${stageLabel}</span> → ${eventLabel}
        </span>
      </div>
    `;
  });
  
  section.innerHTML = html;
}

// ═══ ARTIFACT VIEWER ═══
async function loadArtifact(artifactPath) {
  const body = document.getElementById('artifact-body');
  const empty = document.getElementById('artifact-empty');
  const header = document.querySelector('.artifact-header');
  
  try {
    const res = await fetch(`/api/artifact?path=${encodeURIComponent(artifactPath)}`);
    const md = await res.text();
    
    // Render markdown using marked.js
    body.innerHTML = marked.parse(md);
    body.style.display = 'block';
    empty.style.display = 'none';
    header.innerHTML = `
      <span>${artifactPath.split('/').pop()}</span>
      <button class="artifact-close" onclick="closeArtifact()">✕ Close</button>
    `;
    
    // Scroll artifact section into view
    document.getElementById('artifact-section').scrollTop = 0;
  } catch (e) {
    body.innerHTML = `<p style="color:var(--accent-rose)">Failed to load artifact: ${artifactPath}</p>`;
    body.style.display = 'block';
    empty.style.display = 'none';
  }
}

function closeArtifact() {
  document.getElementById('artifact-body').style.display = 'none';
  document.getElementById('artifact-empty').style.display = 'block';
  document.querySelector('.artifact-header').innerHTML = '<span>Artifact Preview</span>';
}

// ═══ UTILITIES ═══
function toggleStage(key) {
  state.expandedStage = state.expandedStage === key ? null : key;
  renderStageTable();
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
  }
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function fmtK(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}
