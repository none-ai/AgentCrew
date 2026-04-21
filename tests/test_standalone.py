import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib import request

from AgentCrew.executor import get_executor
from AgentCrew.standalone import StandaloneAgentCrewApp, create_server


def _post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url):
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def test_builtin_shell_handler_executes_command():
    executor = get_executor()
    executor.clear()

    task = executor.create_task(
        title="Run inline Python",
        task_type="shell",
        metadata={"command": [sys.executable, "-c", "print('ok')"]},
    )

    result = executor.execute_task(task.id)

    assert result["status"] == "ok"
    assert result["result"]["command_result"]["stdout"] == "ok"


def test_standalone_service_roundtrip(monkeypatch):
    app = StandaloneAgentCrewApp()
    previous_state = app.state_file.read_text(encoding="utf-8") if app.state_file.exists() else None
    app.executor.clear()
    app.communication.message_bus.messages.clear()
    if app.state_file.exists():
        app.state_file.unlink()

    server = create_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        health = _get_json(f"{base_url}/health")
        assert health["health"] == "ok"

        task = _post_json(
            f"{base_url}/tasks",
            {
                "title": "HTTP shell task",
                "task_type": "shell",
                "command": [sys.executable, "-c", "print('svc-ok')"],
            },
        )
        result = _post_json(f"{base_url}/tasks/{task['id']}/execute", {})
        stored = _get_json(f"{base_url}/tasks/{task['id']}")

        assert result["status"] == "ok"
        assert stored["status"] == "completed"
        assert stored["result"]["command_result"]["stdout"] == "svc-ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if previous_state is None:
            app.state_file.unlink(missing_ok=True)
        else:
            app.state_file.write_text(previous_state, encoding="utf-8")


def test_cli_roundtrip_uses_persisted_state():
    app = StandaloneAgentCrewApp()
    previous_state = app.state_file.read_text(encoding="utf-8") if app.state_file.exists() else None
    app.executor.clear()
    app.communication.message_bus.messages.clear()
    app.save_state()

    try:
        created = subprocess.run(
            [
                sys.executable,
                "-m",
                "AgentCrew",
                "task:create",
                "CLI persisted task",
                "--type",
                "shell",
                "--command",
                '["python","-c","print(456)"]',
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        task = json.loads(created.stdout)

        executed = subprocess.run(
            [sys.executable, "-m", "AgentCrew", "task:execute", task["id"]],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(executed.stdout)

        assert result["status"] == "ok"
        assert result["result"]["command_result"]["stdout"] == "456"
    finally:
        if previous_state is None:
            app.state_file.unlink(missing_ok=True)
        else:
            app.state_file.write_text(previous_state, encoding="utf-8")
