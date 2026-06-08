from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any
import json
import os
import subprocess
import time

from .config import OpencodeOptions
from .logging_utils import render_command, sanitize_env, summarize_text, write_json
from .result_schema import AdapterArtifacts


PROMPT_ARGV_LIMIT = 6000


def _reader_thread(stream, queue: Queue[tuple[str, str]], tag: str) -> None:
    try:
        for line in iter(stream.readline, ""):
            queue.put((tag, line))
    finally:
        stream.close()


def _safe_run(command: list[str], cwd: Path | None = None) -> tuple[int | None, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return None, "command not found"
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)

    output = completed.stdout.strip() or completed.stderr.strip()
    return completed.returncode, summarize_text(output)


def probe_opencode(bin_path: str, cwd: Path | None = None) -> dict[str, Any]:
    version_code, version_output = _safe_run([bin_path, "--version"], cwd=cwd)
    help_code, help_output = _safe_run([bin_path, "--help"], cwd=cwd)
    run_help_code, run_help_output = _safe_run([bin_path, "run", "--help"], cwd=cwd)
    serve_help_code, serve_help_output = _safe_run([bin_path, "serve", "--help"], cwd=cwd)
    session_help_code, session_help_output = _safe_run([bin_path, "session", "--help"], cwd=cwd)
    export_help_code, export_help_output = _safe_run([bin_path, "export", "--help"], cwd=cwd)

    return {
        "bin_path": bin_path,
        "version_exit_code": version_code,
        "version": version_output,
        "help_exit_code": help_code,
        "help_summary": help_output,
        "run_help_exit_code": run_help_code,
        "run_help_summary": run_help_output,
        "serve_help_exit_code": serve_help_code,
        "serve_help_summary": serve_help_output,
        "session_help_exit_code": session_help_code,
        "session_help_summary": session_help_output,
        "export_help_exit_code": export_help_code,
        "export_help_summary": export_help_output,
    }


def build_command(options: OpencodeOptions, prompt: str, cwd: Path) -> tuple[list[str], str, str | None]:
    command = [options.bin_path, "run"]
    if options.model:
        command.extend(["--model", options.model])
    if options.agent:
        command.extend(["--agent", options.agent])
    if options.output_format:
        command.extend(["--format", options.output_format])
    if options.attach_url:
        command.extend(["--attach", options.attach_url])
    if options.username:
        command.extend(["--username", options.username])
    if options.password:
        command.extend(["--password", options.password])
    if options.dangerously_skip_permissions:
        command.append("--dangerously-skip-permissions")

    dir_arg = options.workdir or str(cwd)
    command.extend(["--dir", dir_arg])
    command.extend(options.extra_args)

    prompt_transport = "argv"
    prompt_file: str | None = None
    if len(prompt) <= PROMPT_ARGV_LIMIT:
        command.append(prompt)
    else:
        prompt_transport = "stdin"
    return command, prompt_transport, prompt_file


