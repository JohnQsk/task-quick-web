# task-quick-web

A tiny local web UI for [Taskwarrior](https://taskwarrior.org/), focused on the actions used most often: adding, starting, stopping, completing, and editing tasks.

This `taskwarrior` branch shells out to the `task` CLI for all task operations and reads [Timewarrior](https://timewarrior.net/) data for focus time. Other branches: `main` is a self-contained pure-Python variant, `dstask` uses the dstask CLI.

## Features

- List open tasks
- Add new tasks (with optional project)
- Start and stop tasks from a browser
- Mark tasks as done
- View completed tasks (toggle button below the open list)
- Edit task descriptions
- Today's focused time, computed from Timewarrior intervals (`timew export :today`)
- Localhost-only access by default
- No Python dependencies outside the standard library

## Requirements

- Python 3
- Taskwarrior 2.x
- Timewarrior (optional, for the focus-time display)
- WSL on Windows (Taskwarrior and Timewarrior have no native Windows build)

## Quick start on Windows

Install Taskwarrior in WSL:

```powershell
wsl.exe -d Ubuntu -u root -- apt-get install -y taskwarrior
```

Install Timewarrior and its Taskwarrior hook if you want automatic time tracking on start/stop:

```powershell
wsl.exe -d Ubuntu -u root -- apt-get install -y timewarrior
```

Copy `on-modify.timewarrior` into the `hooks` directory below your configured Taskwarrior `data.location`, then make it executable.

Start the web UI from this repository. The server itself runs natively on Windows and only shells into WSL for each `task`/`timew` command, so the WSL VM can idle and release memory whenever the page is closed:

```powershell
.\start-web.ps1
```

For non-default WSL distributions or users:

```powershell
.\start-web.ps1 -Distro Ubuntu -WslUser yourname
```

The page opens at <http://127.0.0.1:8765>.

## CLI and agent access

The server is stateless — all task data lives in Taskwarrior and Timewarrior, so anything (a shell, a script, or an AI agent) can read and write the same data through the CLI while the web UI is running. Changes show up in the web UI on the next manual Refresh.

Examples (from Windows):

```powershell
wsl -d Ubuntu -- task status:pending export   # read open tasks as JSON
wsl -d Ubuntu -- task add "write report" project:work
wsl -d Ubuntu -- task <uuid> start            # also starts Timewarrior via the hook
wsl -d Ubuntu -- task <uuid> done
wsl -d Ubuntu -- timew export :today          # today's focus intervals as JSON
```

## Security

This UI has no authentication system. Keep it bound to `127.0.0.1`, and do not expose the port to a LAN or the public internet.

## Current scope

This is an early personal prototype. It intentionally supports only open/completed task display, add, start/stop, marking done, description editing, and a focus-time summary. Released under the MIT license.
