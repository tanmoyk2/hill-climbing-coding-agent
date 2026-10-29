# Minimalistic coding agent and eval

The eval runs the coding agent once on each task and grades it with a hidden
test the agent never sees.

## Layout

| file | purpose |
|---|---|
| `agent.py` | the coding agent with the `build_agent` factory, and a `__main__` smoke test |
| `eval.py` | the harness: discovers tasks, sandboxes each one, runs the agent, and grades it |
| `tasks/` | the tasks (see below) |

The agent and the evaluation are kept in separate files. `eval.py` imports `build_agent` from `agent.py`.

## Try the agent on its own

Run `agent.py` directly to test the agent on your own prompts, without the
evaluation harness. It creates scripts in the `out/` folder, then executes them and prints the output.

```
python agent.py                                  # default: writes a hello world script
python agent.py "Write a script that prints pi"  # your own prompt
```

## What a task is

A directory under `tasks/` with:

| file | purpose |
|---|---|
| `prompt.md` | what the agent is asked to do |
| `tests/hidden.py` | the grader (pass == exit 0); the agent never sees it |
| `src/` *(optional)* | buggy starter code |

There are two kinds of task, distinguished only by whether they ship a `src/`: if
a task has one, the sandbox is seeded with that buggy code (the agent fixes it);
if not, the agent writes the program from scratch. The evaluation harness treats both the
same way.

## Run

Requires Google Cloud ADC with Vertex access (default model `gemini-3.1-flash-lite`).

```
python eval.py                        # run all tasks
python eval.py --task invoice_report  # run one task
python eval.py --model <model>        # use a different model
```

Output is one line per task — `PASS`/`FAIL`, the number of tool calls, and latency —
then a final `solved N/5`. There is no per-task LLM-call cap; each task runs until
the agent finishes. Every run saves a trajectory and the shipped
source for each task, and at the end prints the path to both.

## Debugging failures: trajectories & `run.json`

Every run writes per-task artifacts under `runs/<timestamp>/<task_id>/`. 
This is where to find the root cause of a `FAIL`.

| artifact | what it is |
|---|---|
| `trajectory.evalset.json` | the agent's full trajectory — every model turn, tool call (with args), and tool result. This is ADK's native eval-set schema, so it round-trips through ADK's own tooling; read it to see *what the agent did*. |
| `tool_uses.json` | a flattened, skimmable list of the same tool calls and responses. |
| `src/` | the exact code the agent shipped (the sandbox itself is discarded). |
| `repro.sh` | re-runs the hidden grader against that `src/` in a throwaway copy and prints the failing assertion — i.e. *why* it failed. |
| `run.json` | run metadata: `passed`, `tool_calls`, `seconds`, and `stop_reason`. |

## The 5 tasks

| task | kind | what it asks |
|---|---|---|
| `invoice_report` | fix | Invoice totals come out short ($24.00 vs $25.49); fix the root cause. |
| `reminder_time` | fix | Reminders fire at the wrong UTC hour for events with an offset; fix for any offset. |
| `range_list` | build | Expand a compact range list, e.g. `1-3,5,7-9` → `1 2 3 5 7 8 9`. |
| `interval_set` | build | Interval-set CLI (`merge`/`count`/`length`/`covers`) over decimal coordinates. |
| `expense_report` | build | Expense-report CLI (`total`/`count`/`average`/`categories`/`top`/`category`) with money + exit codes. |