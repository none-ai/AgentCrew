"""
Command line interface for AgentCrew.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from . import get_communication, get_dispatcher, get_executor, load_teams
from .communication import MessageType


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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
    executor = get_executor()
    task = executor.create_task(
        title=args.title,
        description=args.description or "",
        task_type=args.type or "default",
    )
    if args.assign:
        executor.assign_task(task.id, args.assign)
    _print_json(task.to_dict())


def cmd_list_tasks(args):
    executor = get_executor()
    _print_json({"tasks": executor.get_all_tasks()})


def cmd_task_stats(args):
    executor = get_executor()
    _print_json(executor.get_statistics())


def cmd_execute_task(args):
    executor = get_executor()
    _print_json(executor.execute_task(args.task_id))


def cmd_dispatcher_status(args):
    dispatcher = get_dispatcher()
    _print_json(dispatcher.get_all_status())


def cmd_send_message(args):
    comm = get_communication()
    msg_type = MessageType(args.type) if args.type else MessageType.CHAT
    msg_id = comm.send_message(
        sender=args.sender,
        receiver=args.receiver,
        content=args.content,
        msg_type=msg_type,
    )
    _print_json({"message_id": msg_id})


def cmd_check_inbox(args):
    comm = get_communication()
    _print_json(
        {
            "messages": [
                message.to_dict()
                for message in comm.get_inbox(args.agent, unread_only=args.unread)
            ]
        }
    )


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
