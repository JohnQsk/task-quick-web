import argparse
import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

STORE_DIR = Path.home() / ".taskweb"
TASKS_FILE = STORE_DIR / "tasks.json"
TIMELOG = STORE_DIR / "timelog.jsonl"
ACTIVE_FILE = STORE_DIR / "active.json"

PAGE = b'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tasks</title>
<style>
:root { color-scheme: light; font-family: system-ui, sans-serif; }
body { max-width: 860px; margin: 40px auto; padding: 0 16px; background: #f5f6f8; color: #20242a; }
h1 { font-size: 26px; margin-bottom: 4px; }
#summary, #focus { color: #66707c; margin-bottom: 6px; }
#focus { margin-bottom: 24px; }
.task { display: flex; align-items: center; gap: 16px; padding: 18px; margin: 10px 0; background: white; border-radius: 10px; box-shadow: 0 1px 4px #0001; }
.details { flex: 1; min-width: 0; }
.description { overflow-wrap: anywhere; line-height: 1.45; }
.project { color: #66707c; font-size: 13px; margin-top: 6px; }
.actions { display: flex; flex: none; gap: 8px; }
button { min-width: 88px; padding: 10px 18px; border: 0; border-radius: 7px; background: #1769aa; color: white; font-size: 15px; cursor: pointer; }
button.edit { background: #66707c; }
button.stop { background: #a43b32; }
button.done { background: #2e7d4f; }
button:disabled { opacity: .5; cursor: wait; }
#error { color: #a43b32; white-space: pre-wrap; }
.empty { color: #66707c; padding: 24px 0; }
</style>
</head>
<body>
<h1>Tasks</h1>
<div id="summary">Loading...</div>
<div id="focus"></div>
<div id="error" role="alert"></div>
<main id="tasks"></main>
<script>
const tasksNode = document.getElementById('tasks');
const summaryNode = document.getElementById('summary');
const focusNode = document.getElementById('focus');
const errorNode = document.getElementById('error');

async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed');
  return body;
}

async function changeTask(uuid, action, button) {
  button.disabled = true;
  errorNode.textContent = '';
  try {
    await request('/api/tasks/' + uuid + '/' + action, {
      method: 'POST',
      headers: {'X-Task-Web': '1'}
    });
    await loadTasks();
  } catch (error) {
    errorNode.textContent = error.message;
    button.disabled = false;
  }
}

async function editTask(task, button) {
  const description = window.prompt('Edit task description', task.summary);
  if (description === null || description.trim() === task.summary) return;
  button.disabled = true;
  errorNode.textContent = '';
  try {
    await request('/api/tasks/' + task.uuid + '/description', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Task-Web': '1'},
      body: JSON.stringify({description: description})
    });
    await loadTasks();
  } catch (error) {
    errorNode.textContent = error.message;
    button.disabled = false;
  }
}

async function loadFocus() {
  try {
    const focus = await request('/api/focus');
    const hours = Math.floor(focus.today_seconds / 3600);
    const minutes = Math.floor(focus.today_seconds % 3600 / 60);
    focusNode.textContent = 'Today focused: ' + (hours ? hours + 'h ' : '') + minutes + 'm';
  } catch (error) {
    focusNode.textContent = '';
  }
}

async function loadTasks() {
  try {
    const tasks = await request('/api/tasks');
    const active = tasks.filter(task => task.status === 'active').length;
    summaryNode.textContent = tasks.length + ' open / ' + active + ' active';
    tasksNode.replaceChildren();
    if (!tasks.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = 'No open tasks.';
      tasksNode.append(empty);
    } else {
      for (const task of tasks) {
        const row = document.createElement('section');
        row.className = 'task';
        const details = document.createElement('div');
        details.className = 'details';
        const description = document.createElement('div');
        description.className = 'description';
        description.textContent = task.summary;
        const project = document.createElement('div');
        project.className = 'project';
        project.textContent = task.project || 'Inbox';
        details.append(description, project);
        const actions = document.createElement('div');
        actions.className = 'actions';
        const editButton = document.createElement('button');
        editButton.textContent = 'Edit';
        editButton.className = 'edit';
        editButton.addEventListener('click', () => editTask(task, editButton));
        const button = document.createElement('button');
        const isActive = task.status === 'active';
        button.textContent = isActive ? 'Stop' : 'Start';
        button.className = isActive ? 'stop' : '';
        button.addEventListener('click', () => changeTask(task.uuid, isActive ? 'stop' : 'start', button));
        const doneButton = document.createElement('button');
        doneButton.textContent = 'Done';
        doneButton.className = 'done';
        doneButton.addEventListener('click', () => changeTask(task.uuid, 'done', doneButton));
        actions.append(editButton, button, doneButton);
        row.append(details, actions);
        tasksNode.append(row);
      }
    }
    errorNode.textContent = '';
  } catch (error) {
    errorNode.textContent = error.message;
    summaryNode.textContent = 'Could not load tasks';
  }
  loadFocus();
}

loadTasks();
setInterval(loadTasks, 15000);
</script>
</body>
</html>'''


def now_local():
    return datetime.now().astimezone()


def load_store():
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tasks": []}


def save_store(store):
    STORE_DIR.mkdir(exist_ok=True)
    temp = STORE_DIR / "tasks.json.tmp"
    temp.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    temp.replace(TASKS_FILE)


def public_task(task):
    return {
        "uuid": task["uuid"],
        "status": "active" if task.get("start") else "pending",
        "summary": task["description"],
        "project": task.get("project", ""),
        "created": task.get("created"),
        "due": task.get("due"),
    }


def open_tasks():
    return [
        public_task(task)
        for task in load_store()["tasks"]
        if task.get("status") == "pending"
    ]


def find_task(store, task_uuid):
    for task in store["tasks"]:
        if task.get("uuid") == task_uuid and task.get("status") == "pending":
            return task
    return None


def load_active():
    try:
        return json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_active(active):
    STORE_DIR.mkdir(exist_ok=True)
    ACTIVE_FILE.write_text(
        json.dumps(active, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def track_start(task):
    try:
        active = load_active()
        active[task["uuid"]] = {
            "summary": task["description"],
            "project": task.get("project", ""),
            "start": task["start"],
        }
        save_active(active)
    except OSError:
        pass


def track_stop(task, started_at):
    try:
        active = load_active()
        entry = active.pop(task["uuid"], None)
        save_active(active)
        start_text = entry["start"] if entry else started_at
        if not start_text:
            return
        end = now_local()
        start = datetime.fromisoformat(start_text)
        record = {
            "uuid": task["uuid"],
            "summary": task["description"],
            "project": task.get("project", ""),
            "start": start_text,
            "end": end.isoformat(timespec="seconds"),
            "seconds": max(0, round((end - start).total_seconds())),
        }
        STORE_DIR.mkdir(exist_ok=True)
        with TIMELOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (OSError, ValueError, KeyError):
        pass


def focus_seconds_today(active_uuids):
    today = now_local().date()
    total = 0
    try:
        with TIMELOG.open(encoding="utf-8") as log:
            for line in log:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    if datetime.fromisoformat(record["end"]).date() == today:
                        total += record.get("seconds", 0)
                except (KeyError, ValueError):
                    continue
    except OSError:
        pass
    now = now_local()
    for task_uuid, entry in load_active().items():
        if task_uuid not in active_uuids:
            continue
        try:
            start = datetime.fromisoformat(entry["start"])
        except (KeyError, ValueError):
            continue
        total += max(0, round((now - start).total_seconds()))
    return total


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, value, status=200):
        content = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_bytes(content, "application/json; charset=utf-8", status)

    def send_error_json(self, message, status=400):
        self.send_json({"error": message}, status)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_bytes(PAGE, "text/html; charset=utf-8")
        elif path == "/api/tasks":
            self.send_json(open_tasks())
        elif path == "/api/focus":
            active_uuids = {
                task["uuid"]
                for task in load_store()["tasks"]
                if task.get("status") == "pending" and task.get("start")
            }
            self.send_json({"today_seconds": focus_seconds_today(active_uuids)})
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error_json("Not found", 404)

    def do_POST(self):
        if self.headers.get("X-Task-Web") != "1":
            self.send_error_json("Forbidden", 403)
            return
        match = re.fullmatch(
            r"/api/tasks/([0-9a-fA-F-]{36})/(start|stop|done|description)",
            urlparse(self.path).path,
        )
        if not match:
            self.send_error_json("Not found", 404)
            return
        task_uuid, action = match.groups()
        store = load_store()
        task = find_task(store, task_uuid.lower())
        if not task:
            self.send_error_json("Task not found", 404)
            return
        if action == "description":
            description = self.read_description()
            if description is None:
                return
            task["description"] = description
        elif action == "start":
            task["start"] = task.get("start") or now_local().isoformat(timespec="seconds")
            track_start(task)
        elif action == "stop":
            started_at = task.get("start")
            task["start"] = None
            track_stop(task, started_at)
        elif action == "done":
            started_at = task.get("start")
            task["start"] = None
            task["status"] = "completed"
            task["completed"] = now_local().isoformat(timespec="seconds")
            track_stop(task, started_at)
        try:
            save_store(store)
        except OSError as error:
            self.send_error_json(f"Could not save tasks: {error}", 500)
            return
        self.send_json({"ok": True})

    def read_description(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error_json("Invalid Content-Length")
            return None
        if content_length > 4096:
            self.send_error_json("Description is too long", 413)
            return None
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error_json("Invalid JSON")
            return None
        description = payload.get("description")
        if not isinstance(description, str) or not description.strip():
            self.send_error_json("Description cannot be empty")
            return None
        description = description.strip()
        if len(description) > 1000:
            self.send_error_json("Description is too long", 413)
            return None
        return description


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"Task web: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
