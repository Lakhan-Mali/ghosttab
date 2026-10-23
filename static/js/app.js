/*
 * GhostTab AI — application JavaScript
 * Modular ES6, vanilla JS, accessible.
 */

/* ------------------------------------------------------------------ */
/* Toast API */
/* ------------------------------------------------------------------ */
const Toast = {
  _area: null,
  _ensure() {
    if (!this._area) {
      this._area = document.querySelector('.gt-toast-area');
      if (!this._area) {
        this._area = document.createElement('div');
        this._area.className = 'gt-toast-area';
        document.body.appendChild(this._area);
      }
    }
    return this._area;
  },
  show(message, type = 'info', timeout = 4500) {
    const area = this._ensure();
    const el = document.createElement('div');
    el.className = `gt-toast gt-toast-${type}`;
    el.innerHTML = `<span class="gt-toast-icon"><i data-lucide="${type === 'success' ? 'check-circle-2' : type === 'error' ? 'alert-circle' : 'info'}"></i></span><div class="gt-toast-body">${message}</div>`;
    area.appendChild(el);
    if (window.lucide) window.lucide.createIcons();
    setTimeout(() => {
      el.classList.add('is-leaving');
      setTimeout(() => el.remove(), 300);
    }, timeout);
  },
  success(m, t) { this.show(m, 'success', t); },
  error(m, t) { this.show(m, 'error', t); },
  info(m, t) { this.show(m, 'info', t); },
};

/* ------------------------------------------------------------------ */
/* Modal API */
/* ------------------------------------------------------------------ */
const Modal = {
  open(contentHTML, { onClose } = {}) {
    const backdrop = document.createElement('div');
    backdrop.className = 'gt-modal-backdrop';
    backdrop.innerHTML = `<div class="gt-modal" role="dialog" aria-modal="true">${contentHTML}</div>`;
    document.body.appendChild(backdrop);
    const close = () => {
      backdrop.style.animation = 'gt-fade-in 0.18s var(--gt-ease-out) reverse both';
      setTimeout(() => backdrop.remove(), 160);
      if (onClose) onClose();
    };
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
    const esc = (e) => { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); } };
    document.addEventListener('keydown', esc);
    backdrop._close = close;
    if (window.lucide) window.lucide.createIcons();
    return backdrop;
  },
  close(backdrop) { if (backdrop && backdrop._close) backdrop._close(); },
};

/* ------------------------------------------------------------------ */
/* CSRF helper */
/* ------------------------------------------------------------------ */
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.content;
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return input ? input.value : '';
}

async function apiPost(url, body = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify(body),
  });
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

/* ------------------------------------------------------------------ */
/* Skeleton loaders */
/* ------------------------------------------------------------------ */
function showSkeleton(target, lines = 3) {
  target.innerHTML = Array.from({ length: lines })
    .map(() => `<div class="gt-skeleton" style="height: 12px; margin-bottom: 8px;"></div>`)
    .join('');
}
function clearSkeleton(target) { target.innerHTML = ''; }

/* ------------------------------------------------------------------ */
/* Reveal-on-scroll */
/* ------------------------------------------------------------------ */
function initRevealOnScroll() {
  const els = document.querySelectorAll('[data-reveal]');
  if (!('IntersectionObserver' in window)) {
    els.forEach(el => el.classList.add('is-revealed'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-revealed');
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
  els.forEach(el => io.observe(el));
}

/* ------------------------------------------------------------------ */
/* Boot */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  initRevealOnScroll();
  // Expose for inline handlers
  window.GT = { Toast, Modal, apiPost, showSkeleton, clearSkeleton };
});

window.GhostTab = { Toast, Modal, apiPost };
