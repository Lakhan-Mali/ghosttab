/* GhostTab AI extension service worker.
 * Currently a no-op placeholder — Manifest V3 requires a background script
 * entry even when there is no background work to do. Future home for any
 * offscreen import / sync tasks.
 */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
