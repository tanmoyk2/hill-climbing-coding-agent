"""eval.py

Runs agent.py **once** on each task and grades it with a hidden test the
agent never sees. No config files, no seeds.

The agent itself lives in ``agent.py``; this file is just the harness that
discovers tasks, sandboxes each one, runs the agent, and grades the result.

A task is just a directory under tasks/ containing:
  * prompt.md        — what the agent is asked to do
  * tests/hidden.py  — the grader (passes == exit 0); the agent never sees it
  * src/  (optional) — buggy starter code. If present, the sandbox is seeded with
                       it; if absent, the agent writes the program from scratch
                       into an empty src/.

Usage:
    python eval.py                       # run all tasks (in parallel)
    python eval.py --task invoice_report # run one task
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from typing import NamedTuple

# The Google libraries read these Vertex AI settings from the environment when
# they are imported, so the defaults must be set before the imports just below.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-0cc6061bba01")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.evaluation.eval_case import (  # noqa: E402
    EvalCase, SessionInput, get_all_tool_calls, get_all_tool_responses)
from google.adk.evaluation.eval_set import EvalSet  # noqa: E402
from google.adk.evaluation.evaluation_generator import EvaluationGenerator  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from agent import DEFAULT_MODEL, build_agent  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
TASKS_DIR = os.path.join(HERE, "tasks")
RUNS_DIR = os.path.join(HERE, "runs")  # where per-run trajectory artifacts are saved
USER_ID = "student"  # any fixed id works; the runner just needs a stable user.


# --- logging --------------------------------------------------------------------
# We disable ADK's per-run LLM-call cap (RunConfig(max_llm_calls=0) below). ADK
# logs a one-time heads-up whenever the cap is disabled; silence just that one
# logger so it does not clutter the results table. Every other ADK log still shows.
def silence_no_cap_warning() -> None:
    logging.getLogger("google_adk.google.adk.agents.run_config").setLevel(logging.ERROR)


class TaskResult(NamedTuple):
    passed: bool
    tool_calls: int  # number of file-tool calls the agent made
    seconds: float   # wall-clock time for this task
    run_dir: str     # where this task's trajectory/src/repro artifacts were written
    stop_reason: str # why the agent stopped: completed | error


# --- harness --------------------------------------------------------------------

def discover_tasks(task_id: str) -> list[str]:
    """Return the sorted ids of all tasks, or just ``task_id`` if one was given."""
    ids = sorted(d for d in os.listdir(TASKS_DIR)
                 if os.path.isfile(os.path.join(TASKS_DIR, d, "prompt.md")))
    if task_id:
        return [task_id] if task_id in ids else []
    return ids


def make_sandbox(task_dir: str, sandboxes_dir: str) -> str:
    """Seed a fresh sandbox: copy the task's src/ if it ships one, else start empty."""
    sandbox = tempfile.mkdtemp(prefix="task_", dir=sandboxes_dir)
    src = os.path.join(task_dir, "src")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(sandbox, "src"))
    else:
        os.makedirs(os.path.join(sandbox, "src"))
    return sandbox


