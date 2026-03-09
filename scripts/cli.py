#!/usr/bin/env python3
"""
OpenAgent 命令行管理工具
"""
import sys
import os
import json
import argparse

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import load_teams, DEFAULT_TEAMS
from executor import get_executor, TaskStatus
from scheduler import get_dispatcher
from communication import get_communication, MessageType


def cmd_list_teams(args):
    """列出所有团队"""
    teams = load_teams()
    print("\n📋 可用团队:")
    print("-" * 60)
    
    for team_id, team in teams.items():
        status = team.get_status()
        print(f"\n🏢 {status['name']} ({team_id})")
        print(f"   成员数: {status['member_count']}")
        for member in status['members']:
            print(f"   - {member['role_title']}: {member['name']}")


def cmd_team_status(args):
    """查看团队状态"""
    teams = load_teams()
    team = teams.get(args.team)
    
    if not team:
        print(f"❌ 团队 {args.team} 不存在")
        return
    
    status = team.get_status()
    print(f"\n🏢 {status['name']} 状态")
    print("=" * 60)
    print(f"团队ID: {status['team_id']}")
    print(f"成员数: {status['member_count']}")
    
    for member in status['members']:
        print(f"\n  {member['role_title']}: {member['name']}")
        print(f"    活跃任务: {member['active_tasks']}")
        print(f"    已完成任务: {member['completed_tasks']}")


def cmd_create_task(args):
    """创建任务"""
    executor = get_executor()
    task = executor.create_task(
        title=args.title,
        description=args.description or "",
        task_type=args.type or "default"
    )
    
    if args.assign:
        executor.assign_task(task.id, args.assign)
    
    print(f"\n✅ 任务创建成功!")
    print(f"   任务ID: {task.id}")
    print(f"   标题: {task.title}")
    if args.assign:
        print(f"   分配给: {args.assign}")


def cmd_list_tasks(args):
    """列出任务"""
    executor = get_executor()
    all_tasks = executor.get_all_tasks()
    
    if not all_tasks:
        print("\n📭 暂无任务")
        return
    
    print(f"\n📋 任务列表 (共 {len(all_tasks)} 个)")
    print("=" * 60)
    
    for task in all_tasks:
        status_icon = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(task["status"], "❓")
        
        print(f"\n{status_icon} {task['title']}")
        print(f"   ID: {task['id']}")
        print(f"   状态: {task['status']}")
        if task.get("assignee"):
            print(f"   执行人: {task['assignee']}")


def cmd_task_stats(args):
    """任务统计"""
    executor = get_executor()
    stats = executor.get_statistics()
    
    print("\n📊 任务统计")
    print("=" * 60)
    print(f"总任务数: {stats['total']}")
    print(f"待处理: {stats['pending']}")
    print(f"进行中: {stats['in_progress']}")
    print(f"已完成: {stats['completed']}")
    print(f"失败: {stats['failed']}")


def cmd_dispatcher_status(args):
    """调度器状态"""
    dispatcher = get_dispatcher()
    status = dispatcher.get_all_status()
    
    print("\n🔄 调度器状态")
    print("=" * 60)
    
    for name, s in status.items():
        print(f"\n📦 {name}:")
        print(f"   运行中: {s['running']}")
        print(f"   最大工作线程: {s['max_workers']}")
        print(f"   活跃线程: {s['active_workers']}")
        print(f"   队列任务: {s['queued_tasks']}")


def cmd_send_message(args):
    """发送消息"""
    comm = get_communication()
    msg_type = MessageType(args.type) if args.type else MessageType.CHAT
    
    msg_id = comm.send_message(
        sender=args.sender,
        receiver=args.receiver,
        content=args.content,
        msg_type=msg_type
    )
    
    print(f"\n✅ 消息发送成功!")
    print(f"   消息ID: {msg_id}")
    print(f"   发送者: {args.sender}")
    print(f"   接收者: {args.receiver}")


def cmd_check_inbox(args):
    """查看收件箱"""
    comm = get_communication()
    messages = comm.get_inbox(args.agent, unread_only=args.unread)
    
    if not messages:
        print(f"\n📭 {args.agent} 的收件箱为空")
        return
    
    print(f"\n📬 {args.agent} 的收件箱 (共 {len(messages)} 条)")
    print("=" * 60)
    
    for msg in messages:
        read_icon = "✓" if msg.read else "✗"
        print(f"\n{read_icon} [{msg.type.value}] {msg.timestamp}")
        print(f"   发件人: {msg.sender}")
        print(f"   内容: {msg.content}")


def main():
    parser = argparse.ArgumentParser(description="OpenAgent 命令行管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 团队命令
    parser_list = subparsers.add_parser("list", help="列出所有团队")
    parser_list.set_defaults(func=cmd_list_teams)
    
    parser_status = subparsers.add_parser("status", help="查看团队状态")
    parser_status.add_argument("--team", default="openagent_dev", help="团队ID")
    parser_status.set_defaults(func=cmd_team_status)
    
    # 任务命令
    parser_task = subparsers.add_parser("task:create", help="创建任务")
    parser_task.add_argument("title", help="任务标题")
    parser_task.add_argument("--description", "-d", help="任务描述")
    parser_task.add_argument("--type", "-t", default="default", help="任务类型")
    parser_task.add_argument("--assign", "-a", help="分配给")
    parser_task.set_defaults(func=cmd_create_task)
    
    parser_tasks = subparsers.add_parser("task:list", help="列出任务")
    parser_tasks.set_defaults(func=cmd_list_tasks)
    
    parser_stats = subparsers.add_parser("task:stats", help="任务统计")
    parser_stats.set_defaults(func=cmd_task_stats)
    
    # 调度器命令
    parser_disp = subparsers.add_parser("dispatcher:status", help="调度器状态")
    parser_disp.set_defaults(func=cmd_dispatcher_status)
    
    # 消息命令
    parser_msg = subparsers.add_parser("msg:send", help="发送消息")
    parser_msg.add_argument("--sender", "-s", required=True, help="发送者")
    parser_msg.add_argument("--receiver", "-r", required=True, help="接收者")
    parser_msg.add_argument("--content", "-c", required=True, help="消息内容")
    parser_msg.add_argument("--type", "-t", default="chat", help="消息类型")
    parser_msg.set_defaults(func=cmd_send_message)
    
    parser_inbox = subparsers.add_parser("msg:inbox", help="查看收件箱")
    parser_inbox.add_argument("agent", help="代理ID")
    parser_inbox.add_argument("--unread", "-u", action="store_true", help="只显示未读")
    parser_inbox.set_defaults(func=cmd_check_inbox)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
