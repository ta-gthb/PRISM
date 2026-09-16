// ─── Utility Functions ──────────────────────────────────────────────

// IST clock
function getIST() {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const h = ist.getHours(), m = ist.getMinutes();
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hh = h % 12 || 12;
  return `${hh}:${String(m).padStart(2, '0')} ${ampm}`;
}

function getGreeting() {
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const h = now.getHours();
  if (h < 12) return t('greeting.morning');
  if (h < 17) return t('greeting.afternoon');
  return t('greeting.evening');
}

// Theme
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('lm_theme', theme);
}

function toggleTheme() {
  const current = localStorage.getItem('lm_theme') || 'light';
  applyTheme(current === 'light' ? 'dark' : 'light');
  renderGlobalBar();
}

function initTheme() {
  const stored = localStorage.getItem('lm_theme');
  const pref = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  applyTheme(stored || pref);
}

// Toast notifications
function showToast(msg, type = 'info', duration = 3500) {
  let stack = document.querySelector('.toast-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      ${type === 'success'
        ? '<path d="M3 8l3 3 7-7" stroke="white" stroke-width="1.5" stroke-linecap="round"/>'
        : type === 'error'
        ? '<path d="M4 4l8 8M12 4l-8 8" stroke="white" stroke-width="1.5" stroke-linecap="round"/>'
        : '<circle cx="8" cy="8" r="6.5" stroke="white" stroke-width="1.2"/><path d="M8 5v4M8 11v.5" stroke="white" stroke-width="1.2" stroke-linecap="round"/>'}
    </svg>
    ${msg}`;
  stack.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

// Format date
function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// Compliance badge HTML
function complianceBadge(status) {
  const map = {
    compliant: ['badge-compliant', '✓ Compliant'],
    violation: ['badge-violation', '✗ Violation'],
    partial:   ['badge-warning',   '⚠ Partial'],
  };
  const [cls, lbl] = map[status] || ['badge-navy', status];
  return `<span class="badge ${cls}">${lbl}</span>`;
}

// Score ring SVG
function scoreRingHTML(score) {
  const r = 34, circ = 2 * Math.PI * r;
  const dash = ((score / 100) * circ).toFixed(1);
  const color = score >= 80 ? '#166534' : score >= 50 ? '#d97706' : '#991b1b';
  return `
    <div class="score-ring">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle class="score-ring-track" cx="40" cy="40" r="${r}" />
        <circle class="score-ring-fill" cx="40" cy="40" r="${r}"
          stroke="${color}"
          stroke-dasharray="${dash} ${circ.toFixed(1)}"
          stroke-dashoffset="0" />
      </svg>
      <div class="score-ring-label">
        <span class="score-ring-value" style="color:${color}">${score}</span>
        <span class="score-ring-pct">/ 100</span>
      </div>
    </div>`;
}

// Severity dot
function severityDot(severity) {
  const cls = { critical: 'critical', major: 'major', minor: 'minor' }[severity] || 'minor';
  return `<span class="violation-dot ${cls}"></span>`;
}

// ─── Global Controls Bar ────────────────────────────────────────────
function renderGlobalBar() {
  const theme = localStorage.getItem('lm_theme') || 'light';
  const lang  = localStorage.getItem('lm_lang')  || 'en';
  const activeLang = LANGUAGES.find(l => l.code === lang) || LANGUAGES[0];

  let bar = document.getElementById('global-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'global-bar';
    bar.className = 'global-bar';
    document.body.appendChild(bar);
  }

  bar.innerHTML = `
    <!-- IST clock -->
    <div class="ctrl-pill ist-badge" id="ist-clock" title="Indian Standard Time">
      <span style="width:7px;height:7px;border-radius:50%;background:#34d399;flex-shrink:0;display:inline-block"></span>
      <span id="ist-time">${getIST()}</span> IST
    </div>

    <!-- Language picker -->
    <div style="position:relative" id="lang-wrap">
      <button class="ctrl-pill" onclick="toggleLangMenu()" aria-label="Language">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6.4" stroke="currentColor" stroke-width="1.2"/>
          <path d="M1.6 8h12.8M8 1.6c1.8 2 1.8 10.8 0 12.8M8 1.6c-1.8 2-1.8 10.8 0 12.8" stroke="currentColor" stroke-width="1.2"/>
        </svg>
        <span>${activeLang.native}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style="opacity:.5">
          <path d="M2 3.5l3 3 3-3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </button>
      <div class="lang-dropdown" id="lang-menu" style="display:none">
        ${LANGUAGES.map(l => `
          <div class="lang-option ${l.code === lang ? 'active' : ''}" onclick="setLang('${l.code}')">
            <span>${l.native}</span>
            <span class="lang-code">${l.label}</span>
          </div>`).join('')}
      </div>
    </div>

    <!-- Theme toggle -->
    <button class="ctrl-pill" onclick="toggleTheme()" title="${theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}">
      ${theme === 'dark'
        ? `<svg width="14" height="14" viewBox="0 0 16 16" fill="none">
             <circle cx="8" cy="8" r="3.2" stroke="currentColor" stroke-width="1.2"/>
             <path d="M8 1v1.6M8 13.4V15M1 8h1.6M13.4 8H15M3 3l1.1 1.1M11.9 11.9L13 13M13 3l-1.1 1.1M4.1 11.9L3 13" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
           </svg><span>Light</span>`
        : `<svg width="14" height="14" viewBox="0 0 16 16" fill="none">
             <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
           </svg><span>Dark</span>`}
    </button>`;

  // Tick clock every minute
  clearInterval(window._clockInterval);
  window._clockInterval = setInterval(() => {
    const el = document.getElementById('ist-time');
    if (el) el.textContent = getIST();
  }, 30_000);
}

function toggleLangMenu() {
  const menu = document.getElementById('lang-menu');
  if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

function setLang(code) {
  localStorage.setItem('lm_lang', code);
  document.documentElement.setAttribute('lang', code);
  toggleLangMenu();
  renderGlobalBar();
  if (typeof onLangChange === 'function') onLangChange(code);
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
  const wrap = document.getElementById('lang-wrap');
  const menu = document.getElementById('lang-menu');
  if (menu && wrap && !wrap.contains(e.target)) menu.style.display = 'none';
});

// Sidebar nav active state
function initNavActive(pageId) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === pageId);
  });
}

// Loading spinner helper
function setLoading(btn, loading, label) {
  if (loading) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${label || 'Loading…'}`;
  } else {
    btn.disabled = false;
    btn.innerHTML = label || btn.dataset.label || 'Submit';
  }
}

// File size formatter
function fmtFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