def grade(task_dir: str, sandbox: str) -> bool:
    """Install the hidden test into the sandbox and run it; pass == exit 0."""
    # Replace any tests/ the agent may have written, so the grader is always ours.
    dest = os.path.join(sandbox, "tests")
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(os.path.join(task_dir, "tests"), dest)
    try:
        proc = subprocess.run([sys.executable, "tests/hidden.py"], cwd=sandbox,
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return proc.returncode == 0
    except subprocess.SubprocessError:
        return False


# --- trajectory recording -------------------------------------------------------
# We don't invent a format: ADK already models an agent trajectory as eval
# `Invocation`s, and ships a harvester that turns raw session events into them.
# We serialize those to ADK's native `.evalset.json` so a student can read exactly
# what the agent did (and, with the bundled repro.sh, re-grade the code it shipped).

_REPRO_TEMPLATE = """#!/usr/bin/env bash
# Reproduce the hidden-test result for task '{task_id}' against the code agent.py
# shipped (in ./src). Regenerated by eval.py on every run.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
mkdir -p "$work/src" "$work/tests"
cp -r "$here/src/." "$work/src/" 2>/dev/null || true
cp -r "{tests_dir}/." "$work/tests/"
( cd "$work" && {python} tests/hidden.py ); code=$?
echo "hidden.py exit code: $code (0 = PASS)"
rm -rf "$work"
exit $code
"""


def write_trajectory(task_id: str, task_dir: str, sandbox: str, app_name: str,
                     events: list, runs_root: str) -> str:
    """Persist the agent's trajectory + shipped code + a repro script for one task.

    Returns the per-task run directory. Writes four things into it:
      * trajectory.evalset.json — ADK-native trajectory (rich InvocationEvents form),
        loadable by ADK's own eval tooling.
      * tool_uses.json          — flattened {tool_uses, tool_responses} per invocation,
        a skimmable view derived via ADK's get_all_tool_* helpers.
      * src/                    — a copy of the code the agent actually shipped.
      * repro.sh                — re-runs the hidden grader against that src/.
    """
    # Harvest: raw events -> ADK eval Invocations (one per user turn).
    invocations = EvaluationGenerator.convert_events_to_eval_invocations(events)
    eval_set = EvalSet(
        eval_set_id=task_id,
        name=f"{task_id} trajectory",
        description=(f"Actual trajectory the agent took on task "
                     f"'{task_id}'. Harvested from session events; the task is "
                     f"graded out-of-band by tasks/{task_id}/tests/hidden.py."),
        eval_cases=[EvalCase(
            eval_id=task_id,
            conversation=invocations,
            session_input=SessionInput(app_name=app_name, user_id=USER_ID),
        )],
    )

    task_run_dir = os.path.join(runs_root, task_id)
    os.makedirs(task_run_dir, exist_ok=True)

    with open(os.path.join(task_run_dir, "trajectory.evalset.json"), "w",
              encoding="utf-8") as fh:
        fh.write(eval_set.model_dump_json(exclude_none=True, indent=2))

    # Flattened companion: the same calls/responses as a flat, skimmable list.
    flat = [{
        "invocation_id": inv.invocation_id,
        "tool_uses": [tc.model_dump(exclude_none=True)
                      for tc in get_all_tool_calls(inv.intermediate_data)],
        "tool_responses": [tr.model_dump(exclude_none=True)
                           for tr in get_all_tool_responses(inv.intermediate_data)],
    } for inv in invocations]
    with open(os.path.join(task_run_dir, "tool_uses.json"), "w",
              encoding="utf-8") as fh:
        json.dump(flat, fh, indent=2, default=str)

    # Preserve the code the agent shipped (the temp sandbox is wiped after the run).
    dest_src = os.path.join(task_run_dir, "src")
    shutil.rmtree(dest_src, ignore_errors=True)
    src = os.path.join(sandbox, "src")
    if os.path.isdir(src):
        shutil.copytree(src, dest_src)
    else:
        os.makedirs(dest_src, exist_ok=True)

    # One-step reproduction of the grading result against the shipped code.
    repro_path = os.path.join(task_run_dir, "repro.sh")
    with open(repro_path, "w", encoding="utf-8") as fh:
        fh.write(_REPRO_TEMPLATE.format(
            task_id=task_id, tests_dir=os.path.join(task_dir, "tests"),
            python=sys.executable))
    os.chmod(repro_path, 0o755)

    return task_run_dir


async def run_task(task_id: str, model: str, sandboxes_dir: str,
                   runs_root: str) -> TaskResult:
    start = time.perf_counter()
    task_dir = os.path.join(TASKS_DIR, task_id)
    sandbox = make_sandbox(task_dir, sandboxes_dir)
    with open(os.path.join(task_dir, "prompt.md"), encoding="utf-8") as fh:
        prompt = fh.read().strip()

    agent = build_agent(sandbox, model)
    runner = InMemoryRunner(agent=agent)
    session = await runner.session_service.create_session(app_name=runner.app_name, user_id=USER_ID)
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    tool_calls = 0
    stop_reason, detail = "completed", ""
    try:
        # max_llm_calls=0 disables ADK's call cap, so a task runs to completion.
        async for ev in runner.run_async(user_id=USER_ID, session_id=session.id,
                                         new_message=msg, run_config=RunConfig(max_llm_calls=0)):
            tool_calls += len(ev.get_function_calls() or [])
    except Exception as exc:  # a real failure — report it, but still grade what's there
        stop_reason, detail = "error", str(exc)
        print(f"warning: task {task_id!r} errored: {exc}", file=sys.stderr)

    # Harvest the full trajectory from the session (includes the user turn, which
    # the streamed events above do not), then persist it before we grade.
    full_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=USER_ID, session_id=session.id)
    events = list(full_session.events) if full_session and full_session.events else []
    run_dir = write_trajectory(task_id, task_dir, sandbox, runner.app_name, events, runs_root)

    passed = await asyncio.to_thread(grade, task_dir, sandbox)
    seconds = time.perf_counter() - start

    # Capture run metadata next to the trajectory, so why the agent stopped (incl.
    # the silenced call-cap hit) is preserved rather than lost to a dropped log.
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump({"task_id": task_id, "model": model,
                   "passed": passed, "tool_calls": tool_calls,
                   "seconds": round(seconds, 1), "stop_reason": stop_reason,
                   "detail": detail}, fh, indent=2)

    return TaskResult(passed, tool_calls, seconds, run_dir, stop_reason)


