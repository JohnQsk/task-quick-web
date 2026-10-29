# task-quick-web

A tiny local web UI for [dstask](https://github.com/naggie/dstask), focused on the actions used most often: starting, stopping, completing, and editing task descriptions.

The server runs locally as a native Windows process and calls the `dstask` command directly. No WSL required.

## Features

- List open tasks
- Start and stop tasks from a browser
- Mark tasks as done
- Edit task descriptions
- Simple time tracking: starting/stopping a task logs the session to `~/.dstask-web/timelog.jsonl`, and the page shows today's total focused time
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

## Security

This UI has no authentication system. Keep it bound to `127.0.0.1`, and do not expose the port to a LAN or the public internet.

## Current scope

This is an early personal prototype. It intentionally supports only open-task display, start/stop, marking done, and description editing. A license will be selected before the repository is made public.
