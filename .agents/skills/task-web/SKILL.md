---
name: task-web
description: Read and write tasks in the task-quick-web system (list, add, start, stop, complete, edit, focus time) via its HTTP API or, as a fallback, its JSON data files
type: prompt
whenToUse: When the user asks to list, add, start, stop, complete, or edit tasks, or asks about today's focused time, in the task-quick-web system
---

# task-web task access

The user runs a local task manager ("task-quick-web"): a stdlib Python web server with a browser UI, storing tasks in plain JSON files. Two access methods exist. **Always prefer the HTTP API**; edit files directly only when the server is down.

## Method 1 (preferred): HTTP API

The server listens on `http://127.0.0.1:8765` by default. All POST requests require the header `X-Task-Web: 1` (CSRF guard); omitting it returns 403.

| Action | Request |
| --- | --- |
| List open tasks | `curl -s http://127.0.0.1:8765/api/tasks` |
| List completed tasks | `curl -s http://127.0.0.1:8765/api/tasks/completed` |
| Today's focused seconds | `curl -s http://127.0.0.1:8765/api/focus` |
| Add task | `curl -s -X POST -H 'X-Task-Web: 1' -H 'Content-Type: application/json' --data '{"description": "...", "project": "..."}' http://127.0.0.1:8765/api/tasks` |
| Start / stop / done | `curl -s -X POST -H 'X-Task-Web: 1' http://127.0.0.1:8765/api/tasks/<uuid>/<start\|stop\|done>` |
| Edit description | `curl -s -X POST -H 'X-Task-Web: 1' -H 'Content-Type: application/json' --data '{"description": "..."}' http://127.0.0.1:8765/api/tasks/<uuid>/description` |

Notes:

- Task objects have `uuid`, `status` (`pending` / `active` / `completed`), `summary`, `project`, `created`, `due`, `completed`.
- Descriptions must be 1–1000 chars after trimming; project ≤ 100 chars.
- The API performs validation and time tracking automatically — another reason to prefer it.
- On Windows Git Bash, pass JSON bodies with `--data @file.json` (UTF-8 file) rather than inline, because inline non-ASCII arguments may be mangled by the shell's codepage conversion.

## Method 2 (fallback): direct file access

Use only when the server is not running. Data directory: `~/workspace/taskweb` by default (the server may have been started with `--data-dir` pointing elsewhere; ask the user if unsure). File names are fixed.

### `tasks.json`

```json
{"tasks": [
  {"uuid": "550e8400-e29b-41d4-a716-446655440000",
   "description": "Example task",
   "project": "work",
   "tags": [],
   "status": "pending",
   "start": null,
   "created": "2026-10-29T09:00:00+08:00",
   "due": null,
   "completed": null}
]}
```

Field rules:

- `uuid`: random UUID v4, lowercase.
- `status`: `"pending"` (open) or `"completed"`. Open tasks appear in the UI; completed tasks are history — keep them.
- `start`: ISO 8601 local timestamp with offset (e.g. `2026-10-29T09:30:00+08:00`) while the task is being worked on, otherwise `null`. A pending task with `start` set shows as "active".
- `completed`: same timestamp format, set when `status` becomes `"completed"`, otherwise absent/null.
- `created` / `due`: same format or `null`.
- Preserve any fields you do not recognize — do not strip them.

### Write discipline

1. Read the file fresh immediately before modifying (never reuse a stale copy).
2. Write atomically: write `<name>.tmp` in the same directory, then rename over the target.
3. Use UTF-8 without BOM, `ensure_ascii=False`-style output (raw non-ASCII characters).
4. If you set or clear `start` via direct file edits, also maintain the time-tracking files below; otherwise today's focus time will be wrong.

### `active.json` and `timelog.jsonl`

- `active.json`: object mapping task uuid → `{"summary", "project", "start"}` for currently running tasks. Set on start, remove the key on stop/done.
- `timelog.jsonl`: one JSON object per finished session: `{"uuid", "summary", "project", "start", "end", "seconds"}`.

## Boundaries

- The JSON data files contain personal task content. Do not commit them to any git repository and do not send them anywhere.
- The web UI polls every 15 s on this backend, so direct file edits appear automatically; no server restart needed.
