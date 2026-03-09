#!/usr/bin/env python3
"""
AgentCrew 任务监控工具
实时监控多智能体任务执行状态
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("/home/stlin-claw/.openclaw/workspace-taizi/openagent/AgentCrew/data")

def load_tasks():
    """加载任务数据"""
    task_file = DATA_DIR / "tasks.json"
    if task_file.exists():
        with open(task_file) as f:
            return json.load(f)
    return {}

def get_task_stats(tasks):
    """获取任务统计"""
    total = len(tasks)
    pending = sum(1 for t in tasks.values() if t.get('status') == 'pending')
    running = sum(1 for t in tasks.values() if t.get('status') == 'running')
    completed = sum(1 for t in tasks.values() if t.get('status') == 'completed')
    failed = sum(1 for t in tasks.values() if t.get('status') == 'failed')
    
    return {
        'total': total,
        'pending': pending,
        'running': running,
        'completed': completed,
        'failed': failed
    }

def get_recent_tasks(tasks, limit=5):
    """获取最近的任务"""
    sorted_tasks = sorted(
        tasks.items(),
        key=lambda x: x[1].get('updated_at', ''),
        reverse=True
    )
    return sorted_tasks[:limit]

def main():
    tasks = load_tasks()
    
    if not tasks:
        print("暂无任务数据")
        return
    
    stats = get_task_stats(tasks)
    
    print(f"\n📊 AgentCrew 任务统计")
    print(f"  📋 总任务数: {stats['total']}")
    print(f"  ⏳ 待处理: {stats['pending']}")
    print(f"  🔄 进行中: {stats['running']}")
    print(f"  ✅ 已完成: {stats['completed']}")
    print(f"  ❌ 失败: {stats['failed']}")
    
    # 显示最近任务
    print(f"\n📝 最近任务:")
    recent = get_recent_tasks(tasks)
    for task_id, task in recent:
        status = task.get('status', 'unknown')
        status_emoji = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        }.get(status, '❓')
        
        name = task.get('name', task_id)
        print(f"  {status_emoji} {name} ({status})")

if __name__ == "__main__":
    main()