def format_row(task: str, result: str, tool_calls, latency) -> str:
    """Format one results line; the header and data rows share these widths."""
    return f"{task:<18}{result:<8}{tool_calls:<12}{latency}"


async def main_async(args) -> None:
    task_ids = discover_tasks(args.task)
    if not task_ids:
        print("No tasks matched.")
        return

    silence_no_cap_warning()
    runs_root = os.path.join(RUNS_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(runs_root, exist_ok=True)
    print(f"Please wait: agent.py is solving {len(task_ids)} tasks in parallel with {args.model}...")
    sandboxes_dir = tempfile.mkdtemp(prefix="eval_base_")
    header = format_row("task_id", "result", "tool_calls", "duration_seconds")
    rule = "-" * len(header)
    print(header)
    print(rule)
    solved = 0
    completed = []
    early_stops = []
    try:
        # Launch every task at once, then print each row in task order as it
        # finishes, so the table streams under the header.
        running = [asyncio.create_task(run_task(tid, args.model, sandboxes_dir, runs_root))
                   for tid in task_ids]
        for tid, task in zip(task_ids, running):
            r = await task
            solved += int(r.passed)
            print(format_row(tid, "PASS" if r.passed else "FAIL", r.tool_calls, f"{r.seconds:.1f}"))
            completed.append((tid, r.run_dir))
            if r.stop_reason != "completed":
                early_stops.append((tid, r.stop_reason, r.run_dir))
    finally:
        shutil.rmtree(sandboxes_dir, ignore_errors=True)
    print(rule)
    print(f"Evaluation completed. Solved {solved} out of {len(task_ids)} tasks.")

    # Upload results to GCS if running in Qwiklabs and we ran all tasks
    if not args.task:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            summary = {
                "solved": solved,
                "total": len(task_ids),
                "timestamp": datetime.now().isoformat()
            }
            summary_path = os.path.join(runs_root, "summary.json")
            try:
                with open(summary_path, "w") as fh:
                    json.dump(summary, fh)
                
                bucket = f"gs://{project_id}-l400-apex"
                print(f"Uploading evaluation summary to {bucket}...")
                res = subprocess.run(
                    ["gcloud", "storage", "cp", summary_path, f"{bucket}/summary.json"],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    print("Summary uploaded successfully.")
                else:
                    print(f"Warning: Failed to upload summary to GCS: {res.stderr}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Error saving/uploading summary: {e}", file=sys.stderr)

    # Surface early stops — e.g. an agent that errored out mid-run.
    # The full detail lives in each task's run.json.
    if early_stops:
        print("\nnote: some tasks stopped early (details in each task's run.json):")
        for tid, reason, run_dir in early_stops:
            print(f"  {tid}: {reason}  →  {os.path.relpath(run_dir, os.getcwd())}/run.json")

    # Point students at the trajectory and shipped code for EVERY task that ran —
    # not just failures or early stops — so any run can be inspected and re-graded.
    if completed:
        print("Trajectories and generated code for all tasks:")
        for tid, run_dir in completed:
            rel = os.path.relpath(run_dir, os.getcwd())
            print(f"  {tid}")
            print(f"    trajectory : {rel}/trajectory.evalset.json")
            print(f"    code: {rel}/src/")


def main() -> None:
    p = argparse.ArgumentParser(description="Basic eval (one pass per task)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--task", default="", help="run a single task id (default: all)")
    asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    main()
