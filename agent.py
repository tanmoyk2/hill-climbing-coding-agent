"""Minimalistic coding agent with tools for reading and writing local files."""

import os
import subprocess
import sys
import warnings

from google.adk.agents import Agent
from google.genai import types

# The default model, shared with eval.py so there is a single source of truth.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

# Silencing an ADK warning to declutter terminal output
warnings.filterwarnings("ignore", message=r".*JSON_SCHEMA_FOR_FUNC_DECL.*", category=UserWarning)

def _resolve(sandbox: str, path: str) -> str:
    """Turn a sandbox-relative path into an absolute one, refusing to escape the sandbox."""
    sandbox = os.path.realpath(sandbox)
    full = os.path.realpath(os.path.join(sandbox, path))
    # Allow only the sandbox root itself or a path beneath it (blocks "../" escapes).
    if full != sandbox and not full.startswith(sandbox + os.sep):
        raise ValueError(f"path escapes sandbox: {path!r}")
    return full


# The two helpers below return errors as plain strings instead of raising, so the
# model sees what went wrong and can recover on its next turn.

def _read(sandbox: str, path: str) -> str:
    try:
        with open(_resolve(sandbox, path), encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return f"Error: no such file: {path}"
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"


def _write(sandbox: str, path: str, contents: str) -> str:
    try:
        full = _resolve(sandbox, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(contents)
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"
    return f"Wrote {len(contents)} chars to {path}"


def _list_files(sandbox: str, path: str = ".") -> str:
    try:
        root = _resolve(sandbox, path)
        if not os.path.exists(root):
            return f"Error: no such path: {path}"
        if os.path.isfile(root):
            return os.path.relpath(root, os.path.realpath(sandbox))
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
            for fname in filenames:
                if not fname.endswith(".pyc"):
                    full = os.path.join(dirpath, fname)
                    files.append(os.path.relpath(full, os.path.realpath(sandbox)))
        files.sort()
        return "\n".join(files) if files else "(empty directory)"
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"


def _run_command(sandbox: str, command: str) -> str:
    try:
        real_sandbox = os.path.realpath(sandbox)
        env = os.environ.copy()
        venv_bin = os.path.dirname(sys.executable)
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        src_dir = os.path.join(real_sandbox, "src")
        existing_py = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{real_sandbox}:{src_dir}" + (f":{existing_py}" if existing_py else "")
        proc = subprocess.run(
            command,
            shell=True,
            cwd=real_sandbox,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        return (
            f"exit_code: {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 15 seconds"
    except OSError as exc:
        return f"Error: {exc}"


SYSTEM_INSTRUCTION = """You are an expert Python coding agent. Follow this workflow on every task:
1. Explore: Call `list_files` first and use `read_file` to inspect ALL files in the project (not just the file mentioned in the prompt). Trace imports and upstream/downstream callers to find the true root cause of any bug.
2. Implement: Always use `write_file` to create or update the required source files (never only print code in your response). Preserve expected return types and interfaces.
3. Verify: Always use `run_command` (e.g. `python3 -c "..."` or running the script) to test your code end-to-end before finishing. Test both the examples from the prompt and edge cases (such as empty inputs, zero items, reversed/descending ranges, negative or offset values, and upstream parsing/loading functions). If anything fails, fix the code and re-run until all checks pass."""


def build_agent(sandbox: str, model: str) -> Agent:
    # Each tool's docstring is the description the model sees, so it states that
    # paths are sandbox-relative. Both return their payload under "result".
    def read_file(path: str) -> dict:
        """Read a text file (path is relative to the project root) and return its contents."""
        return {"result": _read(sandbox, path)}

    def write_file(path: str, contents: str) -> dict:
        """Create or overwrite a text file (path is relative to the project root)."""
        return {"result": _write(sandbox, path, contents)}

    def list_files(path: str = ".") -> dict:
        """List all files under a directory (path is relative to the project root, defaults to '.')."""
        return {"result": _list_files(sandbox, path)}

    def run_command(command: str) -> dict:
        """Execute a shell command in the project root directory (e.g. `python3 -c ...` or `python3 script.py`) and return exit_code, stdout, and stderr."""
        return {"result": _run_command(sandbox, command)}

    return Agent(
        name="coding_agent",
        model=model,
        instruction=SYSTEM_INSTRUCTION,
        tools=[read_file, write_file, list_files, run_command],
        generate_content_config=types.GenerateContentConfig(
            temperature=1.0,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            )
        )
    )

if __name__ == "__main__":
    # Test the agent on a prompt in ./out sandbox.  Usage: python agent.py "your prompt"
    import asyncio
    import subprocess
    import sys
    from google.adk.runners import InMemoryRunner

    # Default to Vertex AI (like eval.py) so `python agent.py` works without a
    # Gemini API key; an existing env value, if set, takes precedence.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-0cc6061bba01")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

    sandbox = os.path.join(os.path.dirname(os.path.realpath(__file__)), "out")
    os.makedirs(os.path.join(sandbox, "src"), exist_ok=True)
    prompt = " ".join(sys.argv[1:]) or "Write a hello world python script"

    async def _run_agent() -> None:
        runner = InMemoryRunner(agent=build_agent(sandbox, DEFAULT_MODEL))
        session = await runner.session_service.create_session(
            app_name=runner.app_name, user_id="me")
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for event in runner.run_async(user_id="me", session_id=session.id, new_message=message):
            for part in (event.content and event.content.parts) or []:
                print(part.text or "", end="", flush=True)
    asyncio.run(_run_agent())
    import glob
    for script in glob.glob(f"{sandbox}/**/*.py", recursive=True):
        print(f"\n=== output of {os.path.relpath(script, sandbox)} ===\n" + subprocess.run([sys.executable, script], cwd=sandbox, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout, end="")
