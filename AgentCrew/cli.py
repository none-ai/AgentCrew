"""
Command line interface for AgentCrew.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from . import get_communication, get_dispatcher, get_executor, load_teams
from .agents import save_teams
from .communication import MessageType
from .extensions import ExtensionManager
from .memory import get_memory_manager
from .standalone import StandaloneAgentCrewApp, serve


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _parse_json_or_text(value: str | None) -> Any:
    if not value:
        return None
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("[") or stripped.startswith('"'):
        return json.loads(stripped)
    return stripped


def _get_app() -> StandaloneAgentCrewApp:
    return StandaloneAgentCrewApp()


def cmd_list_teams(args):
    teams = load_teams()
    payload = {
        "teams": {
            team_id: team.get_status()
            for team_id, team in teams.items()
        }
    }
    _print_json(payload if args.json else payload)


def cmd_team_status(args):
    teams = load_teams()
    team = teams.get(args.team)
    if not team:
        raise SystemExit(f"Team {args.team} not found")
    _print_json(team.get_status())


def cmd_team_matrix(args):
    teams = load_teams()
    payload = {
        team_id: team.get_capability_matrix()
        for team_id, team in teams.items()
    }
    _print_json(payload)


def cmd_team_attach_skill(args):
    manager = ExtensionManager()
    manager.skills.get(args.skill)
    teams = load_teams()
    team = teams.get(args.team)
    if not team:
        raise SystemExit(f"Team {args.team} not found")
    payload = team.attach_skill(args.agent, args.skill)
    save_teams(teams)
    _print_json(payload)


def cmd_team_attach_mcp(args):
    manager = ExtensionManager()
    manager.mcp.get(args.server)
    teams = load_teams()
    team = teams.get(args.team)
    if not team:
        raise SystemExit(f"Team {args.team} not found")
    payload = team.attach_mcp_server(args.agent, args.server)
    save_teams(teams)
    _print_json(payload)


def cmd_create_task(args):
    metadata = json.loads(args.metadata) if args.metadata else {}
    if args.command:
        metadata["command"] = json.loads(args.command) if args.command.startswith("[") else args.command
    if args.cwd:
        metadata["cwd"] = args.cwd
    if args.timeout:
        metadata["timeout"] = args.timeout
    if args.domain:
        metadata["domain"] = args.domain
    if args.goal:
        metadata["goal"] = _parse_json_or_text(args.goal)
    if args.workflow:
        metadata["workflow"] = json.loads(args.workflow)

    app = _get_app()
    task = app.create_task(
        {
            "title": args.title,
            "description": args.description or "",
            "task_type": args.type or "default",
            "metadata": metadata,
            "assignee": args.assign,
        }
    )
    _print_json(task)


def cmd_list_tasks(args):
    app = _get_app()
    _print_json({"tasks": app.list_tasks()})


def cmd_task_stats(args):
    app = _get_app()
    _print_json(app.executor.get_statistics())


def cmd_execute_task(args):
    app = _get_app()
    _print_json(app.execute_task(args.task_id))


def cmd_dispatcher_status(args):
    dispatcher = get_dispatcher()
    _print_json(dispatcher.get_all_status())


def cmd_send_message(args):
    app = _get_app()
    _print_json(
        app.send_message(
            {
                "sender": args.sender,
                "receiver": args.receiver,
                "content": args.content,
                "msg_type": args.type or MessageType.CHAT.value,
            }
        )
    )


def cmd_check_inbox(args):
    app = _get_app()
    messages = app.get_inbox(args.agent)
    if args.unread:
        messages = [message for message in messages if not message.get("read")]
    _print_json({"messages": messages})


def cmd_skill_list(args):
    manager = ExtensionManager()
    _print_json({"skills": manager.skills.list()})


def cmd_skill_install(args):
    manager = ExtensionManager()
    if args.file:
        result = manager.skills.install_from_file(args.file, overwrite=not args.no_overwrite)
    else:
        result = manager.skills.install(
            {
                "name": args.name,
                "version": args.version,
                "description": args.description or "",
                "entry_prompt": args.prompt or "",
                "tools": json.loads(args.tools) if args.tools else [],
                "tags": json.loads(args.tags) if args.tags else [],
                "metadata": json.loads(args.metadata) if args.metadata else {},
            },
            overwrite=not args.no_overwrite,
        )
    _print_json(result)


def cmd_mcp_list(args):
    manager = ExtensionManager()
    _print_json({"servers": manager.mcp.list()})


def cmd_mcp_install(args):
    manager = ExtensionManager()
    if args.file:
        result = manager.mcp.install_from_file(args.file, overwrite=not args.no_overwrite)
    else:
        result = manager.mcp.install(
            {
                "name": args.name,
                "version": args.version,
                "description": args.description or "",
                "transport": args.transport,
                "command": args.command or "",
                "args": json.loads(args.args) if args.args else [],
                "env": json.loads(args.env) if args.env else {},
                "cwd": args.cwd,
                "capabilities": json.loads(args.capabilities) if args.capabilities else [],
                "metadata": json.loads(args.metadata) if args.metadata else {},
            },
            overwrite=not args.no_overwrite,
        )
    _print_json(result)


def cmd_graph_query(args):
    memory = get_memory_manager()
    _print_json(memory.graph_context(args.query, depth=args.depth, limit=args.limit))


def cmd_graph_entity(args):
    memory = get_memory_manager()
    _print_json(
        {
            "entity_id": memory.add_entity(
                name=args.name,
                node_type=args.node_type,
                aliases=json.loads(args.aliases) if args.aliases else [],
                attributes=json.loads(args.attributes) if args.attributes else {},
            )
        }
    )


def cmd_graph_relation(args):
    memory = get_memory_manager()
    _print_json(
        {
            "relation_id": memory.link_entities(
                source=args.source,
                target=args.target,
                relation=args.relation,
                weight=args.weight,
                metadata=json.loads(args.metadata) if args.metadata else {},
            )
        }
    )


def cmd_serve(args):
    serve(host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AgentCrew command line interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_list = subparsers.add_parser("list", help="List all teams")
    parser_list.add_argument("--json", action="store_true", default=True)
    parser_list.set_defaults(func=cmd_list_teams)

    parser_status = subparsers.add_parser("status", help="Show team status")
    parser_status.add_argument("--team", default="AgentCrew_dev", help="Team id")
    parser_status.set_defaults(func=cmd_team_status)

    parser_matrix = subparsers.add_parser("team:matrix", help="Show team capability matrix")
    parser_matrix.set_defaults(func=cmd_team_matrix)

    parser_attach_skill = subparsers.add_parser("team:attach-skill", help="Attach an installed skill to an agent")
    parser_attach_skill.add_argument("--team", required=True, help="Team id")
    parser_attach_skill.add_argument("--agent", required=True, help="Agent name")
    parser_attach_skill.add_argument("--skill", required=True, help="Installed skill name")
    parser_attach_skill.set_defaults(func=cmd_team_attach_skill)

    parser_attach_mcp = subparsers.add_parser("team:attach-mcp", help="Attach an installed MCP server to an agent")
    parser_attach_mcp.add_argument("--team", required=True, help="Team id")
    parser_attach_mcp.add_argument("--agent", required=True, help="Agent name")
    parser_attach_mcp.add_argument("--server", required=True, help="Installed MCP server name")
    parser_attach_mcp.set_defaults(func=cmd_team_attach_mcp)

    parser_task = subparsers.add_parser("task:create", help="Create task")
    parser_task.add_argument("title", help="Task title")
    parser_task.add_argument("--description", "-d", help="Task description")
    parser_task.add_argument("--type", "-t", default="default", help="Task type")
    parser_task.add_argument("--assign", "-a", help="Assignee")
    parser_task.add_argument("--metadata", help="JSON metadata payload")
    parser_task.add_argument("--command", help="Command string or JSON array for built-in command execution")
    parser_task.add_argument("--cwd", help="Working directory for command execution")
    parser_task.add_argument("--timeout", type=int, help="Command timeout in seconds")
    parser_task.add_argument("--domain", help="Task domain")
    parser_task.add_argument("--goal", help="Goal text or JSON object")
    parser_task.add_argument("--workflow", help="JSON array of workflow steps")
    parser_task.set_defaults(func=cmd_create_task)

    parser_tasks = subparsers.add_parser("task:list", help="List tasks")
    parser_tasks.set_defaults(func=cmd_list_tasks)

    parser_stats = subparsers.add_parser("task:stats", help="Task statistics")
    parser_stats.set_defaults(func=cmd_task_stats)

    parser_execute = subparsers.add_parser("task:execute", help="Execute a task")
    parser_execute.add_argument("task_id", help="Task id")
    parser_execute.set_defaults(func=cmd_execute_task)

    parser_disp = subparsers.add_parser("dispatcher:status", help="Dispatcher status")
    parser_disp.set_defaults(func=cmd_dispatcher_status)

    parser_msg = subparsers.add_parser("msg:send", help="Send a message")
    parser_msg.add_argument("--sender", "-s", required=True, help="Sender")
    parser_msg.add_argument("--receiver", "-r", required=True, help="Receiver")
    parser_msg.add_argument("--content", "-c", required=True, help="Message content")
    parser_msg.add_argument("--type", "-t", default="chat", help="Message type")
    parser_msg.set_defaults(func=cmd_send_message)

    parser_inbox = subparsers.add_parser("msg:inbox", help="Inspect inbox")
    parser_inbox.add_argument("agent", help="Agent id")
    parser_inbox.add_argument("--unread", "-u", action="store_true", help="Only unread")
    parser_inbox.set_defaults(func=cmd_check_inbox)

    parser_skill_list = subparsers.add_parser("skill:list", help="List installed skills")
    parser_skill_list.set_defaults(func=cmd_skill_list)

    parser_skill_install = subparsers.add_parser("skill:install", help="Install a skill manifest")
    parser_skill_install.add_argument("--file", help="Manifest JSON file")
    parser_skill_install.add_argument("--name", help="Skill name")
    parser_skill_install.add_argument("--version", default="0.1.0", help="Skill version")
    parser_skill_install.add_argument("--description", help="Skill description")
    parser_skill_install.add_argument("--prompt", help="Skill entry prompt")
    parser_skill_install.add_argument("--tools", help="JSON array of tool names")
    parser_skill_install.add_argument("--tags", help="JSON array of tags")
    parser_skill_install.add_argument("--metadata", help="JSON object metadata")
    parser_skill_install.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing skill")
    parser_skill_install.set_defaults(func=cmd_skill_install)

    parser_mcp_list = subparsers.add_parser("mcp:list", help="List installed MCP servers")
    parser_mcp_list.set_defaults(func=cmd_mcp_list)

    parser_mcp_install = subparsers.add_parser("mcp:install", help="Install an MCP server manifest")
    parser_mcp_install.add_argument("--file", help="Manifest JSON file")
    parser_mcp_install.add_argument("--name", help="Server name")
    parser_mcp_install.add_argument("--version", default="0.1.0", help="Server version")
    parser_mcp_install.add_argument("--description", help="Server description")
    parser_mcp_install.add_argument("--transport", default="stdio", help="Transport type")
    parser_mcp_install.add_argument("--command", help="Command executable")
    parser_mcp_install.add_argument("--args", help="JSON array of command args")
    parser_mcp_install.add_argument("--env", help="JSON object of environment vars")
    parser_mcp_install.add_argument("--cwd", help="Working directory")
    parser_mcp_install.add_argument("--capabilities", help="JSON array of capabilities")
    parser_mcp_install.add_argument("--metadata", help="JSON object metadata")
    parser_mcp_install.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing server")
    parser_mcp_install.set_defaults(func=cmd_mcp_install)

    parser_graph_query = subparsers.add_parser("graph:query", help="Query graph memory")
    parser_graph_query.add_argument("query", help="Query string")
    parser_graph_query.add_argument("--depth", type=int, default=1, help="Traversal depth")
    parser_graph_query.add_argument("--limit", type=int, default=8, help="Node limit")
    parser_graph_query.set_defaults(func=cmd_graph_query)

    parser_graph_entity = subparsers.add_parser("graph:add-entity", help="Add a graph entity")
    parser_graph_entity.add_argument("name", help="Entity name")
    parser_graph_entity.add_argument("--node-type", default="concept", help="Entity type")
    parser_graph_entity.add_argument("--aliases", help="JSON array of aliases")
    parser_graph_entity.add_argument("--attributes", help="JSON object of attributes")
    parser_graph_entity.set_defaults(func=cmd_graph_entity)

    parser_graph_relation = subparsers.add_parser("graph:add-relation", help="Add a graph relation")
    parser_graph_relation.add_argument("source", help="Source entity or node id")
    parser_graph_relation.add_argument("target", help="Target entity or node id")
    parser_graph_relation.add_argument("relation", help="Relation name")
    parser_graph_relation.add_argument("--weight", type=float, default=1.0, help="Relation weight")
    parser_graph_relation.add_argument("--metadata", help="JSON object metadata")
    parser_graph_relation.set_defaults(func=cmd_graph_relation)

    parser_serve = subparsers.add_parser("serve", help="Run the standalone HTTP service")
    parser_serve.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser_serve.add_argument("--port", type=int, default=8765, help="Bind port")
    parser_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
