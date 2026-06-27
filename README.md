# Task Planner CLI

A small local task tracker and day planner for the terminal.

## Usage

```bash
task list
task add "finish certifs"
task mark-in-progress 1
task mark-done 1
task plan
task today
task note "remember to call family"
```

`task plan` asks a few planning questions, reads open tasks, and creates a Markdown plan for the day.

By default it tries available AI CLIs, then falls back to a local planner:

```bash
task plan --ai auto
task plan --ai codex
task plan --ai gemini
task plan --ai none
```

Plans are saved in `plans/YYYY-MM-DD.md`. Notes are saved in `notes/YYYY-MM-DD.md`.

## Shell Setup

Add this to `~/.bashrc`:

```bash
task() {
    (cd /path/to/Task && python /path/to/Task/task-cli.py "$@")
}
```

## Data

The app stores local data in:

- `tasks.json`
- `plans/`
- `notes/`

These are ignored by git so personal tasks and plans stay private.
