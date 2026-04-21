"""
Runtime configuration helpers for AgentCrew.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


def _default_home() -> Path:
    home = os.getenv("AGENTCREW_HOME")
    if home:
        return Path(home).expanduser().resolve()
    return (PROJECT_ROOT / ".agentcrew").resolve()


def _default_workspace() -> Path:
    workspace = os.getenv("AGENTCREW_WORKSPACE")
    if workspace:
        return Path(workspace).expanduser().resolve()
    return PROJECT_ROOT


def _default_openclaw_home() -> Path:
    openclaw_home = os.getenv("OPENCLAW_HOME")
    if openclaw_home:
        return Path(openclaw_home).expanduser().resolve()
    return (PROJECT_ROOT / ".openclaw").resolve()


@dataclass(frozen=True)
class RuntimePaths:
    home: Path
    workspace: Path
    openclaw_home: Path
    package_dir: Path
    project_root: Path
    config_dir: Path
    data_dir: Path
    logs_dir: Path
    call_logs_dir: Path
    tmp_dir: Path
    plugin_dir: Path


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runtime_paths(workspace: Optional[str | Path] = None) -> RuntimePaths:
    home = _ensure_directory(_default_home())
    runtime_workspace = Path(workspace).expanduser().resolve() if workspace else _default_workspace()
    openclaw_home = _default_openclaw_home()

    config_dir = _ensure_directory(home / "config")
    data_dir = _ensure_directory(home / "data")
    logs_dir = _ensure_directory(home / "logs")
    call_logs_dir = _ensure_directory(data_dir / "call_logs")
    tmp_dir = Path(tempfile.gettempdir()) / "agentcrew"
    _ensure_directory(tmp_dir)
    plugin_dir = _ensure_directory(PROJECT_ROOT / "openclaw_plugin")

    return RuntimePaths(
        home=home,
        workspace=runtime_workspace,
        openclaw_home=openclaw_home,
        package_dir=PACKAGE_DIR,
        project_root=PROJECT_ROOT,
        config_dir=config_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        call_logs_dir=call_logs_dir,
        tmp_dir=tmp_dir,
        plugin_dir=plugin_dir,
    )


def resolve_workspace_path(value: str | Path, workspace: Optional[str | Path] = None) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (get_runtime_paths(workspace).workspace / path).resolve()


def load_json_config(filename: str, default: Dict[str, Any], workspace: Optional[str | Path] = None) -> Dict[str, Any]:
    runtime = get_runtime_paths(workspace)
    candidates = [
        runtime.config_dir / filename,
        runtime.package_dir / filename,
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            import json

            with path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            merged = {**default, **loaded}
            return merged
        except Exception:
            continue

    return default.copy()
