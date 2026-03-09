#!/usr/bin/env python3
"""
AgentCrew 性能分析工具
分析多智能体系统性能指标
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import statistics

DATA_DIR = Path("/home/stlin-claw/.openclaw/workspace-taizi/openagent/AgentCrew/data")

def load_tasks():
    """加载任务数据"""
    task_file = DATA_DIR / "tasks.json"
    if task_file.exists():
        with open(task_file) as f:
            return json.load(f)
    return {}

def load_connections():
    """加载连接数据"""
    conn_file = DATA_DIR / "connections.json"
    if conn_file.exists():
        with open(conn_file) as f:
            return json.load(f)
    return {}

def calculate_task_duration(task):
    """计算任务执行时长"""
    if 'started_at' in task and 'completed_at' in task:
        try:
            start = datetime.fromisoformat(task['started_at'])
            end = datetime.fromisoformat(task['completed_at'])
            return (end - start).total_seconds()
        except:
            return 0
    return 0

def analyze_task_performance(tasks):
    """分析任务性能"""
    durations = []
    completed_tasks = [t for t in tasks.values() if t.get('status') == 'completed']
    
    for task in completed_tasks:
        duration = calculate_task_duration(task)
        if duration > 0:
            durations.append(duration)
    
    if not durations:
        return None
    
    return {
        'count': len(durations),
        'avg': statistics.mean(durations),
        'median': statistics.median(durations),
        'min': min(durations),
        'max': max(durations),
        'stdev': statistics.stdev(durations) if len(durations) > 1 else 0
    }

def analyze_connection_pool(connections):
    """分析连接池使用情况"""
    if not connections:
        return None
    
    total = len(connections)
    active = sum(1 for c in connections.values() if c.get('status') == 'active')
    idle = sum(1 for c in connections.values() if c.get('status') == 'idle')
    error = sum(1 for c in connections.values() if c.get('status') == 'error')
    
    # 计算响应时间
    response_times = []
    for c in connections.values():
        if 'response_time' in c:
            response_times.append(c['response_time'])
    
    return {
        'total': total,
        'active': active,
        'idle': idle,
        'error': error,
        'avg_response_time': statistics.mean(response_times) if response_times else 0,
    }

def analyze_agent_performance(tasks):
    """分析各智能体性能"""
    agent_stats = {}
    
    for task in tasks.values():
        agent = task.get('agent', 'unknown')
        if agent not in agent_stats:
            agent_stats[agent] = {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'total_duration': 0
            }
        
        agent_stats[agent]['total'] += 1
        if task.get('status') == 'completed':
            agent_stats[agent]['completed'] += 1
            duration = calculate_task_duration(task)
            agent_stats[agent]['total_duration'] += duration
        elif task.get('status') == 'failed':
            agent_stats[agent]['failed'] += 1
    
    # 计算平均执行时间
    for agent in agent_stats:
        if agent_stats[agent]['completed'] > 0:
            agent_stats[agent]['avg_duration'] = (
                agent_stats[agent]['total_duration'] / 
                agent_stats[agent]['completed']
            )
        else:
            agent_stats[agent]['avg_duration'] = 0
    
    return agent_stats

def main():
    print("🔍 AgentCrew 性能分析")
    print("=" * 50)
    
    # 任务性能分析
    tasks = load_tasks()
    if tasks:
        perf = analyze_task_performance(tasks)
        if perf:
            print(f"\n📊 任务执行性能:")
            print(f"  完成任务数: {perf['count']}")
            print(f"  平均执行时间: {perf['avg']:.2f}秒")
            print(f"  中位数执行时间: {perf['median']:.2f}秒")
            print(f"  最短执行时间: {perf['min']:.2f}秒")
            print(f"  最长执行时间: {perf['max']:.2f}秒")
            print(f"  标准差: {perf['stdev']:.2f}秒")
        
        # 智能体性能分析
        agent_perf = analyze_agent_performance(tasks)
        if agent_perf:
            print(f"\n🤖 智能体性能:")
            for agent, stats in sorted(agent_perf.items(), 
                                         key=lambda x: x[1]['completed'], 
                                         reverse=True):
                success_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                print(f"  {agent}:")
                print(f"    总任务: {stats['total']} | 完成: {stats['completed']} | 失败: {stats['failed']}")
                print(f"    成功率: {success_rate:.1f}% | 平均耗时: {stats['avg_duration']:.2f}秒")
    
    # 连接池分析
    connections = load_connections()
    if connections:
        conn_perf = analyze_connection_pool(connections)
        if conn_perf:
            print(f"\n🌐 连接池状态:")
            print(f"  总连接数: {conn_perf['total']}")
            print(f"  活跃: {conn_perf['active']} | 空闲: {conn_perf['idle']} | 错误: {conn_perf['error']}")
            print(f"  平均响应时间: {conn_perf['avg_response_time']*1000:.2f}ms")
    
    if not tasks and not connections:
        print("\n暂无性能数据")

if __name__ == "__main__":
    main()
