# task-quick-web

A tiny local web UI for managing a personal task list, focused on the actions used most often: starting, stopping, completing, and editing task descriptions.

This `main` branch is fully self-contained: tasks are stored in a JSON file and the server is pure Python standard library. See the `dstask` branch for a variant backed by the [dstask](https://github.com/naggie/dstask) CLI.

## Features

- List open tasks
- Add new tasks (with optional project)
- Start and stop tasks from a browser
- Mark tasks as done
- View completed tasks (toggle button below the open list)
- Edit task descriptions
- Simple time tracking: starting/stopping a task logs the session to `~/.taskweb/timelog.jsonl`, and the page shows today's total focused time
- Localhost-only access by default
- No dependencies outside the Python standard library

## Requirements

- Python 3 (Windows)

## Quick start

```powershell
.\start-web.ps1
```

The page opens at <http://127.0.0.1:8765>.

## Data storage

All data lives under `~/workspace/taskweb/` by default, so the enclosing `workspace` git repository doubles as a backup/sync tool. Use `--data-dir` (or `.\start-web.ps1 -DataDir <folder>`) to choose a different folder; file names are fixed:

- `tasks.json` — the task list (open and completed tasks)
- `active.json` — start timestamps of currently running tasks
- `timelog.jsonl` — one JSON record per finished focus session

## Security

This UI has no authentication system. Keep it bound to `127.0.0.1`, and do not expose the port to a LAN or the public internet.

## Current scope

This is an early personal prototype. It intentionally supports only open-task display, start/stop, marking done, description editing, and basic time tracking. Released under the MIT license.
