"""
Command line interface for AgentCrew.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from . import get_communication, get_dispatcher, get_executor, load_teams
from .communication import MessageType
from .standalone import StandaloneAgentCrewApp, serve


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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


def cmd_create_task(args):
    metadata = json.loads(args.metadata) if args.metadata else {}
    if args.command:
        metadata["command"] = json.loads(args.command) if args.command.startswith("[") else args.command
    if args.cwd:
        metadata["cwd"] = args.cwd
    if args.timeout:
        metadata["timeout"] = args.timeout

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

    parser_task = subparsers.add_parser("task:create", help="Create task")
    parser_task.add_argument("title", help="Task title")
    parser_task.add_argument("--description", "-d", help="Task description")
    parser_task.add_argument("--type", "-t", default="default", help="Task type")
    parser_task.add_argument("--assign", "-a", help="Assignee")
    parser_task.add_argument("--metadata", help="JSON metadata payload")
    parser_task.add_argument("--command", help="Command string or JSON array for built-in command execution")
    parser_task.add_argument("--cwd", help="Working directory for command execution")
    parser_task.add_argument("--timeout", type=int, help="Command timeout in seconds")
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
