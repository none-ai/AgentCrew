#!/usr/bin/env python3
"""
AgentCrew 任务调度可视化工具
生成任务调度甘特图和统计信息
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = Path("/home/stlin-claw/.openclaw/workspace-taizi/openagent/AgentCrew/data")

def load_tasks():
    """加载任务数据"""
    task_file = DATA_DIR / "tasks.json"
    if task_file.exists():
        with open(task_file) as f:
            return json.load(f)
    return {}

def load_dependencies():
    """加载依赖关系"""
    dep_file = DATA_DIR / "dependencies.json"
    if dep_file.exists():
        with open(dep_file) as f:
            return json.load(f)
    return {}

def build_task_timeline(tasks):
    """构建任务时间线"""
    timeline = []
    
    for task_id, task in tasks.items():
        try:
            start = task.get('started_at') or task.get('created_at')
            end = task.get('completed_at') or task.get('updated_at')
            
            if start and end:
                timeline.append({
                    'id': task_id,
                    'name': task.get('name', task_id),
                    'agent': task.get('agent', 'unknown'),
                    'status': task.get('status', 'unknown'),
                    'start': start,
                    'end': end
                })
        except Exception:
            pass
    
    return sorted(timeline, key=lambda x: x['start'])

def generate_gantt_markdown(timeline, max_items=20):
    """生成Markdown甘特图"""
    lines = ["# AgentCrew 任务调度甘特图\n"]
    lines.append("| 任务 | 智能体 | 状态 | 开始时间 | 结束时间 |")
    lines.append("|------|--------|------|----------|----------|")
    
    for task in timeline[:max_items]:
        status_emoji = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        }.get(task['status'], '❓')
        
        lines.append(f"| {task['name'][:30]} | {task['agent'][:8]} | {status_emoji} | {task['start'][:16]} | {task['end'][:16]} |")
    
    return "\n".join(lines)

def analyze_parallelism(timeline):
    """分析并行度"""
    if not timeline:
        return None
    
    # 按时间窗口统计并行任务数
    time_windows = defaultdict(int)
    
    for task in timeline:
        if task['status'] == 'running':
            start = task['start']
            time_windows[start[:16]] += 1
    
    if not time_windows:
        return {'max_parallel': 0, 'avg_parallel': 0}
    
    max_parallel = max(time_windows.values())
    avg_parallel = sum(time_windows.values()) / len(time_windows)
    
    return {
        'max_parallel': max_parallel,
        'avg_parallel': round(avg_parallel, 2),
        'time_points': len(time_windows)
    }

def generate_schedule_stats(tasks, timeline):
    """生成调度统计"""
    if not tasks:
        return "暂无任务数据"
    
    # 按状态统计
    status_count = defaultdict(int)
    agent_count = defaultdict(int)
    
    for task_id, task in tasks.items():
        status_count[task.get('status', 'unknown')] += 1
        agent_count[task.get('agent', 'unknown')] += 1
    
    lines = ["## 任务统计\n"]
    
    lines.append("### 按状态分类\n")
    for status, count in sorted(status_count.items()):
        pct = count / len(tasks) * 100
        lines.append(f"- {status}: {count} ({pct:.1f}%)")
    
    lines.append("\n### 按智能体分类\n")
    for agent, count in sorted(agent_count.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(tasks) * 100
        lines.append(f"- {agent}: {count} ({pct:.1f}%)")
    
    # 并行度分析
    parallelism = analyze_parallelism(timeline)
    if parallelism:
        lines.append(f"\n### 并行度分析\n")
        lines.append(f"- 最大并行任务数: {parallelism['max_parallel']}")
        lines.append(f"- 平均并行任务数: {parallelism['avg_parallel']}")
    
    return "\n".join(lines)

def main():
    print("📊 AgentCrew 任务调度分析")
    print("=" * 50)
    
    tasks = load_tasks()
    
    if not tasks:
        print("暂无任务数据")
        return
    
    print(f"总任务数: {len(tasks)}")
    
    # 构建时间线
    timeline = build_task_timeline(tasks)
    
    if timeline:
        print(f"有时间线的任务: {len(timeline)}")
        
        # 并行度分析
        parallelism = analyze_parallelism(timeline)
        if parallelism:
            print(f"\n⚡ 并行度分析:")
            print(f"  最大并行: {parallelism['max_parallel']} 个任务")
            print(f"  平均并行: {parallelism['avg_parallel']} 个任务")
    
    # 调度统计
    stats = generate_schedule_stats(tasks, timeline)
    print(stats)
    
    # 生成Markdown报告
    if timeline:
        gantt = generate_gantt_markdown(timeline)
        report = f"{gantt}\n\n{stats}"
        
        output_file = DATA_DIR / "schedule_report.md"
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 报告已生成: {output_file}")

if __name__ == "__main__":
    main()
