from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


@dataclass
class EvalArtifacts:
    command: list[str] = field(default_factory=list)
    exit_code: int | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    result_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterArtifacts:
    command: list[str]
    command_rendered: str
    stdout_path: str
    stderr_path: str
    raw_output_path: str
    trajectory_path: str
    metadata_path: str
    command_path: str
    version: str | None = None
    prompt_transport: str = "argv"
    prompt_path: str | None = None
    exit_code: int | None = None
    timed_out: bool = False
    reached_max_iterations: bool = False
    error: str | None = None
    session_id: str | None = None
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskSummary:
    benchmark: str
    agent: str
    task_id: str
    task_version: str
    server_hostname: str
    workspace_path: str
    instruction_path: str
    command: list[str]
    command_rendered: str
    opencode_bin: str
    opencode_version: str | None
    model: str | None
    agent_mode: str | None
    env_llm_config: str | None
    env_llm_model: str | None
    start_time: str
    end_time: str
    duration_seconds: float
    exit_code: int | None
    timed_out: bool
    stdout_path: str
    stderr_path: str
    raw_output_path: str
    eval_result_path: str | None
    dangerously_skip_permissions: bool
    status: str
    trajectory_path: str | None = None
    eval_stdout_path: str | None = None
    eval_stderr_path: str | None = None
    eval_exit_code: int | None = None
    reached_max_iterations: bool = False
    session_id: str | None = None
    opencode_metadata_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
