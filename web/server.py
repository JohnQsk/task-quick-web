import argparse
import json
import re
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

DSTASK_DIR = Path.home() / ".dstask"
TRACK_DIR = Path.home() / ".dstask-web"
TIMELOG = TRACK_DIR / "timelog.jsonl"
ACTIVE_FILE = TRACK_DIR / "active.json"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

PAGE = b'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dstask</title>
<style>
:root { color-scheme: light; font-family: system-ui, sans-serif; }
body { max-width: 860px; margin: 40px auto; padding: 0 16px; background: #f5f6f8; color: #20242a; }
h1 { font-size: 26px; margin-bottom: 4px; }
#summary, #focus { color: #66707c; margin-bottom: 6px; }
#focus { margin-bottom: 16px; }
#refresh { margin-bottom: 20px; background: #66707c; }
#add-form { display: flex; gap: 8px; margin-bottom: 20px; }
#add-form input { padding: 10px 14px; border: 1px solid #d0d4da; border-radius: 7px; font-size: 15px; }
#new-description { flex: 3; }
#new-project { flex: 1; }
#toggle-completed { margin-bottom: 10px; background: #66707c; }
#completed .task { opacity: .7; }
#completed .description { text-decoration: line-through; }
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
<h1>dstask</h1>
<div id="summary">Loading...</div>
<div id="focus"></div>
<button id="refresh" type="button">Refresh</button>
<form id="add-form">
<input id="new-description" placeholder="New task description" maxlength="1000" required>
<input id="new-project" placeholder="project (optional)" maxlength="100">
<button type="submit">Add</button>
</form>
<div id="error" role="alert"></div>
<main id="tasks"></main>
<button id="toggle-completed" type="button">Show completed</button>
<section id="completed"></section>
<script>
const tasksNode = document.getElementById('tasks');
const summaryNode = document.getElementById('summary');
const focusNode = document.getElementById('focus');
const errorNode = document.getElementById('error');
const addForm = document.getElementById('add-form');
const newDescription = document.getElementById('new-description');
const newProject = document.getElementById('new-project');
const completedNode = document.getElementById('completed');
const toggleCompleted = document.getElementById('toggle-completed');
document.getElementById('refresh').addEventListener('click', loadTasks);
let showCompleted = false;

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

addForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorNode.textContent = '';
  try {
    await request('/api/tasks', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Task-Web': '1'},
      body: JSON.stringify({
        description: newDescription.value,
        project: newProject.value
      })
    });
    newDescription.value = '';
    newProject.value = '';
    await loadTasks();
  } catch (error) {
    errorNode.textContent = error.message;
  }
});

toggleCompleted.addEventListener('click', () => {
  showCompleted = !showCompleted;
  toggleCompleted.textContent = showCompleted ? 'Hide completed' : 'Show completed';
  if (!showCompleted) completedNode.replaceChildren();
  loadCompleted();
});

