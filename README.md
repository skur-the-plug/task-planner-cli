# Task Planner CLI

A dependency-free Python task tracker and day planner for the terminal. It can
turn your open tasks, daily notes, available hours, energy level, and fixed
appointments into a practical Markdown schedule. AI planning is optional: if
no supported AI CLI is available, Task Planner automatically uses its built-in
local planner.

## Requirements

- Python 3.8 or newer
- Bash (for the convenient `task` shell command below)
- Optional: [OpenAI Codex CLI](https://developers.openai.com/codex/cli/) or
  [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI plans

There are no Python packages to install.

## Install

Clone the repository:

```bash
git clone https://github.com/skur-the-plug/task-planner-cli.git ~/apps/Task
```

Test it directly:

```bash
cd ~/apps/Task
python3 task-cli.py --help
```

To use `task` from any directory, add this function to `~/.bashrc`:

```bash
task() {
    (cd "$HOME/apps/Task" && python3 task-cli.py "$@")
}
```

Reload the shell configuration:

```bash
source ~/.bashrc
task --help
```

If you cloned the project somewhere else, replace `$HOME/apps/Task` with that
directory.

## Task commands

```bash
task add "finish project outline"
task list
task list todo
task list in-progress
task done
task update 1 "finish and send project outline"
task mark-in-progress 1
task mark-done 1
task delete 1
```

## Daily planning

Run the interactive planner:

```bash
task plan
```

It asks for your working window, energy, main focus, and fixed appointments.
The generated plan is saved to `plans/YYYY-MM-DD.md`.

Useful variants:

```bash
# Let Task Planner try Codex, then Gemini, then the local planner
task plan --ai auto

# Select a planner explicitly
task plan --ai codex
task plan --ai gemini
task plan --ai none

# Supply everything non-interactively and print without saving
task plan --no-questions --start 09:00 --end 17:30 \
  --focus "finish the project outline" \
  --energy high \
  --fixed "13:00 lunch" \
  --dry-run
```

Add context during the day and view today's saved plan:

```bash
task note "Ask Sam about the launch date"
task today
```

Notes are saved to `notes/YYYY-MM-DD.md` and included the next time you create
that day's plan.

## AI planner setup

AI is not required. `task plan --ai none` always works offline using only the
Python standard library.

### Codex CLI

Install and authenticate Codex using the
[official Codex CLI setup guide](https://developers.openai.com/codex/cli/), then
verify that it is available:

```bash
codex --version
codex login
task plan --ai codex
```

### Gemini CLI

Install Gemini CLI using its
[official installation guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/index.md),
launch it once to complete authentication, and then test the planner:

```bash
gemini --version
gemini
task plan --ai gemini
```

With `--ai auto` (the default), Task Planner tries Codex first and Gemini
second. If neither command is installed, authentication is missing, the call
fails, or it takes longer than 90 seconds, it prints a short explanation and
uses the local planner instead.

When an AI planner is selected, open task descriptions, today's notes, focus,
energy level, available hours, and fixed appointments are sent to that AI
provider. Codex runs read-only and without persisting a session. Use `--ai none`
for private or offline-only planning.

## Local data

The application creates and updates:

- `tasks.json` — task database
- `plans/` — generated daily plans
- `notes/` — timestamped daily notes

All three are ignored by Git, so new personal task data is not committed.
`examples/tasks.example.json` shows the data format without containing personal
tasks. Back up the local files separately if they matter to you.

## Troubleshooting

- **`task: command not found`** — add the shell function above and run
  `source ~/.bashrc`, or open a new terminal.
- **`codex was not found` / `gemini was not found`** — install that optional
  CLI or use `task plan --ai none`.
- **AI authentication or network error** — authenticate the selected CLI and
  retry it directly. Task Planner will still produce a local plan when the AI
  command fails.
