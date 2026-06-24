"""Web UI server for bartib time tracking."""

import contextlib
import json
import os
import re
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .bartib_integration import BartibIntegration
from .database import TodoistNoteMapping, db
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
      --meeting: #5c7cfa;
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
        --meeting: #3b5bdb;
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
    .btn-complete { background: var(--accent); color: #111; }
    .btn-start { background: var(--accent); color: #111; }
    .btn-note { background: transparent; color: var(--muted); border: 1px solid var(--border); }
    .btn-note:hover { color: var(--text); border-color: var(--text); opacity: 1; }
    .btn-meeting { background: transparent; color: var(--muted); border: 1px solid var(--border); }
    .btn-meeting.on { background: var(--meeting); color: #fff; border-color: var(--meeting); }
    .btn:hover { opacity: 0.82; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .form-full { margin-bottom: 12px; }
    label { display: block; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 4px; }
    select, input[type="text"], input[type="datetime-local"], input[type="time"] {
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
    .form-time-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .form-time-row input[type="time"] { width: auto; }
    .opt { font-weight: 400; opacity: 0.55; text-transform: none; letter-spacing: 0; }
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
    .activity-wrap { border-bottom: 1px solid rgba(255,255,255,0.04); }
    .activity-wrap:last-child { border-bottom: none; }
    .activity {
      display: grid;
      grid-template-columns: 110px 60px 1fr;
      gap: 10px;
      padding: 5px 0;
      font-size: 0.83rem;
      align-items: start;
      cursor: pointer;
      border-radius: 3px;
    }
    .activity:hover { background: rgba(128,128,128,0.06); }
    .activity.editing { background: rgba(128,128,128,0.06); }
    .act-time { color: var(--muted); font-size: 0.78rem; line-height: 1.4; }
    .act-dur { color: var(--muted); font-size: 0.78rem; }
    .act-project { color: var(--accent); font-size: 0.78rem; margin-bottom: 1px; }
    .act-desc { color: var(--text); }
    .activity.running .act-time { color: var(--accent); }
    .activity.running .act-dur { color: var(--accent); }
    .activity-edit {
      display: none;
      padding: 10px 12px 12px;
      border-top: 1px solid var(--border);
      background: var(--input-bg);
      border-radius: 0 0 4px 4px;
    }
    .edit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
    .edit-actions { display: flex; gap: 8px; align-items: center; }
    .btn-save { background: var(--accent); color: #111; }
    .btn-resume { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
    .btn-del { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
    .btn-cancel { background: transparent; color: var(--muted); border: 1px solid var(--border); }
    .edit-err { color: var(--danger); font-size: 0.78rem; margin-left: 4px; }
    .task-wrap { position: relative; }
    .task-input-row { display: flex; gap: 6px; }
    .task-input-row input { flex: 1; }
    .btn-icon {
      padding: 7px 13px;
      background: transparent;
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: 4px;
      cursor: pointer;
      font-family: inherit;
      font-size: 1.1rem;
      line-height: 1;
      flex-shrink: 0;
      transition: color 0.15s, border-color 0.15s;
    }
    .btn-icon:hover { color: var(--accent); border-color: var(--accent); }
    .btn-icon:disabled { opacity: 0.4; cursor: default; }
    .task-dd {
      display: none;
      position: absolute;
      top: 100%; left: 0; right: 0;
      background: var(--surface);
      border: 1px solid var(--active-border);
      border-top: none;
      border-radius: 0 0 4px 4px;
      max-height: 220px;
      overflow-y: auto;
      z-index: 50;
    }
    .task-opt {
      padding: 7px 10px;
      cursor: pointer;
      font-size: 0.83rem;
      border-bottom: 1px solid rgba(128,128,128,0.1);
    }
    .task-opt:last-child { border-bottom: none; }
    .task-opt:hover, .task-opt.hi { background: var(--active-bg); color: var(--accent); }
    .task-opt.is-new { color: var(--muted); font-style: italic; }
    .task-opt.is-new:hover, .task-opt.is-new.hi { background: var(--active-bg); color: var(--accent); }
    .meeting-wrap { position: relative; }
    .meeting-drop {
      display: none;
      position: absolute;
      right: 0;
      top: calc(100% + 4px);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      min-width: 260px;
      z-index: 100;
      box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    .meeting-drop.open { display: block; }
    .meeting-drop-section { padding: 4px 0; border-bottom: 1px solid var(--border); }
    .meeting-drop-section:last-child { border-bottom: none; }
    .meeting-drop-label {
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
      padding: 5px 12px 2px;
    }
    .meeting-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      cursor: pointer;
      font-size: 0.82rem;
    }
    .meeting-item:hover { background: var(--active-bg); }
    .meeting-item-name { font-weight: 600; color: var(--text); white-space: nowrap; }
    .meeting-item-desc { color: var(--muted); font-size: 0.78rem; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .meeting-item-del { color: var(--danger); font-size: 0.9rem; cursor: pointer; padding: 0 2px; opacity: 0.45; flex-shrink: 0; }
    .meeting-item-del:hover { opacity: 1; }
    .meeting-adhoc {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      cursor: pointer;
      font-size: 0.82rem;
      color: var(--muted);
    }
    .meeting-adhoc:hover { background: var(--active-bg); color: var(--text); }
    .meeting-adhoc.on { color: var(--meeting); }
    .meeting-define-toggle {
      padding: 7px 12px;
      cursor: pointer;
      font-size: 0.82rem;
      color: var(--muted);
    }
    .meeting-define-toggle:hover { color: var(--accent); }
    .meeting-define-form { display: none; padding: 8px 12px 10px; border-top: 1px solid var(--border); }
    .meeting-define-form.open { display: block; }
    .meeting-define-form input {
      width: 100%;
      background: var(--input-bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 5px 8px;
      font-family: inherit;
      font-size: 0.82rem;
      margin-bottom: 5px;
    }
    .meeting-define-form input:focus { outline: 1px solid var(--meeting); border-color: var(--meeting); }
    .meeting-define-form .df-label {
      display: block;
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 3px;
    }
    .meeting-define-actions { display: flex; gap: 6px; margin-top: 6px; }
    .btn-meeting-save { background: var(--meeting); color: #fff; padding: 5px 10px; font-size: 0.78rem; }
    .meeting-err { color: var(--danger); font-size: 0.78rem; margin-top: 4px; min-height: 1em; }
    .btn-cal { background: transparent; color: var(--muted); border: 1px solid var(--border); }
    .btn-cal:hover { color: var(--text); border-color: var(--text); }
    .cal-modal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.55);
      z-index: 200;
      overflow-y: auto;
      padding: 40px 16px;
    }
    .cal-modal.open { display: block; }
    .cal-modal-inner {
      max-width: 600px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }
    .cal-modal-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
    }
    .cal-modal-header span { font-weight: 600; font-size: 0.9rem; flex: 1; }
    .cal-modal-header input[type=date] {
      background: var(--input-bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 4px 8px;
      font-family: inherit;
      font-size: 0.82rem;
    }
    .cal-modal-close {
      background: none;
      border: none;
      color: var(--muted);
      font-size: 1.2rem;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }
    .cal-modal-close:hover { color: var(--text); }
    .cal-events-list { padding: 8px 0; }
    .cal-empty { color: var(--muted); font-size: 0.85rem; padding: 16px; text-align: center; }
    .cal-event-row {
      border-bottom: 1px solid var(--border);
      padding: 8px 16px;
    }
    .cal-event-row:last-child { border-bottom: none; }
    .cal-event-meta {
      display: flex;
      align-items: baseline;
      gap: 8px;
    }
    .cal-event-time { color: var(--muted); font-size: 0.78rem; white-space: nowrap; flex-shrink: 0; }
    .cal-event-title { font-size: 0.88rem; font-weight: 600; flex: 1; }
    .cal-event-dur { color: var(--muted); font-size: 0.75rem; white-space: nowrap; }
    .cal-event-conflict {
      font-size: 0.75rem;
      color: #e8a000;
      margin: 2px 0 4px;
    }
    .cal-event-form {
      display: none;
      margin-top: 8px;
      padding: 8px 10px;
      background: var(--input-bg);
      border-radius: 4px;
      border: 1px solid var(--border);
    }
    .cal-event-form.open { display: block; }
    .cal-event-form label {
      display: block;
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin: 6px 0 2px;
    }
    .cal-event-form label:first-child { margin-top: 0; }
    .cal-event-form input {
      width: 100%;
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 5px 8px;
      font-family: inherit;
      font-size: 0.82rem;
    }
    .cal-event-form input:focus { outline: 1px solid var(--accent); border-color: var(--accent); }
    .cal-form-actions { display: flex; gap: 6px; margin-top: 8px; align-items: center; }
    .cal-ongoing-row {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      font-size: 0.82rem;
      color: var(--text);
      cursor: pointer;
      user-select: none;
    }
    .cal-ongoing-row input[type=checkbox] { margin: 0; flex-shrink: 0; cursor: pointer; width: auto; }
    .cal-event-form .cal-ongoing-label {
      display: inline;
      text-transform: none;
      font-size: 0.82rem;
      color: var(--text);
      letter-spacing: 0;
      margin: 0;
      cursor: pointer;
    }
    .btn-cal-log { background: var(--accent); color: #fff; padding: 4px 10px; font-size: 0.78rem; }
    .btn-cal-open { font-size: 0.75rem; padding: 3px 8px; margin-left: auto; flex-shrink: 0; }
    .cal-event-logged { color: var(--accent); font-size: 0.75rem; margin-top: 3px; }
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
        <label>Todoist Task (optional)</label>
        <div class="task-wrap">
          <div class="task-input-row">
            <input id="task-search" type="text" autocomplete="off" placeholder="Search tasks…">
            <button id="btn-add-task" class="btn-icon" title="Add as new Todoist task">+</button>
          </div>
          <div id="task-dd" class="task-dd"></div>
        </div>
        <input type="hidden" id="task-id">
      </div>
    </div>
    <div class="form-full">
      <label for="description">Description</label>
      <input id="description" type="text" list="desc-list" placeholder="What are you working on?">
      <datalist id="desc-list"></datalist>
    </div>
    <div class="form-time-row">
      <div>
        <label for="time-from">From <span class="opt">optional</span></label>
        <input id="time-from" type="time">
      </div>
      <div>
        <label for="time-to">To <span class="opt">optional — completes entry</span></label>
        <input id="time-to" type="time">
      </div>
    </div>
    <div class="form-actions">
      <span class="err" id="form-err"></span>
      <div style="display:flex;gap:8px;align-items:center">
        <div class="meeting-wrap">
          <button id="btn-meeting" class="btn btn-meeting" onclick="toggleMeetingPanel()">&#128197; Meeting</button>
          <div id="meeting-drop" class="meeting-drop">
            <div class="meeting-drop-section">
              <div class="meeting-drop-label">Saved Meetings</div>
              <div id="meeting-list"></div>
            </div>
            <div class="meeting-drop-section">
              <div class="meeting-adhoc" id="meeting-adhoc-item" onclick="toggleAdhoc()">&#128203; Ad-hoc (use form above)</div>
            </div>
            <div class="meeting-drop-section">
              <div class="meeting-define-toggle" onclick="toggleDefineForm()">&#43; Define New Meeting</div>
              <div id="meeting-define-form" class="meeting-define-form">
                <span class="df-label">Alias</span>
                <input id="meeting-alias" type="text" placeholder="e.g. standup">
                <span class="df-label">Description</span>
                <input id="meeting-desc-input" type="text" placeholder="Daily Standup">
                <span class="df-label">Project (optional)</span>
                <input id="meeting-project-input" type="text" placeholder="meetings">
                <span class="df-label">Client (optional)</span>
                <input id="meeting-client-input" type="text" placeholder="">
                <span class="df-label">Tags (comma-separated)</span>
                <input id="meeting-tags-input" type="text" placeholder="team, recurring">
                <div class="meeting-define-actions">
                  <button class="btn btn-meeting-save" onclick="defineMeeting()">Save</button>
                  <button class="btn btn-cancel" onclick="toggleDefineForm()">Cancel</button>
                </div>
                <div class="meeting-err" id="meeting-err"></div>
              </div>
            </div>
          </div>
        </div>
        <button class="btn btn-cal" onclick="openCalModal()">&#128197; Cal</button>
        <button class="btn btn-start" onclick="startTracking()">&#9654; Start</button>
      </div>
    </div>
  </div>

  <div id="activities"></div>

  <div id="cal-modal" class="cal-modal">
    <div class="cal-modal-inner">
      <div class="cal-modal-header">
        <span>&#128197; Import from Calendar</span>
        <input type="date" id="cal-date">
        <button class="btn btn-cal" onclick="loadCalendarEvents()" style="font-size:0.78rem;padding:4px 10px">Load</button>
        <button class="cal-modal-close" onclick="closeCalModal()">&#215;</button>
      </div>
      <div id="cal-events-list" class="cal-events-list">
        <div class="cal-empty">Select a date and click Load.</div>
      </div>
    </div>
  </div>

</div>
<script>
  var startedAt = null;
  var elapsedTimer = null;
  var isMeeting = false;
  var meetingPanelOpen = false;

  function toggleMeetingPanel() {
    meetingPanelOpen = !meetingPanelOpen;
    var drop = document.getElementById('meeting-drop');
    if (meetingPanelOpen) {
      drop.classList.add('open');
      loadMeetings();
    } else {
      drop.classList.remove('open');
    }
  }

  function closeMeetingPanel() {
    meetingPanelOpen = false;
    document.getElementById('meeting-drop').classList.remove('open');
  }

  function toggleAdhoc() {
    isMeeting = !isMeeting;
    document.getElementById('btn-meeting').classList.toggle('on', isMeeting);
    document.getElementById('meeting-adhoc-item').classList.toggle('on', isMeeting);
    closeMeetingPanel();
  }

  function loadMeetings() {
    fetch('/api/meetings').then(function(r){ return r.json(); }).then(function(data) {
      var el = document.getElementById('meeting-list');
      var meetings = data.meetings || [];
      if (!meetings.length) {
        el.innerHTML = '<div style="color:var(--muted);font-size:0.8rem;padding:5px 12px">No saved meetings</div>';
        return;
      }
      var html = '';
      for (var i = 0; i < meetings.length; i++) {
        var m = meetings[i];
        html += '<div class="meeting-item">' +
          '<span class="meeting-item-name" data-alias="' + esc(m.alias) + '" onclick="startSavedMeeting(this.dataset.alias)">' + esc(m.alias) + '</span>' +
          '<span class="meeting-item-desc" data-alias="' + esc(m.alias) + '" onclick="startSavedMeeting(this.dataset.alias)">' + esc(m.description) + '</span>' +
          '<span class="meeting-item-del" data-alias="' + esc(m.alias) + '" onclick="undefineMeeting(this.dataset.alias)">&#215;</span>' +
          '</div>';
      }
      el.innerHTML = html;
    }).catch(function() {
      document.getElementById('meeting-list').innerHTML = '<div style="color:var(--muted);font-size:0.8rem;padding:5px 12px">Failed to load</div>';
    });
  }

  function startSavedMeeting(alias) {
    closeMeetingPanel();
    fetch('/api/meeting/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({alias: alias})
    }).then(function(r){ return r.json(); }).then(function(data) {
      if (data.success) {
        refreshStatus();
      } else {
        document.getElementById('form-err').textContent = data.error || 'Failed to start meeting';
      }
    }).catch(function() { document.getElementById('form-err').textContent = 'Network error'; });
  }

  function undefineMeeting(alias) {
    if (!confirm('Remove saved meeting "' + alias + '"?')) return;
    fetch('/api/meeting/undefine', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({alias: alias})
    }).then(function(r){ return r.json(); }).then(function(data) {
      if (data.success) loadMeetings();
    });
  }

  function toggleDefineForm() {
    var form = document.getElementById('meeting-define-form');
    form.classList.toggle('open');
    document.getElementById('meeting-err').textContent = '';
  }

  function defineMeeting() {
    var alias = document.getElementById('meeting-alias').value.trim();
    var desc = document.getElementById('meeting-desc-input').value.trim();
    var errEl = document.getElementById('meeting-err');
    if (!alias || !desc) { errEl.textContent = 'Alias and description are required'; return; }
    fetch('/api/meeting/define', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        alias: alias,
        description: desc,
        project: document.getElementById('meeting-project-input').value.trim(),
        client: document.getElementById('meeting-client-input').value.trim(),
        tags: document.getElementById('meeting-tags-input').value.trim()
      })
    }).then(function(r){ return r.json(); }).then(function(data) {
      if (data.success) {
        document.getElementById('meeting-alias').value = '';
        document.getElementById('meeting-desc-input').value = '';
        document.getElementById('meeting-project-input').value = '';
        document.getElementById('meeting-client-input').value = '';
        document.getElementById('meeting-tags-input').value = '';
        document.getElementById('meeting-define-form').classList.remove('open');
        loadMeetings();
      } else {
        errEl.textContent = data.error || 'Failed to save';
      }
    }).catch(function() { errEl.textContent = 'Network error'; });
  }

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
    var noteBtn = '';
    if (cur.note_url) {
      noteBtn = '<button class="btn btn-note" data-note-url="' + esc(cur.note_url) + '" onclick="openNote(this)">&#128196; Note</button>';
    } else if (cur.has_todoist_task) {
      noteBtn = '<button class="btn btn-note" id="btn-note-create" onclick="createNote(this)">&#128196; Note</button>';
    }
    content.innerHTML =
      '<div class="current-row">' +
        '<div>' +
          '<div class="current-project">' + esc(cur.project) + '</div>' +
          '<div class="current-desc">' + esc(cur.description) + '</div>' +
          '<div class="current-meta">Started ' + fmtTime(cur.started_at) +
            ' &nbsp;&middot;&nbsp; <span id="elapsed">' + fmtDur(elapsed) + '</span></div>' +
        '</div>' +
        '<div style="display:flex;gap:8px;align-items:flex-start">' +
          noteBtn +
          (cur.has_todoist_task ? '<button class="btn btn-complete" onclick="completeTask()">&#10003; Complete</button>' : '') +
          '<button class="btn btn-stop" onclick="stopTracking()">&#9632; Stop</button>' +
        '</div>' +
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
        var stopInput = a.active ? '<div></div>' :
          '<div><label>End</label><input type="datetime-local" name="new_stopped_at" value="' + esc(a.stopped_at.slice(0,16)) + '"></div>';
        html += '<div class="activity-wrap">' +
          '<div class="activity' + (a.active ? ' running' : '') + '" onclick="toggleEdit(this)" data-key="' + esc(a.started_at) + '">' +
            '<span class="act-time">' + fmtTime(a.started_at) + '–' + endT + '</span>' +
            '<span class="act-dur">' + durS + '</span>' +
            '<div><div class="act-project">' + esc(a.project) + '</div>' +
            '<div class="act-desc">' + esc(a.description) + '</div></div>' +
          '</div>' +
          '<div class="activity-edit" data-key="' + esc(a.started_at) + '">' +
            '<div class="edit-grid">' +
              '<div><label>Start</label><input type="datetime-local" name="new_started_at" value="' + esc(a.started_at.slice(0,16)) + '"></div>' +
              stopInput +
              '<div><label>Project</label><input type="text" name="project" value="' + esc(a.project) + '"></div>' +
              '<div><label>Description</label><input type="text" name="description" value="' + esc(a.description) + '"></div>' +
            '</div>' +
            '<div class="edit-actions">' +
              '<button class="btn btn-save" onclick="saveEdit(this)">Save</button>' +
              '<button class="btn btn-resume" onclick="resumeActivity(this)">&#9654; Resume</button>' +
              '<button class="btn btn-del" onclick="deleteActivity(this)">Delete</button>' +
              '<button class="btn btn-cancel" onclick="cancelEdit(this)">Cancel</button>' +
              '<span class="edit-err"></span>' +
            '</div>' +
          '</div>' +
          '</div>';
      }
      html += '</div>';
    }
    el.innerHTML = html;
  }

  function refreshStatus() {
    var dot = document.getElementById('dot');
    dot.style.opacity = '0.3';
    var editOpen = !!document.querySelector('.activity-edit[style*="display: block"]');
    fetch('/api/status').then(function(r){ return r.json(); }).then(function(data) {
      renderCurrent(data.current);
      if (!editOpen) renderActivities(data.activities);
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

  var currentTasks = [];
  var allTasks = [];
  var allTasksLoaded = false;
  var allTasksLoading = false;
  var focusedIdx = -1;

  function onProjectChange() {
    var val = document.getElementById('project-select').value;
    currentTasks = []; focusedIdx = -1;
    document.getElementById('task-search').value = '';
    document.getElementById('task-id').value = '';
    closeTaskDd();
    document.getElementById('desc-list').innerHTML = '';
    if (!val.startsWith('todoist:')) return;
    var projectId = val.slice(8);
    fetch('/api/tasks?project_id=' + encodeURIComponent(projectId))
      .then(function(r){ return r.json(); })
      .then(function(data) {
        if (!Array.isArray(data)) {
          document.getElementById('form-err').textContent = 'Tasks: ' + (data.error || 'failed to load');
          return;
        }
        currentTasks = data;
        var dl = document.getElementById('desc-list');
        for (var i = 0; i < data.length; i++) {
          var opt = document.createElement('option');
          opt.value = data[i].content;
          dl.appendChild(opt);
        }
      });
  }

  function loadAllTasks() {
    if (allTasksLoaded || allTasksLoading) return;
    allTasksLoading = true;
    var dd = document.getElementById('task-dd');
    dd.innerHTML = '<div class="task-opt" style="color:var(--muted);font-style:italic">Loading tasks…</div>';
    dd.style.display = 'block';
    fetch('/api/tasks')
      .then(function(r){ return r.json(); })
      .then(function(data) {
        allTasksLoading = false;
        if (Array.isArray(data)) {
          allTasks = data;
          allTasksLoaded = true;
          renderTaskDd();
        } else {
          dd.innerHTML = '<div class="task-opt" style="color:var(--danger)">Failed: ' + esc(data.error || 'unknown') + '</div>';
          dd.style.display = 'block';
        }
      })
      .catch(function() {
        allTasksLoading = false;
        dd.innerHTML = '<div class="task-opt" style="color:var(--danger)">Network error</div>';
        dd.style.display = 'block';
      });
  }

  function renderTaskDd() {
    var raw = document.getElementById('task-search').value;
    var q = raw.toLowerCase();
    var dd = document.getElementById('task-dd');
    var projectVal = document.getElementById('project-select').value;
    var noProject = !projectVal;
    if (noProject && !allTasksLoaded) { loadAllTasks(); return; }
    var pool = noProject ? allTasks : currentTasks;
    var matches = q
      ? pool.filter(function(t) { return t.content.toLowerCase().indexOf(q) !== -1; })
      : pool.slice(0, 20);
    if (!matches.length && !raw) { dd.style.display = 'none'; return; }
    var html = '';
    for (var i = 0; i < matches.length; i++) {
      html += '<div class="task-opt" data-id="' + esc(matches[i].id) +
        '" data-txt="' + esc(matches[i].content) +
        '" data-project-id="' + esc(matches[i].project_id || '') + '">' +
        esc(matches[i].content) + '</div>';
    }
    if (raw) {
      html += '<div class="task-opt is-new" data-new="1">+ Add &ldquo;' + esc(raw) + '&rdquo; to Todoist</div>';
    }
    dd.innerHTML = html;
    dd.style.display = 'block';
    focusedIdx = -1;
    var opts = dd.querySelectorAll('.task-opt');
    for (var j = 0; j < opts.length; j++) {
      (function(opt) {
        opt.addEventListener('mousedown', function(e) {
          e.preventDefault();
          if (opt.getAttribute('data-new')) { addTask(); }
          else { selectTask(opt.getAttribute('data-id'), opt.getAttribute('data-txt'), opt.getAttribute('data-project-id')); }
        });
      })(opts[j]);
    }
  }

  function closeTaskDd() {
    document.getElementById('task-dd').style.display = 'none';
    focusedIdx = -1;
  }

  function selectTask(id, content, projectId) {
    document.getElementById('task-id').value = id;
    document.getElementById('task-search').value = content;
    document.getElementById('description').value = content;
    if (projectId) {
      var sel = document.getElementById('project-select');
      var opt = sel.querySelector('option[value="todoist:' + projectId + '"]');
      if (opt) sel.value = opt.value;
    }
    closeTaskDd();
  }

  function onTaskKeydown(e) {
    var dd = document.getElementById('task-dd');
    if (dd.style.display === 'none') { renderTaskDd(); return; }
    var opts = dd.querySelectorAll('.task-opt');
    if (!opts.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIdx = Math.min(focusedIdx + 1, opts.length - 1);
      updateFocus(opts);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIdx = Math.max(focusedIdx - 1, -1);
      updateFocus(opts);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (focusedIdx >= 0 && opts[focusedIdx]) {
        opts[focusedIdx].dispatchEvent(new MouseEvent('mousedown'));
      } else {
        var q = document.getElementById('task-search').value.trim();
        if (q) addTask();
      }
    } else if (e.key === 'Escape') {
      closeTaskDd();
    }
  }

  function updateFocus(opts) {
    for (var i = 0; i < opts.length; i++) {
      opts[i].classList.toggle('hi', i === focusedIdx);
    }
    if (focusedIdx >= 0) opts[focusedIdx].scrollIntoView({block: 'nearest'});
  }

  function addTask() {
    var q = document.getElementById('task-search').value.trim();
    var projectVal = document.getElementById('project-select').value;
    if (!q) { document.getElementById('task-search').focus(); return; }
    if (!projectVal.startsWith('todoist:')) {
      document.getElementById('form-err').textContent = 'Select a Todoist project first to add a task.';
      return;
    }
    var btn = document.getElementById('btn-add-task');
    btn.disabled = true; btn.textContent = '…';
    fetch('/api/task/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project_id: projectVal.slice(8), content: q})
    }).then(function(r){ return r.json(); }).then(function(data) {
      btn.disabled = false; btn.textContent = '+';
      if (data.id) {
        currentTasks.unshift({id: data.id, content: data.content});
        selectTask(data.id, data.content);
      } else {
        document.getElementById('form-err').textContent = 'Failed to add: ' + (data.error || 'unknown');
      }
    }).catch(function(e) {
      btn.disabled = false; btn.textContent = '+';
      document.getElementById('form-err').textContent = 'Error: ' + e.message;
    });
  }

  function startTracking() {
    var errEl = document.getElementById('form-err');
    errEl.textContent = '';
    var description = document.getElementById('description').value.trim();
    if (!description) { errEl.textContent = 'Description is required'; return; }
    var projectVal = document.getElementById('project-select').value;
    var taskId = document.getElementById('task-id').value;
    var body = {description: description};
    if (projectVal.startsWith('todoist:')) body.project_id = projectVal.slice(8);
    else if (projectVal.startsWith('bartib:')) body.project_raw = projectVal.slice(7);
    if (taskId) body.todoist_task_id = taskId;
    if (isMeeting) body.is_meeting = true;
    var timeFrom = document.getElementById('time-from').value;
    var timeTo = document.getElementById('time-to').value;
    if (timeFrom) body.time_from = timeFrom;
    if (timeTo) body.time_to = timeTo;
    fetch('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) {
          document.getElementById('description').value = '';
          document.getElementById('task-search').value = '';
          document.getElementById('task-id').value = '';
          document.getElementById('time-from').value = '';
          document.getElementById('time-to').value = '';
          isMeeting = false;
          document.getElementById('btn-meeting').classList.remove('on');
          document.getElementById('meeting-adhoc-item').classList.remove('on');
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

  function completeTask() {
    fetch('/api/complete', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) refreshStatus();
      });
  }

  function openNote(btn) {
    window.location.href = btn.getAttribute('data-note-url');
  }

  function createNote(btn) {
    btn.disabled = true;
    btn.textContent = '…';
    fetch('/api/note/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) {
          window.location.href = data.note_url;
          refreshStatus();
        } else {
          btn.disabled = false;
          btn.textContent = '📄 Note';
        }
      }).catch(function() {
        btn.disabled = false;
        btn.textContent = '📄 Note';
      });
  }

  function toggleEdit(row) {
    var editDiv = row.parentElement.querySelector('.activity-edit');
    var isOpen = editDiv.style.display === 'block';
    document.querySelectorAll('.activity-edit').forEach(function(d) { d.style.display = 'none'; });
    document.querySelectorAll('.activity.editing').forEach(function(r) { r.classList.remove('editing'); });
    if (!isOpen) {
      editDiv.style.display = 'block';
      row.classList.add('editing');
    }
  }

  function saveEdit(btn) {
    var editDiv = btn.closest('.activity-edit');
    var errEl = editDiv.querySelector('.edit-err');
    errEl.textContent = '';
    var stopInput = editDiv.querySelector('[name=new_stopped_at]');
    var body = {
      original_started_at: editDiv.getAttribute('data-key'),
      new_started_at: editDiv.querySelector('[name=new_started_at]').value,
      new_stopped_at: stopInput ? stopInput.value : '',
      project: editDiv.querySelector('[name=project]').value.trim(),
      description: editDiv.querySelector('[name=description]').value.trim()
    };
    fetch('/api/activity/edit', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) { refreshStatus(); }
        else { errEl.textContent = data.error || 'Save failed'; }
      }).catch(function() { errEl.textContent = 'Network error'; });
  }

  function deleteActivity(btn) {
    if (!confirm('Delete this entry?')) return;
    var editDiv = btn.closest('.activity-edit');
    fetch('/api/activity/delete', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({original_started_at: editDiv.getAttribute('data-key')})})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) refreshStatus();
      });
  }

  function cancelEdit(btn) {
    var editDiv = btn.closest('.activity-edit');
    editDiv.style.display = 'none';
    editDiv.closest('.activity-wrap').querySelector('.activity').classList.remove('editing');
  }

  function resumeActivity(btn) {
    var editDiv = btn.closest('.activity-edit');
    var errEl = editDiv.querySelector('.edit-err');
    errEl.textContent = '';
    var body = {
      original_started_at: editDiv.getAttribute('data-key'),
      project: editDiv.querySelector('[name=project]').value.trim(),
      description: editDiv.querySelector('[name=description]').value.trim()
    };
    fetch('/api/activity/resume', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
      .then(function(r){ return r.json(); }).then(function(data) {
        if (data.success) { refreshStatus(); cancelEdit(btn); }
        else { errEl.textContent = data.error || 'Failed'; }
      }).catch(function() { errEl.textContent = 'Network error'; });
  }

  var calEvents = [];
  var calRecentProjects = [];

  function openCalModal() {
    var modal = document.getElementById('cal-modal');
    modal.classList.add('open');
    var dateEl = document.getElementById('cal-date');
    if (!dateEl.value) {
      var now = new Date();
      dateEl.value = now.getFullYear() + '-' +
        String(now.getMonth()+1).padStart(2,'0') + '-' +
        String(now.getDate()).padStart(2,'0');
      loadCalendarEvents();
    }
  }

  function closeCalModal() {
    document.getElementById('cal-modal').classList.remove('open');
  }

  function loadCalendarEvents() {
    var date = document.getElementById('cal-date').value;
    if (!date) return;
    var listEl = document.getElementById('cal-events-list');
    listEl.innerHTML = '<div class="cal-empty">Loading…</div>';
    fetch('/api/calendar/events?date=' + encodeURIComponent(date))
      .then(function(r){ return r.json(); })
      .then(function(data) {
        if (data.error) {
          listEl.innerHTML = '<div class="cal-empty">' + esc(data.error) + '</div>';
          return;
        }
        calEvents = data.events || [];
        calRecentProjects = data.recent_projects || [];
        renderCalEvents();
      })
      .catch(function() {
        listEl.innerHTML = '<div class="cal-empty">Failed to load events.</div>';
      });
  }

  function renderCalEvents() {
    var listEl = document.getElementById('cal-events-list');
    if (!calEvents.length) {
      listEl.innerHTML = '<div class="cal-empty">No timed events on this day.</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < calEvents.length; i++) {
      var ev = calEvents[i];
      var conflictHtml = '';
      if (ev.conflicts && ev.conflicts.length) {
        for (var c = 0; c < ev.conflicts.length; c++) {
          var cf = ev.conflicts[c];
          conflictHtml += '<div class="cal-event-conflict">&#9888; Conflicts with: ' +
            esc(cf.task_name) + ' (' + esc(cf.start) + '&#8211;' + esc(cf.end) + ')</div>';
        }
      }
      var projectSuggestions = '';
      if (calRecentProjects.length) {
        projectSuggestions = '<datalist id="cal-proj-list-' + i + '">';
        for (var p = 0; p < calRecentProjects.length; p++) {
          projectSuggestions += '<option value="' + esc(calRecentProjects[p]) + '">';
        }
        projectSuggestions += '</datalist>';
      }
      html += '<div class="cal-event-row" id="cal-row-' + i + '">' +
        '<div class="cal-event-meta">' +
        '<span class="cal-event-time">' + esc(ev.start_fmt) + '&#8211;' + esc(ev.end_fmt) + '</span>' +
        '<span class="cal-event-title">' + esc(ev.title) + '</span>' +
        '<span class="cal-event-dur">' + esc(ev.duration_fmt) + '</span>' +
        '<button class="btn btn-cal-open" onclick="toggleCalForm(' + i + ')">Log</button>' +
        '</div>' +
        conflictHtml +
        '<div class="cal-event-form" id="cal-form-' + i + '">' +
        projectSuggestions +
        '<label>Description</label>' +
        '<input type="text" id="cal-desc-' + i + '" value="' + esc(ev.title) + '">' +
        '<label>Project</label>' +
        '<input type="text" id="cal-proj-' + i + '" placeholder="client::project"' +
          (calRecentProjects.length ? ' list="cal-proj-list-' + i + '"' : '') + '>' +
        '<div id="cal-end-wrap-' + i + '">' +
        '<label>End time</label>' +
        '<input type="time" id="cal-end-' + i + '" value="' + esc(ev.end_fmt) + '">' +
        '</div>' +
        '<div class="cal-ongoing-row">' +
        '<input type="checkbox" id="cal-ongoing-' + i + '" onchange="toggleCalOngoing(' + i + ')">' +
        '<label for="cal-ongoing-' + i + '" class="cal-ongoing-label">Start as current (ongoing) task</label>' +
        '</div>' +
        '<div class="cal-form-actions">' +
        '<button class="btn btn-cal-log" onclick="logCalEvent(' + i + ')">Log Entry</button>' +
        '<button class="btn btn-cancel" onclick="toggleCalForm(' + i + ')">Cancel</button>' +
        '<span class="cal-event-logged" id="cal-ok-' + i + '" style="display:none">&#10003; Logged</span>' +
        '</div>' +
        '<div class="meeting-err" id="cal-err-' + i + '"></div>' +
        '</div>' +
        '</div>';
    }
    listEl.innerHTML = html;
  }

  function toggleCalForm(idx) {
    var form = document.getElementById('cal-form-' + idx);
    form.classList.toggle('open');
  }

  function toggleCalOngoing(idx) {
    var ongoing = document.getElementById('cal-ongoing-' + idx).checked;
    var endWrap = document.getElementById('cal-end-wrap-' + idx);
    endWrap.style.opacity = ongoing ? '0.35' : '1';
    endWrap.querySelector('input').disabled = ongoing;
  }

  function logCalEvent(idx) {
    var ev = calEvents[idx];
    var desc = document.getElementById('cal-desc-' + idx).value.trim();
    var proj = document.getElementById('cal-proj-' + idx).value.trim();
    var ongoing = document.getElementById('cal-ongoing-' + idx).checked;
    var errEl = document.getElementById('cal-err-' + idx);
    errEl.textContent = '';
    if (!desc || !proj) {
      errEl.textContent = 'Description and project are required.';
      return;
    }
    var body = {start: ev.start_iso, description: desc, project: proj, ongoing: ongoing};
    if (!ongoing) {
      var endTime = document.getElementById('cal-end-' + idx).value;
      if (!endTime) { errEl.textContent = 'End time required.'; return; }
      // combine event date with (possibly edited) end time
      var startDate = ev.start_iso.substring(0, 10);
      body.end = startDate + 'T' + endTime + ':00';
    }
    fetch('/api/calendar/log', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(function(data) {
      if (data.success) {
        var okEl = document.getElementById('cal-ok-' + idx);
        okEl.textContent = data.ongoing ? '&#9654; Started' : '&#10003; Logged';
        okEl.style.display = 'inline';
        document.getElementById('cal-form-' + idx).classList.remove('open');
        if (data.ongoing) closeCalModal();
        refreshStatus();
      } else {
        errEl.textContent = data.error || 'Failed to log entry.';
      }
    }).catch(function() { errEl.textContent = 'Network error.'; });
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeCalModal();
  });

  document.getElementById('project-select').addEventListener('change', onProjectChange);
  document.getElementById('task-search').addEventListener('focus', renderTaskDd);
  document.getElementById('task-search').addEventListener('input', function() {
    document.getElementById('task-id').value = '';
    renderTaskDd();
  });
  document.getElementById('task-search').addEventListener('keydown', onTaskKeydown);
  document.getElementById('btn-add-task').addEventListener('click', addTask);
  document.addEventListener('mousedown', function(e) {
    var wrap = document.querySelector('.task-wrap');
    if (wrap && !wrap.contains(e.target)) closeTaskDd();
    var mwrap = document.querySelector('.meeting-wrap');
    if (meetingPanelOpen && mwrap && !mwrap.contains(e.target)) closeMeetingPanel();
  });

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

    activities.sort(key=lambda a: a["started_at"], reverse=True)
    return activities


def _get_todoist_projects() -> list[dict]:
    try:
        api = TodoistAPI()
        projects = api.get_projects()

        children_of: dict[str, list] = {}
        roots = []
        for p in projects:
            if p.is_inbox_project:
                continue
            if p.parent_id:
                children_of.setdefault(p.parent_id, []).append(p)
            else:
                roots.append(p)

        roots.sort(key=lambda p: p.order)
        for kids in children_of.values():
            kids.sort(key=lambda p: p.order)

        result: list[dict] = []

        def walk(p, ancestors: list[str]) -> None:
            path = " / ".join([*ancestors, p.name])
            result.append({"id": p.id, "name": path})
            for child in children_of.get(p.id, []):
                walk(child, [*ancestors, p.name])

        for root in roots:
            walk(root, [])

        return result
    except Exception:
        return []


def _get_todoist_tasks(project_id: str) -> list[dict]:
    api = TodoistAPI()
    tasks = api.get_tasks(project_id=project_id or None)
    return [
        {"id": t.id, "content": t.content, "project_id": t.project_id}
        for t in tasks
        if not t.is_completed
    ]


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


def _parse_bartib_for_day(target_date: datetime) -> list:
    """Return bartib records whose start falls on target_date."""
    from datetime import timedelta

    from .database import TaskTimeTracking

    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        return []
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    records: list[TaskTimeTracking] = []
    try:
        with open(bartib_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" | ", 2)
                if len(parts) != 3:
                    continue
                time_part, project_name, task_name = parts
                if " - " in time_part:
                    start_str, stop_str = time_part.split(" - ", 1)
                    started_at = datetime.strptime(start_str.strip(), "%Y-%m-%d %H:%M")
                    stopped_at = datetime.strptime(stop_str.strip(), "%Y-%m-%d %H:%M")
                else:
                    started_at = datetime.strptime(time_part.strip(), "%Y-%m-%d %H:%M")
                    stopped_at = None
                if day_start <= started_at < day_end:
                    records.append(
                        TaskTimeTracking(
                            todoist_task_id="",
                            project_name=project_name,
                            task_name=task_name,
                            started_at=started_at,
                            stopped_at=stopped_at,
                        )
                    )
    except OSError:
        pass
    return records


def _append_bartib_entry(project: str, description: str, start: datetime, end: datetime) -> None:
    """Append a completed entry directly to the bartib file."""
    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        raise RuntimeError(
            "BARTIB_FILE environment variable is not set. "
            "Set it to the path of your bartib activity log."
        )
    start_str = start.strftime("%Y-%m-%d %H:%M")
    end_str = end.strftime("%Y-%m-%d %H:%M")
    line = f"{start_str} - {end_str} | {project} | {description}\n"
    with open(bartib_file, "a") as f:
        f.write(line)


def _sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned if cleaned else "general"


def _build_bartib_project(project: str, client: str = "", tags: list[str] | None = None) -> str:
    parts = (
        [_sanitize_name(client), _sanitize_name(project)] if client else [_sanitize_name(project)]
    )
    if tags:
        parts.append(",".join(_sanitize_name(t) for t in tags))
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


def _bartib_key(iso: str) -> str:
    """Convert an ISO datetime string to bartib file format 'YYYY-MM-DD HH:MM'."""
    return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")


def _edit_bartib_line(
    original_started_at: str,
    new_started_at: str,
    new_stopped_at: str,
    project: str,
    description: str,
) -> bool:
    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        return False
    orig_key = _bartib_key(original_started_at)
    new_start_str = _bartib_key(new_started_at) if new_started_at else orig_key
    try:
        with open(bartib_file) as f:
            lines = f.readlines()
    except OSError:
        return False
    new_lines = []
    found = False
    for line in lines:
        stripped = line.strip()
        parts = stripped.split(" | ", 2) if stripped else []
        if len(parts) == 3:
            time_part = parts[0]
            line_start = time_part.split(" - ", 1)[0].strip()
            if line_start == orig_key:
                found = True
                if " - " in time_part:
                    orig_stop = time_part.split(" - ", 1)[1].strip()
                    stop_str = _bartib_key(new_stopped_at) if new_stopped_at else orig_stop
                    time_str = f"{new_start_str} - {stop_str}"
                else:
                    time_str = new_start_str
                new_lines.append(f"{time_str} | {project} | {description}\n")
                continue
        new_lines.append(line)
    if not found:
        return False
    with open(bartib_file, "w") as f:
        f.writelines(new_lines)
    return True


def _delete_bartib_line(original_started_at: str) -> bool:
    bartib_file = os.environ.get("BARTIB_FILE", "")
    if not bartib_file:
        return False
    orig_key = _bartib_key(original_started_at)
    try:
        with open(bartib_file) as f:
            lines = f.readlines()
    except OSError:
        return False
    new_lines = []
    found = False
    for line in lines:
        stripped = line.strip()
        parts = stripped.split(" | ", 2) if stripped else []
        if len(parts) == 3:
            time_part = parts[0]
            line_start = time_part.split(" - ", 1)[0].strip()
            if line_start == orig_key:
                found = True
                continue
        new_lines.append(line)
    if not found:
        return False
    with open(bartib_file, "w") as f:
        f.writelines(new_lines)
    return True


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
        elif path == "/api/meetings":
            self._handle_meetings_list()
        elif path == "/api/calendar/events":
            date_str = parse_qs(parsed.query).get("date", [""])[0]
            self._handle_calendar_events(date_str)
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
        elif path == "/api/task/create":
            self._handle_task_create(body)
        elif path == "/api/activity/edit":
            self._handle_activity_edit(body)
        elif path == "/api/activity/delete":
            self._handle_activity_delete(body)
        elif path == "/api/activity/resume":
            self._handle_activity_resume(body)
        elif path == "/api/note/create":
            self._handle_note_create()
        elif path == "/api/complete":
            self._handle_complete()
        elif path == "/api/meeting/start":
            self._handle_meeting_start(body)
        elif path == "/api/meeting/define":
            self._handle_meeting_define(body)
        elif path == "/api/meeting/undefine":
            self._handle_meeting_undefine(body)
        elif path == "/api/calendar/log":
            self._handle_calendar_log(body)
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
            task_id = active.todoist_task_id or ""
            has_todoist_task = bool(task_id and not task_id.startswith("meeting:"))
            note_url = None
            if has_todoist_task:
                mapping = db.get_todoist_note_by_task_id(task_id)
                if mapping:
                    note_url = mapping.obsidian_url
            current = {
                "project": active.project_name,
                "description": active.task_name,
                "started_at": active.started_at.isoformat(),
                "elapsed_seconds": elapsed,
                "todoist_task_id": task_id,
                "has_todoist_task": has_todoist_task,
                "note_url": note_url,
            }
        self._send_json({"current": current, "activities": activities})

    def _handle_projects(self):
        self._send_json(
            {"todoist": _get_todoist_projects(), "recent": _get_recent_bartib_projects()}
        )

    def _handle_tasks(self, project_id: str):
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
            is_meeting = bool(body.get("is_meeting", False))
            todoist_task_id = body.get("todoist_task_id", "")
            if is_meeting:
                todoist_task_id = f"meeting:{description}"

            active = db.get_active_tracking()
            if active:
                _stop_active(active)

            bartib = BartibIntegration()

            # If a specific task is linked, resolve project+labels from the task itself.
            # Otherwise fall back to the dropdown-selected project.
            task_labels: list[str] = []
            if todoist_task_id and not is_meeting:
                try:
                    from .main import resolve_project_info

                    api = TodoistAPI()
                    task_obj = api.get_task(todoist_task_id)
                    if task_obj:
                        project_name, client_name = resolve_project_info(task_obj.project_id, api)
                        task_labels = task_obj.labels or []
                    elif project_id:
                        project_name, client_name = resolve_project_info(project_id, api)
                    else:
                        raise ValueError("no project")
                    bartib_project = _build_bartib_project(project_name, client_name, task_labels)
                except Exception:
                    bartib_project = project_raw or "taskbridge"
            elif project_id:
                try:
                    from .main import resolve_project_info

                    api = TodoistAPI()
                    project_name, client_name = resolve_project_info(project_id, api)
                    bartib_project = _build_bartib_project(project_name, client_name)
                except Exception:
                    bartib_project = project_raw or ("meetings" if is_meeting else "taskbridge")
            else:
                bartib_project = project_raw or ("meetings" if is_meeting else "taskbridge")

            if is_meeting:
                bartib_project = f"{bartib_project}::meeting"

            time_from = body.get("time_from", "").strip()  # HH:MM or ""
            time_to = body.get("time_to", "").strip()  # HH:MM or ""

            today = datetime.now().strftime("%Y-%m-%d")
            if time_from and time_to:
                # Completed past entry — write directly, no live session
                from .main import append_bartib_entry

                start_dt = datetime.strptime(f"{today} {time_from}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{today} {time_to}", "%Y-%m-%d %H:%M")
                if end_dt <= start_dt:
                    self._send_json({"success": False, "error": "To must be after From"}, 400)
                    return
                append_bartib_entry(bartib_project, description, start_dt, end_dt)
            else:
                # Live session — optionally backdated
                bartib.start_tracking(
                    description=description,
                    project=bartib_project,
                    start_time=time_from or None,
                )
                started_at = (
                    datetime.strptime(f"{today} {time_from}", "%Y-%m-%d %H:%M")
                    if time_from
                    else datetime.now()
                )
                db.create_tracking_record(
                    todoist_task_id=todoist_task_id,
                    project_name=bartib_project,
                    task_name=description,
                    started_at=started_at,
                )
            self._send_json({"success": True, "project": bartib_project})

        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_task_create(self, body: dict):
        content = body.get("content", "").strip()
        project_id = body.get("project_id", "")
        if not content:
            self._send_json({"error": "Content required"}, 400)
            return
        try:
            api = TodoistAPI()
            task = api.create_task(content=content, project_id=project_id or None)
            self._send_json({"id": task.id, "content": task.content})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

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

    def _handle_activity_edit(self, body: dict):
        original = body.get("original_started_at", "").strip()
        new_start = body.get("new_started_at", "").strip()
        new_stop = body.get("new_stopped_at", "").strip()
        project = body.get("project", "").strip()
        description = body.get("description", "").strip()
        if not original:
            self._send_json({"success": False, "error": "original_started_at required"}, 400)
            return
        if not description or not project:
            self._send_json({"success": False, "error": "Project and description required"}, 400)
            return
        try:
            ok = _edit_bartib_line(original, new_start, new_stop, project, description)
            if ok:
                self._send_json({"success": True})
            else:
                self._send_json({"success": False, "error": "Entry not found"}, 404)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_activity_delete(self, body: dict):
        original = body.get("original_started_at", "").strip()
        if not original:
            self._send_json({"success": False, "error": "original_started_at required"}, 400)
            return
        try:
            ok = _delete_bartib_line(original)
            if ok:
                self._send_json({"success": True})
            else:
                self._send_json({"success": False, "error": "Entry not found"}, 404)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_activity_resume(self, body: dict):
        project = body.get("project", "").strip()
        description = body.get("description", "").strip()
        original = body.get("original_started_at", "").strip()
        if not project or not description:
            self._send_json({"success": False, "error": "Project and description required"}, 400)
            return
        try:
            active = db.get_active_tracking()
            if active:
                _stop_active(active)

            # Recover the Todoist task ID from the original DB record (if any)
            todoist_task_id = ""
            if original:
                with contextlib.suppress(Exception):
                    orig_dt = datetime.fromisoformat(original)
                    records = db.get_tracking_in_range(
                        orig_dt - timedelta(seconds=30),
                        orig_dt + timedelta(seconds=30),
                    )
                    for r in records:
                        if r.todoist_task_id and not r.todoist_task_id.startswith("meeting:"):
                            todoist_task_id = r.todoist_task_id
                            break

            bartib = BartibIntegration()
            bartib.start_tracking(description=description, project=project)
            db.create_tracking_record(
                todoist_task_id=todoist_task_id,
                project_name=project,
                task_name=description,
                started_at=datetime.now(),
            )
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_note_create(self):
        active = db.get_active_tracking()
        if (
            not active
            or not active.todoist_task_id
            or active.todoist_task_id.startswith("meeting:")
        ):
            self._send_json({"success": False, "error": "No active Todoist task"}, 400)
            return
        try:
            from .config import config as config_manager
            from .main import resolve_project_info

            # Return existing note if already mapped
            existing = db.get_todoist_note_by_task_id(active.todoist_task_id)
            if existing:
                self._send_json({"success": True, "note_url": existing.obsidian_url, "new": False})
                return

            api = TodoistAPI()
            task = api.get_task(active.todoist_task_id)
            if not task:
                self._send_json({"success": False, "error": "Task not found in Todoist"}, 404)
                return

            project_name, client_name = resolve_project_info(task.project_id, api)
            note_path = config_manager.create_task_note(
                project_name=project_name,
                task_title=task.content,
                client=client_name,
                status="backlog",
                tags=task.labels,
            )
            obsidian_url = config_manager.generate_obsidian_url(project_name, note_path.name)

            mapping = TodoistNoteMapping(
                todoist_task_id=active.todoist_task_id,
                todoist_project_id=task.project_id,
                note_path=str(note_path),
                obsidian_url=obsidian_url,
            )
            db.create_todoist_note_mapping(mapping)

            with contextlib.suppress(Exception):
                api.create_comment(
                    active.todoist_task_id,
                    f"📝 Obsidian note: [Open Note]({obsidian_url})",
                )

            self._send_json({"success": True, "note_url": obsidian_url, "new": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_complete(self):
        active = db.get_active_tracking()
        if not active:
            self._send_json({"success": False, "error": "No active tracking"}, 400)
            return
        task_id = active.todoist_task_id or ""
        if not task_id or task_id.startswith("meeting:"):
            self._send_json({"success": False, "error": "No active Todoist task"}, 400)
            return
        try:
            from .config import config as config_manager

            _stop_active(active)

            api = TodoistAPI()
            api.close_task(task_id)

            mapping = db.get_todoist_note_by_task_id(task_id)
            if mapping:
                note_path = Path(mapping.note_path)
                if note_path.exists():
                    content = note_path.read_text()
                    content = re.sub(r'status: "[^"]*"', 'status: "done"', content)
                    content = re.sub(r"status: '[^']*'", "status: 'done'", content)
                    content = re.sub(r"status: \S+", 'status: "done"', content)
                    note_path.write_text(content)

                    vault_path = config_manager.get_obsidian_vault_path()
                    if vault_path:
                        archive_dir = Path(vault_path) / "40 Archive"
                        archive_dir.mkdir(exist_ok=True)
                        archive_path = archive_dir / note_path.name
                        note_path.rename(archive_path)
                        mapping.note_path = str(archive_path)
                        mapping.obsidian_url = config_manager.generate_obsidian_url(
                            "40 Archive", archive_path.name
                        )
                        db.update_todoist_note_mapping(mapping)

            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_meetings_list(self):
        from .config import config as config_manager

        meetings = config_manager.get_meetings()
        usage = config_manager.get_meeting_usage()
        ordered = sorted(
            [{"alias": alias, **defn} for alias, defn in meetings.items()],
            key=lambda m: usage.get(m["alias"], 0),
            reverse=True,
        )
        self._send_json({"meetings": ordered})

    def _handle_meeting_start(self, body: dict):
        try:
            alias = body.get("alias", "").strip()
            if not alias:
                self._send_json({"success": False, "error": "Alias required"}, 400)
                return
            from .config import config as config_manager

            definition = config_manager.get_meetings().get(alias)
            if not definition:
                self._send_json({"success": False, "error": f"No meeting named '{alias}'"}, 404)
                return

            description = definition["description"]
            project = definition.get("project") or "meetings"
            client = definition.get("client", "")
            tags = list(definition.get("tags", []))
            if "meeting" not in tags:
                tags.append("meeting")
            bartib_project = _build_bartib_project(project, client, tags)

            active = db.get_active_tracking()
            if active:
                _stop_active(active)

            slug = alias.lower().replace(" ", "-")
            bartib = BartibIntegration()
            bartib.start_tracking(description=description, project=bartib_project)
            db.create_tracking_record(
                todoist_task_id=f"meeting:{slug}",
                project_name=bartib_project,
                task_name=description,
                started_at=datetime.now(),
            )
            config_manager.increment_meeting_usage(alias)
            self._send_json({"success": True, "project": bartib_project})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_meeting_define(self, body: dict):
        try:
            alias = body.get("alias", "").strip()
            description = body.get("description", "").strip()
            if not alias or not description:
                self._send_json(
                    {"success": False, "error": "Alias and description are required"}, 400
                )
                return
            project = body.get("project", "").strip()
            client = body.get("client", "").strip()
            tags_raw = body.get("tags", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
            from .config import config as config_manager

            config_manager.set_meeting(
                alias=alias, description=description, project=project, client=client, tags=tags
            )
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_meeting_undefine(self, body: dict):
        try:
            alias = body.get("alias", "").strip()
            if not alias:
                self._send_json({"success": False, "error": "Alias required"}, 400)
                return
            from .config import config as config_manager

            if config_manager.delete_meeting(alias):
                self._send_json({"success": True})
            else:
                self._send_json({"success": False, "error": f"No meeting named '{alias}'"}, 404)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_calendar_events(self, date_str: str):
        from .config import config as config_manager

        gcal_creds = config_manager.get_gcal_credentials_path()
        if not gcal_creds:
            self._send_json(
                {"error": "Google Calendar not configured. Run: taskbridge config gcal"}
            )
            return

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        except ValueError:
            self._send_json({"error": f"Invalid date: {date_str}"}, 400)
            return

        try:
            from .gcal_integration import GoogleCalendarClient

            gcal = GoogleCalendarClient(
                credentials_path=gcal_creds,
                token_path=config_manager.get_gcal_token_path(),
            )
            events = gcal.get_events(target_date, config_manager.get_gcal_calendar_id())
        except Exception as e:
            self._send_json({"error": f"Could not fetch calendar events: {e}"})
            return

        timed_events = [e for e in events if (e.end - e.start).total_seconds() < 86400]

        bartib_file = os.environ.get("BARTIB_FILE")
        existing: list = []
        if bartib_file:
            with contextlib.suppress(Exception):
                existing = _parse_bartib_for_day(target_date)

        recent_projects = _get_recent_bartib_projects(limit=8) if bartib_file else []

        def _fmt_mins(secs: float) -> str:
            m = int(secs // 60)
            h, m = divmod(m, 60)
            return f"{h}h {m}m" if h else f"{m}m"

        result = []
        for ev in timed_events:
            conflicts = [
                {
                    "task_name": r.task_name,
                    "start": r.started_at.strftime("%H:%M"),
                    "end": r.stopped_at.strftime("%H:%M") if r.stopped_at else "active",
                }
                for r in existing
                if r.started_at < ev.end and (r.stopped_at or datetime.now()) > ev.start
            ]
            result.append(
                {
                    "title": ev.title,
                    "start_iso": ev.start.isoformat(),
                    "end_iso": ev.end.isoformat(),
                    "start_fmt": ev.start.strftime("%H:%M"),
                    "end_fmt": ev.end.strftime("%H:%M"),
                    "duration_fmt": _fmt_mins((ev.end - ev.start).total_seconds()),
                    "conflicts": conflicts,
                }
            )

        self._send_json({"events": result, "recent_projects": recent_projects})

    def _handle_calendar_log(self, body: dict):
        try:
            start_iso = body.get("start", "")
            end_iso = body.get("end", "")
            description = body.get("description", "").strip()
            project = body.get("project", "").strip()
            ongoing = bool(body.get("ongoing", False))

            if not all([start_iso, description, project]):
                self._send_json(
                    {"success": False, "error": "start, description, and project are required"},
                    400,
                )
                return

            start_dt = datetime.fromisoformat(start_iso)

            if ongoing:
                active = db.get_active_tracking()
                if active:
                    _stop_active(active)
                bartib = BartibIntegration()
                bartib.start_tracking(
                    description=description,
                    project=project,
                    start_time=start_dt.strftime("%H:%M"),
                )
                db.create_tracking_record(
                    todoist_task_id=f"cal:{start_dt.strftime('%Y%m%d%H%M')}",
                    project_name=project,
                    task_name=description,
                    started_at=start_dt,
                )
                self._send_json({"success": True, "ongoing": True})
            else:
                if not end_iso:
                    self._send_json(
                        {"success": False, "error": "end time required for completed entries"}, 400
                    )
                    return
                end_dt = datetime.fromisoformat(end_iso)
                if end_dt <= start_dt:
                    self._send_json({"success": False, "error": "End must be after start"}, 400)
                    return
                _append_bartib_entry(project, description, start_dt, end_dt)
                self._send_json({"success": True, "ongoing": False})
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
