/*
 * GhostTab AI — popup logic
 *
 * Permissions policy:
 * - Reads tabs only after the popup is opened and the user clicks "Save".
 * - Never reads browsing history.
 * - Sends only the URL, title, and domain of selected (checked) tabs to the
 *   configured GhostTab AI instance.
 */
const API = {
  base: '',
};

async function loadConfig() {
  const { gtBase = 'http://localhost:8000', gtToken = '' } = await chrome.storage.local.get(['gtBase', 'gtToken']);
  API.base = gtBase.replace(/\/$/, '');
  API.token = gtToken;
  return { gtBase, gtToken };
}

async function saveConfig(cfg) {
  await chrome.storage.local.set(cfg);
}

async function isSessionValid() {
  try {
    const r = await fetch(`${API.base}/api/extension/health/`, { credentials: 'include' });
    if (!r.ok) return false;
    const data = await r.json();
    return data.authenticated === true;
  } catch {
    return false;
  }
}

async function login(email, password) {
  const r = await fetch(`${API.base}/api/extension/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.error || `Login failed (${r.status})`);
  }
  return r.json();
}

async function loadTabs() {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  // Filter to http(s) only — never internal chrome:// pages
  return tabs
    .filter(t => /^https?:\/\//.test(t.url || ''))
    .map(t => {
      let domain = '';
      try { domain = new URL(t.url).hostname; } catch {}
      return {
        id: t.id,
        url: t.url,
        title: t.title || t.url,
        domain,
        selected: true,
      };
    });
}

function renderTabs(tabs) {
  const list = document.getElementById('tabList');
  list.innerHTML = '';
  if (!tabs.length) {
    list.innerHTML = '<li style="padding:12px;color:var(--text-soft);text-align:center;">No http(s) tabs in this window.</li>';
    return;
  }
  tabs.forEach(t => {
    const li = document.createElement('li');
    li.className = 'ext-tab-item';
    li.innerHTML = `
      <input type="checkbox" data-id="${t.id}" ${t.selected ? 'checked' : ''}>
      <div class="ext-tab-title">
        ${escapeHTML(t.title)}
        <div class="ext-tab-domain">${escapeHTML(t.domain)}</div>
      </div>
    `;
    li.querySelector('input').addEventListener('change', (e) => {
      t.selected = e.target.checked;
      updateCount(tabs);
    });
    list.appendChild(li);
  });
  updateCount(tabs);
}

function updateCount(tabs) {
  const n = tabs.filter(t => t.selected).length;
  document.getElementById('tabCount').textContent = `${n} tab${n === 1 ? '' : 's'} selected`;
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function setStatus(msg, type = '') {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'ext-status ' + type;
}

async function save(tabs) {
  const selected = tabs.filter(t => t.selected);
  if (!selected.length) {
    setStatus('Select at least one tab.', 'error');
    return;
  }
  const title = document.getElementById('projectTitle').value.trim() || 'Imported tabs';
  const autoGroup = document.getElementById('autoGroup').checked;
  const saveBtn = document.getElementById('saveBtn');
  saveBtn.disabled = true;
  setStatus('Sending to GhostTab AI…', 'loading');

  try {
    const r = await fetch(`${API.base}/api/extension/import/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(API.token ? { 'X-GhostTab-Token': API.token } : {}),
      },
      credentials: 'include',
      body: JSON.stringify({
        project_title: title,
        pages: selected.map(t => ({ url: t.url, title: t.title })),
        auto_group: autoGroup,
      }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || `Import failed (${r.status})`);
    setStatus(`Imported ${data.imported} page${data.imported === 1 ? '' : 's'}.`, 'success');
    setTimeout(() => window.close(), 1200);
  } catch (e) {
    setStatus(e.message, 'error');
  } finally {
    saveBtn.disabled = false;
  }
}

async function init() {
  await loadConfig();
  if (!API.base) {
    document.getElementById('notConfigured').hidden = false;
    document.getElementById('openOptions').onclick = () => chrome.runtime.openOptionsPage();
    return;
  }
  if (!(await isSessionValid())) {
    document.getElementById('notAuthenticated').hidden = false;
    document.getElementById('loginForm').onsubmit = async (e) => {
      e.preventDefault();
      const email = document.getElementById('loginEmail').value;
      const password = document.getElementById('loginPassword').value;
      try {
        await login(email, password);
        document.getElementById('notAuthenticated').hidden = true;
        showMain();
      } catch (err) {
        alert(err.message);
      }
    };
    return;
  }
  showMain();
}

async function showMain() {
  document.getElementById('main').hidden = false;
  let tabs = await loadTabs();
  renderTabs(tabs);
  document.getElementById('refreshBtn').onclick = async () => {
    tabs = await loadTabs();
    renderTabs(tabs);
  };
  document.getElementById('saveBtn').onclick = () => save(tabs);
}

document.getElementById('optionsBtn').onclick = () => chrome.runtime.openOptionsPage();

init();
