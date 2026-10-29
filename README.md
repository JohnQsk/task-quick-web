# task-quick-web

A tiny local web UI for [dstask](https://github.com/naggie/dstask), focused on the actions used most often: adding, starting, stopping, completing, and editing tasks.

This `dstask` branch shells out to the `dstask` CLI for all task operations. Other branches: `main` is a self-contained pure-Python variant, `taskwarrior` uses Taskwarrior/Timewarrior via WSL.

## Features

- List open tasks
- Add new tasks (with optional project)
- Start and stop tasks from a browser
- Mark tasks as done
- View completed tasks (toggle button below the open list)
- Edit task descriptions
- Simple time tracking: starting/stopping a task logs the session to `~/.dstask-web/timelog.jsonl`, and the page shows today's total focused time
- Manual refresh (Refresh button, no polling)
- Sync button: runs `dstask sync` (git pull + push to the configured remote) and reloads the list
- Localhost-only access by default
- No Python dependencies outside the standard library

## Requirements

- Python 3 (Windows)
- dstask (`dstask.exe` in your `PATH` — download `dstask-windows-amd64.exe` from the [releases page](https://github.com/naggie/dstask/releases))

## Quick start on Windows

Put `dstask.exe` somewhere in your `PATH`, then start the web UI from this repository:

```powershell
.\start-web.ps1
```

The page opens at <http://127.0.0.1:8765>.

## Known limitations

- dstask parses tokens like `project:x`, `+tag` and `P0` anywhere in a task summary, so avoid those patterns in descriptions entered via the Add form.
- `dstask modify` cannot change a task summary, so description edits are applied by rewriting the task file and committing via `dstask git`.
- Time tracking is done by the server itself; dstask has no equivalent of the Timewarrior hook.

## Security

This UI has no authentication system. Keep it bound to `127.0.0.1`, and do not expose the port to a LAN or the public internet.

## Current scope

This is an early personal prototype. It intentionally supports only open/completed task display, add, start/stop, marking done, description editing, and basic time tracking. A license will be selected before the repository is made public.
