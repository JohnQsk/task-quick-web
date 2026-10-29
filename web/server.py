import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PAGE = b'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taskwarrior</title>
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
<h1>Taskwarrior</h1>
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


WSL_PREFIX = ["wsl.exe"]


def run_wsl(*args):
    try:
        return subprocess.run(
            [*WSL_PREFIX, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError("wsl.exe not found")
    except subprocess.TimeoutExpired:
        raise RuntimeError("command timed out")


def run_task(*args):
    return run_wsl("task", *args)


def export_tasks(*filters):
    result = run_task(*filters, "export")
    if result.returncode != 0:
        output = result.stdout + result.stderr
        if "No matches" in output:
            return []
        raise RuntimeError(output.strip() or "Could not read tasks")
    return json.loads(result.stdout or "[]")


def iso_local(taskwarrior_time):
    if not taskwarrior_time:
        return None
    moment = datetime.strptime(taskwarrior_time, "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    return moment.astimezone().isoformat(timespec="seconds")


def public_task(task):
    if task.get("status") == "completed":
        status = "completed"
    elif task.get("start"):
        status = "active"
    else:
        status = "pending"
    return {
        "uuid": task["uuid"],
        "status": status,
        "summary": task["description"],
        "project": task.get("project", ""),
        "created": iso_local(task.get("entry")),
        "due": iso_local(task.get("due")),
        "completed": iso_local(task.get("end"))
        if task.get("status") == "completed"
        else None,
    }


def open_tasks():
    return [public_task(task) for task in export_tasks("status:pending")]


def completed_tasks():
    tasks = [
        public_task(task) for task in export_tasks("status:completed")
    ]
    tasks.sort(key=lambda task: task.get("completed") or "", reverse=True)
    return tasks[:100]


def add_task(description, project):
    command = ["add"]
    if project:
        command.append(f"project:{project}")
    command.append(description)
    result = run_task(*command)
    if result.returncode != 0:
        raise RuntimeError((result.stdout + result.stderr).strip() or "Add failed")
    latest = export_tasks("+LATEST")
    if not latest:
        raise RuntimeError("Could not find the new task")
    return latest[0]


def focus_seconds_today():
    try:
        result = run_wsl("timew", "export", ":today")
    except RuntimeError:
        return 0
    if result.returncode != 0:
        return 0
    try:
        intervals = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return 0
    total = 0
    now = datetime.now(timezone.utc)
    midnight = (
        now.astimezone()
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc)
    )
    for interval in intervals:
        try:
            start = datetime.strptime(interval["start"], "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
            start = max(start, midnight)
            if interval.get("end"):
                end = datetime.strptime(interval["end"], "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
            else:
                end = now
        except (KeyError, ValueError):
            continue
        total += max(0, round((end - start).total_seconds()))
    return total


def wait_for_hook(task_id):
    details_result = run_task(task_id, "export")
    try:
        details = json.loads(details_result.stdout or "[]")
    except json.JSONDecodeError:
        return
    if details and details[0].get("start"):
        started_at = datetime.strptime(
            details[0]["start"], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        delay = 1.1 - (datetime.now(timezone.utc) - started_at).total_seconds()
        if delay > 0:
            time.sleep(delay)


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
                self.send_json({"today_seconds": focus_seconds_today()})
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
        task_id, action = match.groups()
        if action == "description":
            payload = self.read_json_body()
            if payload is None:
                return
            description = self.validate_description(payload.get("description"))
            if description is None:
                return
            command = ["rc.confirmation=no", task_id, "modify", f"description:{description}"]
        else:
            command = ["rc.confirmation=no", task_id, action]
            if action in ("stop", "done"):
                wait_for_hook(task_id)
        try:
            result = run_task(*command)
        except Exception as error:
            self.send_error_json(str(error), 500)
            return
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            self.send_error_json(output or "Task command failed")
            return
        self.send_json({"ok": True, "message": output})

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
    global WSL_PREFIX
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--distro", default="Ubuntu", help="WSL distribution name")
    parser.add_argument("--wsl-user", default="", help="WSL user (default user if empty)")
    args = parser.parse_args()
    WSL_PREFIX = ["wsl.exe", "-d", args.distro]
    if args.wsl_user:
        WSL_PREFIX += ["-u", args.wsl_user]
    WSL_PREFIX.append("--")
    server = HTTPServer((args.host, args.port), Handler)
    print(f"Taskwarrior web: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
