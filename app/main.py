import os
import secrets

import deepagents
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from telegram import Bot

from .db import (
    grant_access, init_db, is_allowed, is_public_mode,
    list_users, revoke_access, set_public_mode,
)
from .deep_agent_runtime import run_chat

_SEED_IDS: list[int] = [
    int(cid.strip())
    for cid in os.environ.get("TG_ALLOWED_CHAT_IDS", "").split(",")
    if cid.strip()
]

init_db(seed_ids=_SEED_IDS)

app = FastAPI(
    title="Project Nexus",
    description="FastAPI backend with deepagents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    medium: str = "web"


@app.post("/chat")
async def chat(request: ChatRequest):
    return await run_chat(
        message=request.message,
        thread_id=request.thread_id,
        medium=request.medium,
    )


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "deepagents": deepagents.__version__}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Project Nexus API",
        "docs": "/docs",
        "deepagents_version": deepagents.__version__,
    }


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

_basic = HTTPBasic()


def _require_admin(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    valid_user = secrets.compare_digest(
        credentials.username, os.environ["ADMIN_USERNAME"]
    )
    valid_pass = secrets.compare_digest(
        credentials.password, os.environ["ADMIN_PASSWORD"]
    )
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


# ---------------------------------------------------------------------------
# Access control API
# ---------------------------------------------------------------------------

class UserIn(BaseModel):
    chat_id: int
    label: str = ""


class ModeIn(BaseModel):
    public: bool


@app.get("/admin/mode", dependencies=[Depends(_require_admin)])
async def admin_get_mode():
    return {"public": is_public_mode()}


@app.post("/admin/mode", dependencies=[Depends(_require_admin)])
async def admin_set_mode(body: ModeIn):
    set_public_mode(body.public)
    return {"public": body.public}


@app.get("/admin/users", dependencies=[Depends(_require_admin)])
async def admin_list_users():
    return list_users()


@app.post("/admin/users", status_code=201, dependencies=[Depends(_require_admin)])
async def admin_grant(body: UserIn):
    grant_access(body.chat_id, body.label)
    return {"chat_id": body.chat_id, "label": body.label}


@app.delete("/admin/users/{chat_id}", status_code=204, dependencies=[Depends(_require_admin)])
async def admin_revoke(chat_id: int):
    if not is_allowed(chat_id):
        raise HTTPException(status_code=404, detail="User not found")
    revoke_access(chat_id)


# ---------------------------------------------------------------------------
# Prowl notifications
# ---------------------------------------------------------------------------

class JobMatch(BaseModel):
    title: str
    company: str
    score: int
    verdict: str
    url: str


class ProwlNotifyRequest(BaseModel):
    event: str
    chat_id: str
    count: int
    jobs: list[JobMatch]
    link: str | None = None


@app.post("/notify/prowl")
async def prowl_notify(body: ProwlNotifyRequest, x_api_key: str = Header(...)):
    expected = os.environ.get("PROWL_NOTIFY_SECRET")
    if not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")

    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="TG_BOT_TOKEN not configured")

    lines = [
        f"<b>Prowl found {body.count} new job recommendation{'s' if body.count != 1 else ''} for you</b>",
        "",
    ]
    for i, job in enumerate(body.jobs, 1):
        verdict_tag = "Strong match" if job.verdict == "apply" else "Worth a look"
        lines.append(f"{i}. <b>{job.title}</b> at <b>{job.company}</b>")
        lines.append(f"   Match score: {job.score}/100 — {verdict_tag}")
        lines.append(f"   <a href=\"{job.url}\">View job</a>")
        lines.append("")
    if body.link:
        lines.append(f"<a href=\"{body.link}\">See all recommendations on Prowl</a>")

    bot = Bot(token=token)
    await bot.send_message(chat_id=int(body.chat_id), text="\n".join(lines), parse_mode="HTML")

    return {"status": "sent"}


# ---------------------------------------------------------------------------
# Admin UI
# ---------------------------------------------------------------------------

_ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nexus — Access Control</title>
  <style>
    :root { font-family: system-ui, Segoe UI, sans-serif; background: #0f1419; color: #e7e9ea; }
    body { max-width: 48rem; margin: 0 auto; padding: 2rem 1.5rem; box-sizing: border-box; }
    h1 { font-size: 1.25rem; font-weight: 600; margin: 0 0 0.25rem; }
    .subtitle { font-size: 0.8rem; color: #8b98a5; margin: 0 0 2rem; }
    .card { background: #16181c; border: 1px solid #38444d; border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }
    .card h2 { font-size: 0.9rem; font-weight: 600; margin: 0 0 1rem; color: #8b98a5; text-transform: uppercase; letter-spacing: 0.05em; }
    .form-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    input[type="number"], input[type="text"] {
      background: #0f1419; border: 1px solid #38444d; border-radius: 6px;
      color: #e7e9ea; padding: 0.5rem 0.7rem; font-size: 0.9rem;
    }
    input[type="number"] { width: 10rem; }
    input[type="text"] { flex: 1; min-width: 8rem; }
    button {
      padding: 0.5rem 1.1rem; border-radius: 6px; border: none;
      font-weight: 600; font-size: 0.875rem; cursor: pointer;
    }
    .btn-primary { background: #1d9bf0; color: #fff; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-danger { background: transparent; color: #f4212e; border: 1px solid #f4212e; padding: 0.3rem 0.75rem; font-size: 0.8rem; }
    .btn-danger:hover { background: #f4212e22; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th { text-align: left; color: #8b98a5; font-weight: 500; padding: 0 0 0.6rem; border-bottom: 1px solid #38444d; }
    td { padding: 0.65rem 0; border-bottom: 1px solid #1e2732; vertical-align: middle; }
    td:last-child { text-align: right; }
    .chat-id { font-family: monospace; color: #1d9bf0; }
    .label { color: #8b98a5; font-style: italic; }
    .granted { font-size: 0.75rem; color: #8b98a5; }
    .empty { color: #8b98a5; font-size: 0.875rem; padding: 1rem 0; }
    .toast { position: fixed; bottom: 1.5rem; right: 1.5rem; background: #16181c; border: 1px solid #38444d;
             border-radius: 8px; padding: 0.7rem 1.1rem; font-size: 0.875rem; opacity: 0;
             transition: opacity 0.2s; pointer-events: none; }
    .toast.show { opacity: 1; }
    .toast.error { border-color: #f4212e; color: #f4212e; }
    .mode-card { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
    .mode-info h3 { margin: 0 0 0.2rem; font-size: 1rem; }
    .mode-info p { margin: 0; font-size: 0.8rem; color: #8b98a5; }
    .toggle-wrap { display: flex; align-items: center; gap: 0.65rem; flex-shrink: 0; }
    .toggle-label { font-size: 0.85rem; font-weight: 600; min-width: 4rem; text-align: right; }
    .toggle-label.public { color: #00ba7c; }
    .toggle-label.private { color: #8b98a5; }
    .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; inset: 0; background: #38444d; border-radius: 24px; cursor: pointer; transition: 0.2s; }
    .slider:before { content: ""; position: absolute; width: 18px; height: 18px; left: 3px; bottom: 3px;
                     background: #fff; border-radius: 50%; transition: 0.2s; }
    input:checked + .slider { background: #00ba7c; }
    input:checked + .slider:before { transform: translateX(20px); }
  </style>
</head>
<body>
  <h1>Nexus — Access Control</h1>
  <p class="subtitle">Manage who can talk to your Telegram bot.</p>

  <div class="card">
    <h2>Access mode</h2>
    <div class="mode-card">
      <div class="mode-info">
        <h3 id="modeTitle">Loading…</h3>
        <p id="modeDesc"></p>
      </div>
      <div class="toggle-wrap">
        <span class="toggle-label private" id="modeLabel">Private</span>
        <label class="switch">
          <input type="checkbox" id="modeToggle" onchange="toggleMode()" />
          <span class="slider"></span>
        </label>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Grant access</h2>
    <div class="form-row">
      <input id="chatId" type="number" placeholder="Chat ID" />
      <input id="label" type="text" placeholder="Label (optional)" />
      <button class="btn-primary" id="grantBtn" onclick="grantAccess()">Grant</button>
    </div>
  </div>

  <div class="card">
    <h2>Allowed users</h2>
    <div id="tableWrap"><p class="empty">Loading…</p></div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    async function loadUsers() {
      const res = await fetch('/admin/users');
      const users = await res.json();
      const wrap = document.getElementById('tableWrap');
      if (!users.length) {
        wrap.innerHTML = '<p class="empty">No users allowed yet.</p>';
        return;
      }
      wrap.innerHTML = `
        <table>
          <thead><tr><th>Chat ID</th><th>Label</th><th>Granted</th><th></th></tr></thead>
          <tbody>
            ${users.map(u => `
              <tr>
                <td><span class="chat-id">${u.chat_id}</span></td>
                <td><span class="label">${u.label || '—'}</span></td>
                <td><span class="granted">${u.granted_at}</span></td>
                <td><button class="btn-danger" onclick="revokeAccess(${u.chat_id})">Revoke</button></td>
              </tr>`).join('')}
          </tbody>
        </table>`;
    }

    async function grantAccess() {
      const chatId = parseInt(document.getElementById('chatId').value);
      const label = document.getElementById('label').value.trim();
      if (!chatId) { showToast('Enter a valid chat ID', true); return; }
      const btn = document.getElementById('grantBtn');
      btn.disabled = true;
      try {
        const res = await fetch('/admin/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: chatId, label }),
        });
        if (!res.ok) throw new Error(await res.text());
        document.getElementById('chatId').value = '';
        document.getElementById('label').value = '';
        showToast('Access granted');
        loadUsers();
      } catch (e) {
        showToast('Failed: ' + e.message, true);
      } finally {
        btn.disabled = false;
      }
    }

    async function revokeAccess(chatId) {
      if (!confirm(`Revoke access for ${chatId}?`)) return;
      const res = await fetch(`/admin/users/${chatId}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        showToast('Access revoked');
        loadUsers();
      } else {
        showToast('Failed to revoke', true);
      }
    }

    function showToast(msg, error = false) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.className = 'toast show' + (error ? ' error' : '');
      setTimeout(() => t.className = 'toast', 2500);
    }

    async function loadMode() {
      const res = await fetch('/admin/mode');
      const { public: isPublic } = await res.json();
      applyMode(isPublic);
    }

    function applyMode(isPublic) {
      document.getElementById('modeToggle').checked = isPublic;
      document.getElementById('modeLabel').textContent = isPublic ? 'Public' : 'Private';
      document.getElementById('modeLabel').className = 'toggle-label ' + (isPublic ? 'public' : 'private');
      document.getElementById('modeTitle').textContent = isPublic ? 'Public — anyone can chat' : 'Private — whitelist only';
      document.getElementById('modeDesc').textContent = isPublic
        ? 'All Telegram users can send messages to Nexus. The whitelist is ignored.'
        : 'Only users in the whitelist below can send messages to Nexus.';
    }

    async function toggleMode() {
      const isPublic = document.getElementById('modeToggle').checked;
      const res = await fetch('/admin/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ public: isPublic }),
      });
      if (res.ok) {
        applyMode(isPublic);
        showToast(isPublic ? 'Switched to public mode' : 'Switched to private mode');
      } else {
        showToast('Failed to update mode', true);
        document.getElementById('modeToggle').checked = !isPublic;
      }
    }

    loadMode();
    loadUsers();
  </script>
</body>
</html>"""


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
async def admin_ui():
    return HTMLResponse(content=_ADMIN_HTML)
