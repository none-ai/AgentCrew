"""
Standalone HTTP service for AgentCrew.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .agents import load_teams, save_teams
from .communication import Message, MessageType, get_communication
from .extensions import ExtensionManager
from .executor import Task, get_executor
from .memory import get_memory_manager
from .runtime import get_runtime_paths


class StandaloneAgentCrewApp:
    def __init__(self):
        self.runtime = get_runtime_paths()
        self.state_file = self.runtime.data_dir / "standalone_state.json"
        self.executor = get_executor()
        self.communication = get_communication()
        self.memory = get_memory_manager(str(self.runtime.data_dir))
        self.extensions = ExtensionManager()
        self._load_state()

    def _load_state(self):
        if not self.state_file.exists():
            return

        with self.state_file.open("r", encoding="utf-8") as file:
            state = json.load(file)

        self.executor.load_tasks(state.get("tasks", []))
        self.communication.message_bus.messages = [
            Message.from_dict(item) for item in state.get("messages", [])
        ]

    def save_state(self):
        payload = {
            "tasks": self.executor.get_all_tasks(),
            "messages": [message.to_dict() for message in self.communication.message_bus.messages],
        }
        with self.state_file.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def list_teams(self):
        return {
            team_id: team.get_status()
            for team_id, team in load_teams().items()
        }

    def team_matrix(self):
        return {
            team_id: team.get_capability_matrix()
            for team_id, team in load_teams().items()
        }

    def get_agent_bundle(self, team_id: str, agent_name: str):
        teams = load_teams()
        team = teams.get(team_id)
        if not team:
            raise KeyError(team_id)
        agent = team.get_agent(agent_name)
        if not agent:
            raise KeyError(agent_name)
        return self.extensions.build_agent_bundle(agent.profile)

    def list_tasks(self):
        return self.executor.get_all_tasks()

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.executor.get_task(task_id)

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        metadata = payload.get("metadata") or {}
        if payload.get("command"):
            metadata["command"] = payload["command"]
            if payload.get("cwd"):
                metadata["cwd"] = payload["cwd"]
            if payload.get("timeout"):
                metadata["timeout"] = payload["timeout"]

        task = self.executor.create_task(
            title=payload["title"],
            description=payload.get("description", ""),
            task_type=payload.get("task_type", "default"),
            parent_id=payload.get("parent_id"),
            metadata=metadata,
        )
        if payload.get("assignee"):
            self.executor.assign_task(task.id, payload["assignee"])
        self.save_state()
        return task.to_dict()

    def assign_task(self, task_id: str, assignee: str) -> Dict[str, Any]:
        if not self.executor.assign_task(task_id, assignee):
            raise KeyError(task_id)
        self.save_state()
        return self.executor.get_task(task_id).to_dict()

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        result = self.executor.execute_task(task_id)
        self.save_state()
        return result

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        msg_type = MessageType(payload.get("msg_type", "chat"))
        message_id = self.communication.send_message(
            sender=payload["sender"],
            receiver=payload["receiver"],
            content=payload["content"],
            msg_type=msg_type,
            metadata=payload.get("metadata"),
        )
        self.save_state()
        return {"message_id": message_id}

    def get_inbox(self, agent_id: str):
        return [message.to_dict() for message in self.communication.get_inbox(agent_id)]

    def snapshot(self):
        return {
            "health": "ok",
            "runtime": {
                "home": str(self.runtime.home),
                "workspace": str(self.runtime.workspace),
                "data_dir": str(self.runtime.data_dir),
            },
            "stats": self.executor.get_statistics(),
            "memory": self.memory.get_stats(),
            "extensions": self.extensions.stats(),
        }

    def graph_context(self, query: str, depth: int = 1, limit: int = 8):
        return self.memory.graph_context(query, depth=depth, limit=limit)

    def add_graph_entity(self, payload: Dict[str, Any]):
        entity_id = self.memory.add_entity(
            name=payload["name"],
            node_type=payload.get("node_type", "concept"),
            aliases=payload.get("aliases"),
            attributes=payload.get("attributes"),
        )
        return {"entity_id": entity_id}

    def add_graph_relation(self, payload: Dict[str, Any]):
        relation_id = self.memory.link_entities(
            source=payload["source"],
            target=payload["target"],
            relation=payload["relation"],
            weight=payload.get("weight", 1.0),
            metadata=payload.get("metadata"),
        )
        return {"relation_id": relation_id}

    def list_skills(self):
        return self.extensions.skills.list()

    def install_skill(self, payload: Dict[str, Any]):
        if payload.get("file"):
            return self.extensions.skills.install_from_file(payload["file"], overwrite=payload.get("overwrite", True))
        return self.extensions.skills.install(payload, overwrite=payload.get("overwrite", True))

    def attach_skill(self, team_id: str, agent_name: str, skill_name: str):
        self.extensions.skills.get(skill_name)
        teams = load_teams()
        team = teams.get(team_id)
        if not team:
            raise KeyError(team_id)
        result = team.attach_skill(agent_name, skill_name)
        save_teams(teams)
        return result

    def list_mcp_servers(self):
        return self.extensions.mcp.list()

    def install_mcp_server(self, payload: Dict[str, Any]):
        if payload.get("file"):
            return self.extensions.mcp.install_from_file(payload["file"], overwrite=payload.get("overwrite", True))
        return self.extensions.mcp.install(payload, overwrite=payload.get("overwrite", True))

    def attach_mcp_server(self, team_id: str, agent_name: str, server_name: str):
        self.extensions.mcp.get(server_name)
        teams = load_teams()
        team = teams.get(team_id)
        if not team:
            raise KeyError(team_id)
        result = team.attach_mcp_server(agent_name, server_name)
        save_teams(teams)
        return result


class AgentCrewRequestHandler(BaseHTTPRequestHandler):
    app = None

    def _get_app(self) -> StandaloneAgentCrewApp:
        if self.app is None:
            self.__class__.app = StandaloneAgentCrewApp()
        return self.app

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_json(self, status: int, payload: Dict[str, Any]):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        app = self._get_app()

        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, app.snapshot())
            return

        if parsed.path == "/teams":
            self._send_json(HTTPStatus.OK, {"teams": app.list_teams()})
            return

        if parsed.path == "/teams/capabilities":
            self._send_json(HTTPStatus.OK, {"teams": app.team_matrix()})
            return

        if len(parts) == 5 and parts[0] == "teams" and parts[2] == "agents" and parts[4] == "bundle":
            self._send_json(HTTPStatus.OK, app.get_agent_bundle(parts[1], parts[3]))
            return

        if parsed.path == "/tasks":
            self._send_json(HTTPStatus.OK, {"tasks": app.list_tasks()})
            return

        if parsed.path == "/skills":
            self._send_json(HTTPStatus.OK, {"skills": app.list_skills()})
            return

        if parsed.path == "/mcp/servers":
            self._send_json(HTTPStatus.OK, {"servers": app.list_mcp_servers()})
            return

        if parsed.path == "/memory/graph":
            query = parse_qs(parsed.query)
            term = query.get("query", [""])[0]
            depth = int(query.get("depth", ["1"])[0])
            limit = int(query.get("limit", ["8"])[0])
            self._send_json(HTTPStatus.OK, app.graph_context(term, depth=depth, limit=limit))
            return

        if len(parts) == 2 and parts[0] == "tasks":
            task = app.get_task(parts[1])
            if not task:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "task_not_found"})
                return
            self._send_json(HTTPStatus.OK, task.to_dict())
            return

        if parsed.path == "/messages":
            query = parse_qs(parsed.query)
            agent = query.get("agent", [None])[0]
            if not agent:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "agent query parameter is required"})
                return
            self._send_json(HTTPStatus.OK, {"messages": app.get_inbox(agent)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        payload = self._read_json()
        app = self._get_app()

        try:
            if parsed.path == "/tasks":
                task = app.create_task(payload)
                self._send_json(HTTPStatus.CREATED, task)
                return

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "assign":
                result = app.assign_task(parts[1], payload["assignee"])
                self._send_json(HTTPStatus.OK, result)
                return

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "execute":
                result = app.execute_task(parts[1])
                status = HTTPStatus.OK if result.get("status") == "ok" else HTTPStatus.BAD_REQUEST
                self._send_json(status, result)
                return

            if parsed.path == "/messages":
                message = app.send_message(payload)
                self._send_json(HTTPStatus.CREATED, message)
                return

            if parsed.path == "/skills/install":
                skill = app.install_skill(payload)
                self._send_json(HTTPStatus.CREATED, skill)
                return

            if len(parts) == 5 and parts[0] == "teams" and parts[2] == "agents" and parts[4] == "skills":
                result = app.attach_skill(parts[1], parts[3], payload["skill"])
                self._send_json(HTTPStatus.OK, result)
                return

            if parsed.path == "/mcp/install":
                server = app.install_mcp_server(payload)
                self._send_json(HTTPStatus.CREATED, server)
                return

            if len(parts) == 5 and parts[0] == "teams" and parts[2] == "agents" and parts[4] == "mcp":
                result = app.attach_mcp_server(parts[1], parts[3], payload["server"])
                self._send_json(HTTPStatus.OK, result)
                return

            if parsed.path == "/memory/graph/entity":
                entity = app.add_graph_entity(payload)
                self._send_json(HTTPStatus.CREATED, entity)
                return

            if parsed.path == "/memory/graph/relation":
                relation = app.add_graph_relation(payload)
                self._send_json(HTTPStatus.CREATED, relation)
                return
        except KeyError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "detail": str(exc)})
            return
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "detail": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format, *args):
        return


def create_server(host: str = "127.0.0.1", port: int = 8765, app: Optional[StandaloneAgentCrewApp] = None):
    handler = type("ConfiguredAgentCrewRequestHandler", (AgentCrewRequestHandler,), {})
    handler.app = app or StandaloneAgentCrewApp()
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8765):
    server = create_server(host=host, port=port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
