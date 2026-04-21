"""
Built-in task handlers for standalone AgentCrew execution.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, Iterable, Optional

from .runtime import get_runtime_paths, resolve_workspace_path


def _command_result(command: Any, cwd: Optional[str], timeout: int) -> Dict[str, Any]:
    run_cwd = str(resolve_workspace_path(cwd, None)) if cwd else str(get_runtime_paths().workspace)
    use_shell = isinstance(command, str)
    completed = subprocess.run(
        command,
        cwd=run_cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=use_shell,
    )

    result = {
        "command": command,
        "cwd": run_cwd,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode != 0:
        raise RuntimeError(result["stderr"] or f"Command failed with exit code {completed.returncode}")
    return result


def _maybe_run_command(task) -> Optional[Dict[str, Any]]:
    command = task.metadata.get("command")
    if not command:
        return None
    timeout = int(task.metadata.get("timeout", 300))
    cwd = task.metadata.get("cwd")
    return _command_result(command, cwd, timeout)


def _generic_result(task, category: str, deliverables: Iterable[str]) -> Dict[str, Any]:
    result = _maybe_run_command(task)
    if result is not None:
        return {
            "category": category,
            "mode": "command",
            "summary": f"{task.title} executed via command",
            "deliverables": list(deliverables),
            "command_result": result,
        }

    return {
        "category": category,
        "mode": "built_in",
        "summary": f"{task.title} completed with the built-in {category} handler",
        "description": task.description,
        "deliverables": list(deliverables),
        "assignee": task.assignee,
        "next_steps": [
            "Review the generated output",
            "Attach a project-specific handler for deeper automation",
        ],
    }


def default_handler(task):
    return _generic_result(task, "default", ["task summary", "next-step checklist"])


def design_handler(task):
    return _generic_result(task, "design", ["architecture outline", "component plan"])


def development_handler(task):
    return _generic_result(task, "development", ["implementation summary", "execution artifact"])


def testing_handler(task):
    return _generic_result(task, "testing", ["test checklist", "verification report"])


def documentation_handler(task):
    return _generic_result(task, "documentation", ["documentation outline", "release notes"])


def shell_handler(task):
    result = _maybe_run_command(task)
    if result is None:
        raise RuntimeError("shell tasks require metadata.command")
    return {
        "category": "shell",
        "mode": "command",
        "summary": f"{task.title} executed via shell handler",
        "command_result": result,
    }


def get_builtin_handlers():
    return {
        "default": default_handler,
        "design": design_handler,
        "development": development_handler,
        "testing": testing_handler,
        "documentation": documentation_handler,
        "shell": shell_handler,
        "command": shell_handler,
    }


def register_builtin_handlers(executor) -> None:
    for task_type, handler in get_builtin_handlers().items():
        if task_type not in executor.task_handlers:
            executor.register_handler(task_type, handler)
