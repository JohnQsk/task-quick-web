# Changelog

## 2026-10-27

### main (self-written backend)

#### Added
- Agent skill at `.agents/skills/task-web/SKILL.md`: teaches AI agents to manage tasks via the HTTP API (preferred) or by editing the JSON data files directly (fallback), including schema and write-discipline rules
- View completed tasks: toggle button below the open list, served by `GET /api/tasks/completed`, newest first
- Add new tasks from the web UI: description plus optional project, via `POST /api/tasks`
- `--data-dir` server option (and `-DataDir` in `start-web.ps1`) to choose the storage folder; file names are fixed (`tasks.json`, `active.json`, `timelog.jsonl`)
- Simple time tracking: start/stop sessions are logged to `timelog.jsonl`, and the page shows today's total focused time
- Mark tasks as done from the web UI

#### Changed
- Backend no longer shells out to any external task CLI: tasks are stored in a JSON file, pure Python standard library, no WSL required
- Default data directory is `~/workspace/taskweb` so the enclosing git repository can be used for backup/sync

### dstask (branch)

- Variant backed by the [dstask](https://github.com/naggie/dstask) CLI (native Windows binary), kept for reference on the `dstask` branch
- Same UI features: list, add is not included; start/stop/done, description editing (via direct task-file rewrite, since `dstask modify` cannot change summaries), and server-side time tracking
