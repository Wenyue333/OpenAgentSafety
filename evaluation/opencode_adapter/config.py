from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
import os
import shlex


def _split_args(value: str | None) -> list[str]:
    if not value:
        return []
    return shlex.split(value)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class OpencodeOptions:
    """CLI/runtime options for invoking OpenCode."""

    bin_path: str = "opencode"
    extra_args: list[str] = field(default_factory=list)
    config_path: str | None = None
    model: str | None = None
    agent: str | None = None
    output_format: str = "json"
    attach_url: str | None = None
    username: str | None = None
    password: str | None = None
    dangerously_skip_permissions: bool = False
    timeout_seconds: int = 1800
    max_iterations: int | None = None
    workdir: str | None = None

    @classmethod
    def from_env(cls) -> "OpencodeOptions":
        return cls(
            bin_path=os.environ.get("OPENCODE_BIN", "opencode"),
            extra_args=_split_args(os.environ.get("OPENCODE_ARGS")),
            config_path=os.environ.get("OPENCODE_CONFIG"),
            model=os.environ.get("OPENCODE_MODEL"),
            agent=os.environ.get("OPENCODE_AGENT"),
            output_format=os.environ.get("OPENCODE_FORMAT", "json"),
            attach_url=os.environ.get("OPENCODE_ATTACH_URL"),
            username=os.environ.get("OPENCODE_SERVER_USERNAME"),
            password=os.environ.get("OPENCODE_SERVER_PASSWORD"),
            dangerously_skip_permissions=_env_flag(
                "OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS", False
            ),
            workdir=os.environ.get("OPENCODE_WORKDIR"),
        )


@dataclass
class RunnerOptions:
    """Top-level runner configuration."""

    repo_root: Path
    tasks_root: Path
    base_image_root: Path
    outputs_path: Path
    server_hostname: str
    version: str
    env_llm_config_name: str | None = None
    env_llm_config_path: Path | None = None
    task_id: str | None = None
    resume: bool = False
    dry_run: bool = False
    keep_runtime: bool = False
    docker_image: str | None = None
    opencode: OpencodeOptions = field(default_factory=OpencodeOptions.from_env)
    env_overrides: Mapping[str, str] = field(default_factory=dict)

    @property
    def resolved_docker_image(self) -> str:
        if self.docker_image:
            return self.docker_image
        return f"ghcr.io/theagentcompany/task-base-image:{self.version}"
