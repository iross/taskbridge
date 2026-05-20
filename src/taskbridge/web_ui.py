"""Web UI server for bartib time tracking."""

import json
import os
import re
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .bartib_integration import BartibIntegration
from .database import db
from .todoist_api import TodoistAPI

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TaskBridge Time</title>
  <style>
    :root {
      --bg: #111;
      --surface: #1e1e1e;
      --active-bg: #1a2e1a;
      --active-border: #4a9a4a;
      --text: #e0e0e0;
      --muted: #777;
      --accent: #4caf50;
      --danger: #e57373;
      --border: #2e2e2e;
      --input-bg: #252525;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg: #f4f4f4;
        --surface: #fff;
        --active-bg: #f0fff0;
        --active-border: #4caf50;
        --text: #1a1a1a;
        --muted: #666;
        --border: #ddd;
        --input-bg: #fafafa;
      }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
      background: var(--bg);
      color: var(--text);
      padding: 24px 16px;
      min-height: 100vh;
    }
    .container { max-width: 820px; margin: 0 auto; }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    h1 { font-size: 1rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--accent);
      transition: opacity 0.3s;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 14px;
    }
    .card.active {
      background: var(--active-bg);
      border-color: var(--active-border);
    }
    .card-label {
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
      margin-bottom: 12px;
    }
    .current-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .current-project { font-size: 0.95rem; font-weight: 600; color: var(--accent); }
    .current-desc { color: var(--text); margin: 3px 0; font-size: 0.9rem; }
    .current-meta { font-size: 0.8rem; color: var(--muted); }
    .idle { color: var(--muted); font-style: italic; font-size: 0.9rem; }
    .btn {
      padding: 7px 15px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-family: inherit;
      font-size: 0.82rem;
      font-weight: 600;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .btn-stop { background: var(--danger); color: #fff; }
    .btn-start { background: var(--accent); color: #111; }
    .btn:hover { opacity: 0.82; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .form-full { margin-bottom: 12px; }
    label { display: block; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 4px; }
    select, input[type="text"] {
      width: 100%;
      background: var(--input-bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 7px 10px;
      font-family: inherit;
      font-size: 0.88rem;
    }
    select:focus, input:focus { outline: 1px solid var(--accent); border-color: var(--accent); }
    .form-actions { display: flex; justify-content: space-between; align-items: center; }
    .err { color: var(--danger); font-size: 0.82rem; }
    .day-group { margin-bottom: 18px; }
    .day-header {
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 6px;
    }
    .activity {
      display: grid;
      grid-template-columns: 110px 60px 1fr;
      gap: 10px;
      padding: 5px 0;
      font-size: 0.83rem;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      align-items: start;
    }
    .activity:last-child { border-bottom: none; }
    .act-time { color: var(--muted); font-size: 0.78rem; line-height: 1.4; }
    .act-dur { color: var(--muted); font-size: 0.78rem; }
    .act-project { color: var(--accent); font-size: 0.78rem; margin-bottom: 1px; }
    .act-desc { color: var(--text); }
    .activity.running .act-time { color: var(--accent); }
    .activity.running .act-dur { color: var(--accent); }
  </style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>TaskBridge Time</h1>
    <div class="dot" id="dot"></div>
  </div>

  <div id="current-card" class="card">
    <div class="card-label">Currently Tracking</div>
    <div id="current-content"><span class="idle">Not tracking</span></div>
  </div>

  <div class="card">
    <div class="card-label">Start New</div>
    <div class="form-grid">
      <div>
        <label for="project-select">Project</label>
        <select id="project-select"><option value="">Loading...</option></select>
      </div>
      <div>
        <label for="task-select">Todoist Task (optional)</label>
        <select id="task-select"><option value="">— none —</option></select>
      </div>
    </div>
    <div class="form-full">
      <label for="description">Description</label>
      <input id="description" type="text" list="desc-list" placeholder="What are you working on?">
      <datalist id="desc-list"></datalist>
    </div>
    <div class="form-actions">
      <span class="err" id="form-err"></span>
      <button class="btn btn-start" onclick="startTracking()">&#9654; Start</button>
    </div>
  </div>

  <div id="activities"></div>

</div>
<script>
  var startedAt = null;
  var elapsedTimer = null;

  function esc(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function fmtDur(secs) {
    if (!secs || secs < 0) return '0m';
    var h = Math.floor(secs / 3600);
    var m = Math.floor((secs % 3600) / 60);
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
  }

  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return d.toTimeString().slice(0, 5);
  }

  function fmtDay(iso) {
    var d = new Date(iso);
    var now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Today';
    var yest = new Date(now - 86400000);
    if (d.toDateString() === yest.toDateString()) return 'Yesterday';
    return d.toLocaleDateString('en-US', {weekday:'long', month:'short', day:'numeric'});
  }

  function updateElapsed() {
    if (!startedAt) return;
    var el = document.getElementById('elapsed');
    if (el) el.textContent = fmtDur(Math.floor((Date.now() - startedAt) / 1000));
  }

  function renderCurrent(cur) {
    var card = document.getElementById('current-card');
    var content = document.getElementById('current-content');
    clearInterval(elapsedTimer);
    elapsedTimer = null;
    if (!cur) {
      card.classList.remove('active');
      content.innerHTML = '<span class="idle">Not tracking</span>';
      startedAt = null;
      return;
    }
    card.classList.add('active');
    startedAt = new Date(cur.started_at).getTime();
    elapsedTimer = setInterval(updateElapsed, 1000);
    var elapsed = Math.floor((Date.now() - startedAt) / 1000);
    content.innerHTML =
      '<div class="current-row">' +
        '<div>' +
          '<div class="current-project">' + esc(cur.project) + '</div>' +
          '<div class="current-desc">' + esc(cur.description) + '</div>' +
          '<div class="current-meta">Started ' + fmtTime(cur.started_at) +
            ' &nbsp;&middot;&nbsp; <span id="elapsed">' + fmtDur(elapsed) + '</span></div>' +
        '</div>' +
        '<button class="btn btn-stop" onclick="stopTracking()">&#9632; Stop</button>' +
      '</div>';
  }

  function renderActivities(acts) {
    var el = document.getElementById('activities');
    if (!acts.length) {
      el.innerHTML = '<p style="color:var(--muted);font-size:.83rem">No activities in the last 7 days.</p>';
      return;
    }
    var groups = {};
    var keys = [];
    for (var i = 0; i < acts.length; i++) {
      var a = acts[i];
      var key = new Date(a.started_at).toDateString();
      if (!groups[key]) { groups[key] = {label: fmtDay(a.started_at), items: [], total: 0}; keys.push(key); }
      groups[key].items.push(a);
      if (a.duration_seconds) groups[key].total += a.duration_seconds;
    }
    var html = '';
    for (var k = 0; k < keys.length; k++) {
      var g = groups[keys[k]];
      html += '<div class="day-group"><div class="day-header"><span>' + esc(g.label) + '</span>';
      if (g.total) html += '<span>' + fmtDur(g.total) + '</span>';
      html += '</div>';
      for (var j = 0; j < g.items.length; j++) {
        var a = g.items[j];
        var endT = a.stopped_at ? fmtTime(a.stopped_at) : '···';
        var durS = a.duration_seconds ? fmtDur(a.duration_seconds) : '···';
        html += '<div class="activity' + (a.active ? ' running' : '') + '">' +
          '<span class="act-time">' + fmtTime(a.started_at) + '–' + endT + '</span>' +
          '<span class="act-dur">' + durS + '</span>' +
          '<div><div class="act-project">' + esc(a.project) + '</div>' +
          '<div class="act-desc">' + esc(a.description) + '</div></div>' +
          '</div>';
      }
      html += '</div>';
    }
    el.innerHTML = html;
  }

  function refreshStatus() {
    var dot = document.getElementById('dot');
    dot.style.opacity = '0.3';
    fetch('/api/status').then(function(r){ return r.json(); }).then(function(data) {
      renderCurrent(data.current);
      renderActivities(data.activities);
      dot.style.opacity = '1';
    }).catch(function() { dot.style.opacity = '1'; });
  }

  function loadProjects() {
    fetch('/api/projects').then(function(r){ return r.json(); }).then(function(data) {
      var sel = document.getElementById('project-select');
      var html = '<option value="">— select project —</option>';
      if (data.todoist && data.todoist.length) {
        html += '<optgroup label="Todoist">';
        for (var i = 0; i < data.todoist.length; i++) {
          var p = data.todoist[i];
          html += '<option value="todoist:' + esc(p.id) + '">' + esc(p.name) + '</option>';
        }
        html += '</optgroup>';
      }
      if (data.recent && data.recent.length) {
        html += '<optgroup label="Recent">';
        for (var i = 0; i < data.recent.length; i++) {
          var p = data.recent[i];
          html += '<option value="bartib:' + esc(p) + '">' + esc(p) + '</option>';
        }
        html += '</optgroup>';
      }
      sel.innerHTML = html;
    });
  }

  function onProjectChange() {
    var val = document.getElementById('project-select').value;
    var taskSel = document.getElementById('task-select');
    taskSel.innerHTML = '<option value="">— none —</option>';
    document.getElementById('desc-list').innerHTML = '';
    if (!val.startsWith('todoist:')) return;
    var projectId = val.slice(8);
    fetch('/api/tasks?project_id=' + encodeURIComponent(projectId)).then(function(r){ return r.json(); }).then(function(data) {
      if (!Array.isArray(data)) {
        var opt = document.createElement('option');
        opt.textContent = 'Error: ' + (data.error || 'failed to load');
        opt.disabled = true;
        taskSel.appendChild(opt);
        return;
      }
      for (var i = 0; i < data.length; i++) {
        var opt = document.createElement('option');
        opt.value = data[i].id;
        opt.textContent = data[i].content;
        taskSel.appendChild(opt);
      }
      var dl = document.getElementById('desc-list');
      for (var i = 0; i < data.length; i++) {
        var opt = document.createElement('option');
        opt.value = data[i].content;
        dl.appendChild(opt);
      }
    }).catch(function(e) {
      var opt = document.createElement('option');
      opt.textContent = 'Error: ' + e.message;
      opt.disabled = true;
      taskSel.appendChild(opt);
    });
  }

  function onTaskChange() {
    var taskSel = document.getElementById('task-select');
    if (!taskSel.value) return;
    var text = taskSel.options[taskSel.selectedIndex].textContent;
    if (text !== '— none —') document.getElementById('description').value = text;
  }

  function startTracking() {
    var errEl = document.getElementById('form-err');
    errEl.textContent = '';
    var description = document.getElementById('description').value.trim();
    if (!description) { errEl.textContent = 'Description is required'; return; }
    var projectVal = document.getElementById('project-select').value;
    var taskId = document.getElementById('task-select').value;
    var body = {description: description};
    if (projectVal.startsWith('todoist:')) body.project_id = projectVal.slice(8);
    else if (projectVal.startsWith('bartib:')) body.project_raw = projectVal.slice(7);
    if (taskId) body.todoist_task_id = taskId;
    fetch('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) {
          document.getElementById('description').value = '';
          document.getElementById('task-select').value = '';
          refreshStatus();
        } else {
          errEl.textContent = data.error || 'Failed to start';
        }
      }).catch(function() { errEl.textContent = 'Network error'; });
  }

  function stopTracking() {
    fetch('/api/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
      .then(function(){ refreshStatus(); });
  }

  document.getElementById('project-select').addEventListener('change', onProjectChange);
  document.getElementById('task-select').addEventListener('change', onTaskChange);

  refreshStatus();
  loadProjects();
  setInterval(refreshStatus, 10000);
</script>
</body>
</html>"""


def _read_activities(days: int = 7) -> list[dict]:
    """Read activities from bartib file, newest first, for the last N days."""
    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    activities: list[dict] = []

    try:
        with open(bartib_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" | ", 2)
                if len(parts) != 3:
                    continue
                time_part, project, description = parts

                if " - " in time_part:
                    start_str, stop_str = time_part.split(" - ", 1)
                    started_at = datetime.strptime(start_str.strip(), "%Y-%m-%d %H:%M")
                    stopped_at = datetime.strptime(stop_str.strip(), "%Y-%m-%d %H:%M")
                    duration = int((stopped_at - started_at).total_seconds())
                    active = False
                else:
                    started_at = datetime.strptime(time_part.strip(), "%Y-%m-%d %H:%M")
                    stopped_at = None
                    duration = None
                    active = True

                if started_at < cutoff:
                    continue

                activities.append(
                    {
                        "project": project,
                        "description": description,
                        "started_at": started_at.isoformat(),
                        "stopped_at": stopped_at.isoformat() if stopped_at else None,
                        "duration_seconds": duration,
                        "active": active,
                    }
                )
    except OSError:
        pass

    activities.reverse()
    return activities


def _get_todoist_projects() -> list[dict]:
    try:
        api = TodoistAPI()
        projects = api.get_projects()
        return [{"id": p.id, "name": p.name} for p in projects if not p.is_inbox_project]
    except Exception:
        return []


def _get_todoist_tasks(project_id: str) -> list[dict]:
    api = TodoistAPI()
    tasks = api.get_tasks(project_id=project_id)
    return [{"id": t.id, "content": t.content} for t in tasks if not t.is_completed]


def _get_recent_bartib_projects(limit: int = 10) -> list[str]:
    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        return []
    projects: list[str] = []
    seen: set[str] = set()
    try:
        with open(bartib_file) as f:
            lines = f.readlines()
        for line in reversed(lines):
            parts = line.strip().split(" | ", 2)
            if len(parts) == 3:
                project = parts[1]
                if project not in seen:
                    seen.add(project)
                    projects.append(project)
                    if len(projects) >= limit:
                        break
    except OSError:
        pass
    return projects


def _sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    return cleaned if cleaned else "general"


def _build_bartib_project(project: str, client: str = "") -> str:
    if client:
        parts = [_sanitize_name(client), _sanitize_name(project)]
    else:
        parts = [_sanitize_name(project)]
    return "::".join(parts)


def _stop_active(tracking) -> None:
    """Stop bartib and update the DB record for the active session."""
    bartib = BartibIntegration()
    bartib.stop_tracking()
    stopped_at = datetime.now()
    db.update_tracking_record(tracking, stopped_at=stopped_at)

    if tracking.todoist_task_id and not tracking.todoist_task_id.startswith("meeting:"):
        try:
            api = TodoistAPI()
            if tracking.started_at:
                secs = int((stopped_at - tracking.started_at).total_seconds())
                h, m = secs // 3600, (secs % 3600) // 60
                dur = f"{h}h {m}m" if h else f"{m}m"
            else:
                dur = "unknown"
            api.create_comment(tracking.todoist_task_id, f"⏱️ Tracked {dur}")
        except Exception:
            pass


class TimeWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send_html()
        elif path == "/api/status":
            self._handle_status()
        elif path == "/api/projects":
            self._handle_projects()
        elif path == "/api/tasks":
            qs = parse_qs(parsed.query)
            project_id = qs.get("project_id", [""])[0]
            self._handle_tasks(project_id)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}") if length else {}

        if path == "/api/start":
            self._handle_start(body)
        elif path == "/api/stop":
            self._handle_stop()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_html(self):
        data = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload, status: int = 200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_status(self):
        activities = _read_activities(days=7)
        active = db.get_active_tracking()
        current = None
        if active and active.started_at:
            elapsed = int((datetime.now() - active.started_at).total_seconds())
            current = {
                "project": active.project_name,
                "description": active.task_name,
                "started_at": active.started_at.isoformat(),
                "elapsed_seconds": elapsed,
                "todoist_task_id": active.todoist_task_id,
            }
        self._send_json({"current": current, "activities": activities})

    def _handle_projects(self):
        self._send_json(
            {"todoist": _get_todoist_projects(), "recent": _get_recent_bartib_projects()}
        )

    def _handle_tasks(self, project_id: str):
        if not project_id:
            self._send_json([])
            return
        try:
            self._send_json(_get_todoist_tasks(project_id))
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_start(self, body: dict):
        try:
            description = body.get("description", "").strip()
            if not description:
                self._send_json({"success": False, "error": "Description required"}, 400)
                return

            project_id = body.get("project_id", "")
            project_raw = body.get("project_raw", "")
            todoist_task_id = body.get("todoist_task_id", "")

            active = db.get_active_tracking()
            if active:
                _stop_active(active)

            bartib = BartibIntegration()

            if project_id:
                try:
                    from .main import resolve_project_info

                    api = TodoistAPI()
                    project_name, client_name = resolve_project_info(project_id, api)
                    bartib_project = _build_bartib_project(project_name, client_name)
                except Exception:
                    bartib_project = project_raw or "taskbridge"
            else:
                bartib_project = project_raw or "taskbridge"

            bartib.start_tracking(description=description, project=bartib_project)
            db.create_tracking_record(
                todoist_task_id=todoist_task_id,
                project_name=bartib_project,
                task_name=description,
                started_at=datetime.now(),
            )
            self._send_json({"success": True, "project": bartib_project})

        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_stop(self):
        active = db.get_active_tracking()
        if not active:
            self._send_json({"success": False, "error": "No active tracking"})
            return
        try:
            _stop_active(active)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)


def run_server(host: str = "127.0.0.1", port: int = 7777, open_browser: bool = True) -> None:
    """Start the time tracking web UI server."""
    server = HTTPServer((host, port), TimeWebHandler)
    url = f"http://{host}:{port}"
    print(f"TaskBridge Time UI: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()