async function loadCompleted() {
  if (!showCompleted) return;
  try {
    const tasks = await request('/api/tasks/completed');
    completedNode.replaceChildren();
    for (const task of tasks) {
      const row = document.createElement('section');
      row.className = 'task';
      const details = document.createElement('div');
      details.className = 'details';
      const description = document.createElement('div');
      description.className = 'description';
      description.textContent = task.summary;
      const meta = document.createElement('div');
      meta.className = 'project';
      meta.textContent = (task.project || 'Inbox') +
        (task.completed ? ' - completed ' + task.completed.slice(0, 16).replace('T', ' ') : '');
      details.append(description, meta);
      row.append(details);
      completedNode.append(row);
    }
  } catch (error) {
    completedNode.replaceChildren();
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
  loadCompleted();
}

loadTasks();
</script>
</body>
</html>'''


def run_dstask(*args):
    try:
        return subprocess.run(
            ["dstask", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError("dstask not found in PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("dstask command timed out")


def clean_output(result):
    return ANSI_RE.sub("", result.stdout + result.stderr).strip()


def list_tasks(show_command):
    result = run_dstask(show_command, "--")
    if result.returncode != 0:
        raise RuntimeError(clean_output(result) or "Could not read tasks")
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        raise RuntimeError("Could not parse dstask output")


def public_task(task):
    status = task.get("status")
    if status == "resolved":
        mapped = "completed"
    elif status == "active":
        mapped = "active"
    else:
        mapped = "pending"
    due = task.get("due") or ""
    return {
        "uuid": task["uuid"],
        "status": mapped,
        "summary": task["summary"],
        "project": task.get("project", ""),
        "created": task.get("created"),
        "due": None if due.startswith("0001-") else due,
        "completed": task.get("resolved") if mapped == "completed" else None,
    }


def open_tasks():
    return [public_task(task) for task in list_tasks("show-open")]


def completed_tasks():
    tasks = [public_task(task) for task in list_tasks("show-resolved")]
    tasks.sort(key=lambda task: task.get("completed") or "", reverse=True)
    return tasks[:100]


def find_task(uuid):
    for task in list_tasks("show-open"):
        if task.get("uuid") == uuid:
            return task
    return None


def add_task(description, project):
    result = run_dstask("add", description, "--")
    output = clean_output(result)
    if result.returncode != 0:
        raise RuntimeError(output or "Add failed")
    id_match = re.search(r"Added (\d+):", output)
    if not id_match:
        raise RuntimeError("Could not determine new task ID")
    task_id = id_match.group(1)
    if project:
        modify = run_dstask("modify", task_id, f"project:{project}", "--")
        if modify.returncode != 0:
            raise RuntimeError(clean_output(modify) or "Could not set project")
    for task in list_tasks("show-open"):
        if str(task.get("id")) == task_id:
            return task
    raise RuntimeError("Could not find the new task")


def edit_summary(task, description):
    task_file = DSTASK_DIR / task["status"] / f"{task['uuid']}.yml"
    if not task_file.is_file():
        raise RuntimeError("Task file not found")
    lines = task_file.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("summary:"):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = "summary: " + json.dumps(
                description, ensure_ascii=False
            ) + newline
            break
    else:
        raise RuntimeError("Task file has no summary field")
    task_file.write_text("".join(lines), encoding="utf-8")
    run_dstask("git", "add", "-A")
    commit = run_dstask("git", "commit", "-m", f"Edited task {task['id']}")
    if commit.returncode != 0:
        raise RuntimeError(clean_output(commit) or "Could not commit edit")
    updated = find_task(task["uuid"])
    if not updated or updated.get("summary") != description:
        raise RuntimeError("Edit did not take effect")


def now_local():
    return datetime.now().astimezone()


def load_active():
    try:
        return json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_active(active):
    TRACK_DIR.mkdir(exist_ok=True)
    ACTIVE_FILE.write_text(
        json.dumps(active, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def track_start(task):
    try:
        active = load_active()
        active[task["uuid"]] = {
            "summary": task["summary"],
            "project": task.get("project", ""),
            "start": now_local().isoformat(timespec="seconds"),
        }
        save_active(active)
    except OSError:
        pass


def track_stop(task):
    try:
        active = load_active()
        entry = active.pop(task["uuid"], None)
        save_active(active)
        if not entry:
            return
        end = now_local()
        start = datetime.fromisoformat(entry["start"])
        record = {
            "uuid": task["uuid"],
            "summary": task["summary"],
            "project": task.get("project", ""),
            "start": entry["start"],
            "end": end.isoformat(timespec="seconds"),
            "seconds": max(0, round((end - start).total_seconds())),
        }
        TRACK_DIR.mkdir(exist_ok=True)
        with TIMELOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (OSError, ValueError):
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
        if start.date() == today:
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
            try:
                self.send_json(open_tasks())
            except Exception as error:
                self.send_error_json(str(error), 500)
        elif path == "/api/tasks/completed":
            try:
                self.send_json(completed_tasks())
            except Exception as error:
                self.send_error_json(str(error), 500)
        elif path == "/api/focus":
            try:
                active_uuids = {
                    task["uuid"]
                    for task in list_tasks("show-open")
                    if task.get("status") == "active"
                }
                self.send_json({"today_seconds": focus_seconds_today(active_uuids)})
            except Exception as error:
                self.send_error_json(str(error), 500)
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error_json("Not found", 404)

    def do_POST(self):
        if self.headers.get("X-Task-Web") != "1":
            self.send_error_json("Forbidden", 403)
            return
        path = urlparse(self.path).path
        if path == "/api/tasks":
            payload = self.read_json_body()
            if payload is None:
                return
            description = self.validate_description(payload.get("description"))
            if description is None:
                return
            project = payload.get("project") or ""
            if not isinstance(project, str):
                self.send_error_json("Invalid project")
                return
            project = project.strip()
            if len(project) > 100:
                self.send_error_json("Project name is too long", 413)
                return
            try:
                task = add_task(description, project)
            except Exception as error:
                self.send_error_json(str(error), 500)
                return
            self.send_json({"ok": True, "task": public_task(task)}, 201)
            return
        match = re.fullmatch(
            r"/api/tasks/([0-9a-fA-F-]{36})/(start|stop|done|description)",
            path,
        )
        if not match:
            self.send_error_json("Not found", 404)
            return
        task_uuid, action = match.groups()
        try:
            task = find_task(task_uuid.lower())
            if not task:
                self.send_error_json("Task not found", 404)
                return
            if action == "description":
                payload = self.read_json_body()
                if payload is None:
                    return
                description = self.validate_description(payload.get("description"))
                if description is None:
                    return
                edit_summary(task, description)
                self.send_json({"ok": True})
                return
            result = run_dstask(action, str(task["id"]), "--")
            if result.returncode != 0:
                self.send_error_json(clean_output(result) or "Task command failed")
                return
            if action == "start":
                track_start(task)
            else:
                track_stop(task)
            self.send_json({"ok": True, "message": clean_output(result)})
        except Exception as error:
            self.send_error_json(str(error), 500)

    def validate_description(self, description):
        if not isinstance(description, str) or not description.strip():
            self.send_error_json("Description cannot be empty")
            return None
        description = description.strip()
        if len(description) > 1000:
            self.send_error_json("Description is too long", 413)
            return None
        return description

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error_json("Invalid Content-Length")
            return None
        if content_length > 4096:
            self.send_error_json("Request body is too large", 413)
            return None
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error_json("Invalid JSON")
            return None
        if not isinstance(payload, dict):
            self.send_error_json("Invalid JSON")
            return None
        return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"dstask web: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