def convert_jsonl_to_trajectory(raw_path: Path, trajectory_path: Path) -> tuple[int, str | None]:
    events: list[dict[str, Any]] = []
    mapped: list[dict[str, Any]] = []
    session_id: str | None = None
    step_count = 0

    if not raw_path.exists():
        trajectory_path.write_text("[]", encoding="utf-8")
        return 0, None

    for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            mapped.append(
                {
                    "source": "environment",
                    "observation": "raw_output",
                    "message": line,
                }
            )
            continue

        events.append(event)
        session_id = session_id or event.get("sessionID")
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp")

        if event_type == "step_start":
            step_count += 1
            mapped.append(
                {
                    "source": "environment",
                    "action": "step_start",
                    "message": json.dumps(event.get("part", {}), ensure_ascii=True),
                    "timestamp": timestamp,
                }
            )
            continue

        if event_type == "step_finish":
            mapped.append(
                {
                    "source": "environment",
                    "action": "step_finish",
                    "message": json.dumps(event.get("part", {}), ensure_ascii=True),
                    "timestamp": timestamp,
                }
            )
            continue

        if event_type == "text":
            part = event.get("part", {})
            mapped.append(
                {
                    "source": "agent",
                    "message": part.get("text", ""),
                    "timestamp": timestamp,
                }
            )
            continue

        if event_type == "reasoning":
            part = event.get("part", {})
            mapped.append(
                {
                    "source": "agent",
                    "observation": "reasoning",
                    "message": part.get("text", ""),
                    "timestamp": timestamp,
                }
            )
            continue

        if event_type == "tool_use":
            part = event.get("part", {})
            mapped.append(
                {
                    "source": "agent",
                    "action": part.get("tool", "tool"),
                    "observation": part.get("state", {}).get("status", "unknown"),
                    "message": json.dumps(part, ensure_ascii=True),
                    "timestamp": timestamp,
                }
            )
            continue

        if event_type == "error":
            mapped.append(
                {
                    "source": "environment",
                    "observation": "error",
                    "message": json.dumps(event.get("error", {}), ensure_ascii=True),
                    "timestamp": timestamp,
                }
            )
            continue

        mapped.append(
            {
                "source": "environment",
                "observation": event_type,
                "message": json.dumps(event, ensure_ascii=True),
                "timestamp": timestamp,
            }
        )

    trajectory_path.write_text(
        json.dumps(mapped, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return step_count, session_id


def run_opencode(
    *,
    options: OpencodeOptions,
    prompt: str,
    working_directory: Path,
    task_output_dir: Path,
    inherited_env: dict[str, str],
) -> AdapterArtifacts:
    stdout_path = task_output_dir / "opencode_stdout.log"
    stderr_path = task_output_dir / "opencode_stderr.log"
    raw_output_path = task_output_dir / (
        "opencode_raw_output.jsonl" if options.output_format == "json" else "opencode_raw_output.txt"
    )
    trajectory_path = task_output_dir / "opencode_trajectory.json"
    metadata_path = task_output_dir / "opencode_metadata.json"
    command_path = task_output_dir / "opencode_command.json"

    command, prompt_transport, prompt_file = build_command(options, prompt, working_directory)
    write_json(
        command_path,
        {
            "command": command,
            "command_rendered": render_command(command),
            "prompt_transport": prompt_transport,
            "prompt_length": len(prompt),
        },
    )

    probe = probe_opencode(options.bin_path, cwd=working_directory)
    metadata = {
        "probe": probe,
        "environment": sanitize_env(inherited_env),
        "working_directory": str(working_directory),
    }
    write_json(metadata_path, metadata)

    if probe["version_exit_code"] is None:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(probe["version"], encoding="utf-8")
        raw_output_path.write_text("", encoding="utf-8")
        trajectory_path.write_text("[]", encoding="utf-8")
        return AdapterArtifacts(
            command=command,
            command_rendered=render_command(command),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            raw_output_path=str(raw_output_path),
            trajectory_path=str(trajectory_path),
            metadata_path=str(metadata_path),
            command_path=str(command_path),
            version=None,
            prompt_transport=prompt_transport,
            prompt_path=prompt_file,
            exit_code=None,
            timed_out=False,
            reached_max_iterations=False,
            error=probe["version"],
            session_id=None,
            step_count=0,
        )

    env = os.environ.copy()
    env.update(inherited_env)
    if options.config_path:
        env["OPENCODE_CONFIG"] = options.config_path
    if options.dangerously_skip_permissions:
        env["OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS"] = "true"

    process = subprocess.Popen(
        command,
        cwd=str(working_directory),
        env=env,
        stdin=subprocess.PIPE if prompt_transport == "stdin" else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if prompt_transport == "stdin" and process.stdin is not None:
        process.stdin.write(prompt)
        process.stdin.close()

    queue: Queue[tuple[str, str]] = Queue()
    threads = [
        Thread(target=_reader_thread, args=(process.stdout, queue, "stdout"), daemon=True),
        Thread(target=_reader_thread, args=(process.stderr, queue, "stderr"), daemon=True),
    ]
    for thread in threads:
        thread.start()

    start = time.monotonic()
    timed_out = False
    reached_max_iterations = False
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    raw_lines: list[str] = []
    step_count = 0

    while True:
        if process.poll() is not None and queue.empty():
            break

        if time.monotonic() - start > options.timeout_seconds:
            timed_out = True
            process.kill()
            break

        try:
            tag, line = queue.get(timeout=0.1)
        except Empty:
            continue

        if tag == "stdout":
            stdout_lines.append(line)
            raw_lines.append(line)
            if options.output_format == "json":
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    event = None
                if event and event.get("type") == "step_start":
                    step_count += 1
                    if options.max_iterations and step_count >= options.max_iterations:
                        reached_max_iterations = True
                        process.kill()
                        break
        else:
            stderr_lines.append(line)

    for thread in threads:
        thread.join(timeout=1)

    exit_code = process.wait(timeout=5)
    stdout_path.write_text("".join(stdout_lines), encoding="utf-8")
    stderr_path.write_text("".join(stderr_lines), encoding="utf-8")
    raw_output_path.write_text("".join(raw_lines), encoding="utf-8")
    mapped_steps, session_id = convert_jsonl_to_trajectory(raw_output_path, trajectory_path)

    return AdapterArtifacts(
        command=command,
        command_rendered=render_command(command),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        raw_output_path=str(raw_output_path),
        trajectory_path=str(trajectory_path),
        metadata_path=str(metadata_path),
        command_path=str(command_path),
        version=probe["version"],
        prompt_transport=prompt_transport,
        prompt_path=prompt_file,
        exit_code=exit_code,
        timed_out=timed_out,
        reached_max_iterations=reached_max_iterations,
        error=None,
        session_id=session_id,
        step_count=max(step_count, mapped_steps),
    )
