import argparse
import json
import os
import re
import shutil
import subprocess
import textwrap
from datetime import date, datetime, timedelta


TASKS_FILE = "tasks.json"
PLANS_DIR = "plans"
NOTES_DIR = "notes"


if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, "w") as f:
        json.dump([], f)

with open(TASKS_FILE) as f:
    data = json.load(f)


def color_text(text, color):
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "cyan": "\033[36m",
        "reset": "\033[0m",
    }

    return colors.get(color, "") + text + colors["reset"]


def save():
    with open(TASKS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def printer(task):
    print()
    print(color_text("[", "red"), end="")
    print(task["id"], end="")
    print(color_text("]", "red"), end=" ")
    print("\033[1m" + task["description"] + "\033[0m" + color_text("   -  ", "yellow"), end="")
    print(color_text(task["status"], "yellow"))
    print(color_text(f"   createdAt: {task['createdAt']}", "blue"))
    print(color_text(f"   updatedAt: {task['updatedAt']}", "yellow"))
    for _ in range(2):
        print()


def match_was_not_found():
    print()
    print("------match was not found------")
    print()
    print("------please try another id------")
    print()


def list_by_filter(filter):
    for task in data:
        if task["status"] == filter:
            printer(task)


def mark_as(status, done_mip):
    match_found = False
    for task in data:
        if task["id"] == done_mip:
            match_found = True
            task["status"] = status
            task["updatedAt"] = datetime.now().isoformat(timespec="seconds")
            print("updated")
            break
    if match_found is False:
        match_was_not_found()
    save()


def open_tasks():
    return [task for task in data if task["status"] in ("todo", "in-progress")]


def parse_hhmm(value):
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        raise argparse.ArgumentTypeError("use HH:MM, for example 09:30")
    return parsed.time()


def combine_today(time_value):
    return datetime.combine(date.today(), time_value)


def combine_window(start, end):
    start_at = combine_today(start)
    end_at = combine_today(end)
    if end_at <= start_at:
        end_at += timedelta(days=1)
    return start_at, end_at


def format_time(value):
    return value.strftime("%H:%M")


def format_window(start, end):
    start_at, end_at = combine_window(start, end)
    suffix = " next day" if end_at.date() != start_at.date() else ""
    return f"{format_time(start_at)} to {format_time(end_at)}{suffix}"


def fixed_start(item):
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", item)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    return datetime.combine(date.today(), datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time())


def fixed_start_for_window(item, start_at, end_at):
    starts_at = fixed_start(item)
    if starts_at is None:
        return None
    if starts_at < start_at and starts_at + timedelta(days=1) < end_at:
        starts_at += timedelta(days=1)
    return starts_at


def plan_path(plan_date=None):
    plan_date = plan_date or date.today()
    return os.path.join(PLANS_DIR, f"{plan_date.isoformat()}.md")


def today_note_path(plan_date=None):
    plan_date = plan_date or date.today()
    return os.path.join(NOTES_DIR, f"{plan_date.isoformat()}.md")


def read_today_notes():
    path = today_note_path()
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read().strip()


def ask_text(question, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or default


def ask_time(question, default):
    while True:
        answer = ask_text(question, default)
        try:
            return parse_hhmm(answer)
        except argparse.ArgumentTypeError as error:
            print(error)


def ask_fixed(existing):
    fixed = list(existing)
    print("Fixed appointments? Add one per line, empty line to finish.")
    while True:
        item = input("> ").strip()
        if not item:
            break
        fixed.append(item)
    return fixed


def collect_plan_answers(args):
    start = args.start
    end = args.end
    focus = args.focus
    fixed = list(args.fixed)
    energy = args.energy

    if args.no_questions:
        start = start or parse_hhmm("09:00")
        end = end or parse_hhmm("18:00")
    else:
        print(color_text("Quick planning questions", "cyan"))
        start = start or ask_time("Start time", "09:00")
        end = end or ask_time("End time", "18:00")
        energy = energy or ask_text("Energy level", "normal")
        focus = focus or ask_text("Most important thing today")
        fixed = ask_fixed(fixed)

    return start, end, focus, fixed, energy


def build_prompt(tasks, start, end, focus, fixed, notes, energy):
    task_lines = "\n".join(
        f"- [{task['id']}] {task['description']} ({task['status']})" for task in tasks
    ) or "- No open tasks"
    fixed_lines = "\n".join(f"- {item}" for item in fixed) or "- None"
    notes_text = notes or "None"
    focus_text = focus or "No stated focus"
    energy_text = energy or "normal"

    return textwrap.dedent(
        f"""
        Make a realistic day plan for today.

        Rules:
        - Use the time window {format_window(start, end)}.
        - Keep it practical, not motivational.
        - Include breaks.
        - Prefer finishing fewer important things over listing everything.
        - Return Markdown only.
        - Include sections: Top priority, Schedule, Open tasks used, Notes.

        Focus:
        {focus_text}

        Energy:
        {energy_text}

        Fixed appointments:
        {fixed_lines}

        Open tasks:
        {task_lines}

        Notes:
        {notes_text}
        """
    ).strip()


def run_ai_plan(ai, prompt):
    if ai == "none":
        return None

    if ai == "auto":
        for candidate in ("codex", "gemini"):
            plan = run_ai_plan(candidate, prompt)
            if plan is not None:
                return plan
        return None

    if shutil.which(ai) is None:
        print(f"{ai} was not found, using local planner.")
        return None

    try:
        if ai == "codex":
            cmd = [
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "--color",
                "never",
                "-",
            ]
        elif ai == "gemini":
            cmd = ["gemini", "--prompt", "Follow the planning instructions from stdin."]
        else:
            return None

        result = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        print(f"{ai} planner timed out after 90 seconds, using local planner.")
        return None
    except OSError as error:
        print(f"{ai} planner could not start: {error}")
        return None

    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        print(f"{ai} planner failed, using local planner.")
        if result.stderr.strip():
            print(result.stderr.strip().splitlines()[-1])
        return None

    return output


def local_plan(tasks, start, end, focus, fixed, notes, energy):
    cursor, finish = combine_window(start, end)
    blocks = []

    for item in fixed:
        if fixed_start(item) is None:
            blocks.append(("Fixed", item))

    if focus:
        blocks.append(("Focus", focus))

    for task in tasks:
        label = f"[{task['id']}] {task['description']}"
        if task["status"] == "in-progress":
            label += " (continue)"
        blocks.append(("Task", label))

    if not blocks:
        blocks.append(("Review", "Clean up inbox, notes, and next tasks"))

    schedule = []
    fixed_events = sorted(
        [
            (fixed_start_for_window(item, cursor, finish), item)
            for item in fixed
            if fixed_start_for_window(item, cursor, finish) is not None
        ],
        key=lambda event: event[0],
    )
    block_index = 0

    def add_work_until(until):
        nonlocal cursor, block_index
        while cursor < until and block_index < len(blocks):
            kind, description = blocks[block_index]
            duration = timedelta(minutes=75 if kind in ("Focus", "Task") else 45)
            block_end = min(cursor + duration, until)
            schedule.append(f"- {format_time(cursor)}-{format_time(block_end)} {description}")
            cursor = block_end
            block_index += 1

            if cursor + timedelta(minutes=10) < until:
                break_end = cursor + timedelta(minutes=10)
                schedule.append(f"- {format_time(cursor)}-{format_time(break_end)} Break")
                cursor = break_end

    for fixed_time, item in fixed_events:
        if fixed_time >= finish:
            continue
        if fixed_time > cursor:
            add_work_until(fixed_time)
            cursor = fixed_time
        fixed_end = min(fixed_time + timedelta(minutes=45), finish)
        if fixed_end > cursor:
            schedule.append(f"- {format_time(cursor)}-{format_time(fixed_end)} Fixed: {item}")
            cursor = fixed_end

    add_work_until(finish)

    task_lines = "\n".join(
        f"- [{task['id']}] {task['description']} ({task['status']})" for task in tasks
    ) or "- No open tasks"
    fixed_lines = "\n".join(f"- {item}" for item in fixed) or "- None"
    notes_text = notes or "None"
    energy_text = energy or "normal"
    top_priority = focus or (tasks[0]["description"] if tasks else "Plan the next useful action")

    return "\n\n".join(
        [
            f"# Plan for {date.today().isoformat()}",
            f"## Top priority\n{top_priority}",
            f"## Energy\n{energy_text}",
            f"## Fixed appointments\n{fixed_lines}",
            f"## Schedule\n{chr(10).join(schedule)}",
            f"## Open tasks used\n{task_lines}",
            f"## Notes\n{notes_text}",
        ]
    )


def save_plan(content, dry_run=False):
    path = plan_path()
    if dry_run:
        print(content)
        return path

    os.makedirs(PLANS_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(content.rstrip() + "\n")
    print(content)
    print()
    print(color_text(f"saved: {path}", "green"))
    return path


def show_today_plan():
    path = plan_path()
    if not os.path.exists(path):
        print("No plan for today yet. Run: task plan")
        return

    with open(path) as f:
        print(f.read().rstrip())


def add_note(text):
    os.makedirs(NOTES_DIR, exist_ok=True)
    path = today_note_path()
    timestamp = datetime.now().strftime("%H:%M")
    with open(path, "a") as f:
        f.write(f"- {timestamp} {text}\n")
    print(color_text(f"noted: {path}", "green"))


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

list_parser = subparsers.add_parser("list")
list_parser.add_argument("filter", nargs="?", choices=["done", "todo", "in-progress"])

subparsers.add_parser("done")

add_parser = subparsers.add_parser("add")
add_parser.add_argument("description")

update_parser = subparsers.add_parser("update")
update_parser.add_argument("id", type=int)
update_parser.add_argument("description")

delete_parser = subparsers.add_parser("delete")
delete_parser.add_argument("id", type=int)

mip_parser = subparsers.add_parser("mark-in-progress")
mip_parser.add_argument("id", type=int)

done_parser = subparsers.add_parser("mark-done")
done_parser.add_argument("id", type=int)

plan_parser = subparsers.add_parser("plan")
plan_parser.add_argument("--ai", choices=["auto", "none", "codex", "gemini"], default="auto")
plan_parser.add_argument("--start", type=parse_hhmm)
plan_parser.add_argument("--end", type=parse_hhmm)
plan_parser.add_argument("--focus")
plan_parser.add_argument("--energy")
plan_parser.add_argument("--fixed", action="append", default=[])
plan_parser.add_argument("--dry-run", action="store_true")
plan_parser.add_argument("--no-questions", action="store_true")

subparsers.add_parser("today")

note_parser = subparsers.add_parser("note")
note_parser.add_argument("text")

args = parser.parse_args()

if args.command == "add":
    if data == []:
        current_id = 1
    else:
        current_id = max([tasks["id"] for tasks in data]) + 1
    new_data = {
        "id": current_id,
        "description": args.description,
        "status": "todo",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    }
    print("added")
    data.append(new_data)

    save()

elif args.command == "list":
    if args.filter:
        for task in data:
            if task["status"] == args.filter:
                printer(task)
    else:
        for task in data:
            if task["status"] != "done":
                printer(task)

elif args.command == "done":
    for task in data:
        if task["status"] == "done":
            printer(task)

elif args.command == "update":
    wanted_id = args.id
    wanted_text_update = args.description

    match_found = False
    for task in data:
        if task["id"] == wanted_id:
            match_found = True
            print("updated")
            task["description"] = wanted_text_update
            task["updatedAt"] = datetime.now().isoformat(timespec="seconds")
            break
    if match_found is False:
        match_was_not_found()

    save()

elif args.command == "delete":
    match_found = False
    for task in data:
        if task["id"] == args.id:
            match_found = True
            index_task = data.index(task)
            data.pop(index_task)
            print("deleted")
            break
    if match_found is False:
        match_was_not_found()

    save()

elif args.command == "mark-in-progress":
    mark_as("in-progress", args.id)

elif args.command == "mark-done":
    mark_as("done", args.id)

elif args.command == "plan":
    tasks = open_tasks()
    notes = read_today_notes()
    start, end, focus, fixed, energy = collect_plan_answers(args)
    prompt = build_prompt(tasks, start, end, focus, fixed, notes, energy)
    plan = run_ai_plan(args.ai, prompt)
    if plan is None:
        plan = local_plan(tasks, start, end, focus, fixed, notes, energy)
    save_plan(plan, args.dry_run)

elif args.command == "today":
    show_today_plan()

elif args.command == "note":
    add_note(args.text)

else:
    parser.print_help()
