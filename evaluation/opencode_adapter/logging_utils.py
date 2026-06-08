from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Any
import json
import shlex

SENSITIVE_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def render_command(command: Iterable[str]) -> str:
    return shlex.join(list(command))


def sanitize_env(env: Mapping[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in env.items():
        if any(token in key.upper() for token in SENSITIVE_TOKENS):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


def summarize_text(text: str, max_lines: int = 80) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    kept = lines[:max_lines]
    kept.append(f"... truncated {len(lines) - max_lines} additional lines ...")
    return "\n".join(kept)

