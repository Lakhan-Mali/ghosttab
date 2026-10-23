# GhostTab AI Browser Extension

A Chrome Manifest V3 extension that lets you push selected browser tabs into your GhostTab AI workspace.

## Install

1. Open `chrome://extensions` in Chrome or any Chromium browser.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. Click the GhostTab AI icon in your toolbar.
5. Click the ⚙ icon to set your GhostTab AI URL (default: `http://localhost:8000`).
6. Open the popup, sign in with your GhostTab AI account, select the tabs you want to save, give the project a title, and click **Save to GhostTab AI**.

## Permissions

- `tabs` — needed to read the title and URL of the tabs in the current window when you open the popup. Tabs are only read **after the popup is opened**, never in the background.
- `activeTab` — alternative access path to the currently focused tab.
- `storage` — store the GhostTab AI URL and (optional) shared extension token locally on the browser.
- `host_permissions` — limited to `http://localhost/*` and `http://127.0.0.1/*` for development. Add your production host here when deploying.

The extension **never reads browsing history**. It only reads the tabs in the current window at the moment you open the popup, and only sends the ones you explicitly leave checked.

## Authentication

This first iteration authenticates with the regular Django session cookie. After you sign in through the popup, the session cookie is reused for subsequent imports.

For production deployments with many users, swap the session-cookie auth for a per-user API token model (e.g. `rest_framework.authtoken`) and store the token via `chrome.storage.local`.

## Manual URL import fallback

If the extension is not installed, users can paste URLs directly into a project via the **Bulk import** button in the project workspace.
