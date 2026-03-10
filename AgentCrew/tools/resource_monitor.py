#!/usr/bin/env python3
"""
AgentCrew 资源监控工具
实时监控系统资源使用情况
"""
import json
import os
import psutil
import time
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("/home/stlin-claw/.openclaw/workspace-taizi/openagent/AgentCrew/data")

def get_cpu_usage():
    """获取CPU使用率"""
    return psutil.cpu_percent(interval=1, percpu=False)

def get_cpu_per_core():
    """获取每个核心的CPU使用率"""
    return psutil.cpu_percent(interval=1, percpu=True)

def get_memory_usage():
    """获取内存使用情况"""
    mem = psutil.virtual_memory()
    return {
        'total': mem.total / (1024**3),  # GB
        'available': mem.available / (1024**3),
        'used': mem.used / (1024**3),
        'percent': mem.percent
    }

def get_disk_usage(path='/'):
    """获取磁盘使用情况"""
    disk = psutil.disk_usage(path)
    return {
        'total': disk.total / (1024**3),
        'used': disk.used / (1024**3),
        'free': disk.free / (1024**3),
        'percent': disk.percent
    }

def get_network_io():
    """获取网络IO"""
    net = psutil.net_io_counters()
    return {
        'bytes_sent': net.bytes_sent,
        'bytes_recv': net.bytes_recv,
        'packets_sent': net.packets_sent,
        'packets_recv': net.packets_recv
    }

def get_process_info():
    """获取当前进程信息"""
    process = psutil.Process()
    with process.oneshot():
        return {
            'pid': process.pid,
            'name': process.name(),
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'memory_info': process.memory_info().rss / (1024**2),  # MB
            'num_threads': process.num_threads(),
            'status': process.status()
        }

def get_top_processes(limit=5):
    """获取CPU/内存占用最高的进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu': proc.info['cpu_percent'] or 0,
                'memory': proc.info['memory_percent'] or 0
            })
        except:
            pass
    
    # 按CPU排序
    top_cpu = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:limit]
    # 按内存排序
    top_mem = sorted(processes, key=lambda x: x['memory'], reverse=True)[:limit]
    
    return {'top_cpu': top_cpu, 'top_mem': top_mem}

def save_metrics(metrics):
    """保存指标到文件"""
    metrics_file = DATA_DIR / "metrics.json"
    
    # 读取现有数据
    existing = []
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                existing = json.load(f)
        except:
            existing = []
    
    # 添加新指标
    existing.append(metrics)
    
    # 只保留最近1000条
    if len(existing) > 1000:
        existing = existing[-1000:]
    
    with open(metrics_file, 'w') as f:
        json.dump(existing, f, indent=2)

def main():
    print("💻 AgentCrew 资源监控")
    print("=" * 50)
    
    # CPU
    cpu = get_cpu_usage()
    cpu_cores = get_cpu_per_core()
    print(f"\n🔲 CPU:")
    print(f"  总使用率: {cpu}%")
    print(f"  核心使用率: ", end="")
    print(", ".join([f"Core{i}:{c}%" for i, c in enumerate(cpu_cores)]))
    
    # 内存
    mem = get_memory_usage()
    print(f"\n🧠 内存:")
    print(f"  总计: {mem['total']:.1f} GB")
    print(f"  已用: {mem['used']:.1f} GB ({mem['percent']}%)")
    print(f"  可用: {mem['available']:.1f} GB")
    
    # 磁盘
    disk = get_disk_usage('/')
    print(f"\n💾 磁盘:")
    print(f"  总计: {disk['total']:.1f} GB")
    print(f"  已用: {disk['used']:.1f} GB ({disk['percent']}%)")
    print(f"  可用: {disk['free']:.1f} GB")
    
    # 网络
    net = get_network_io()
    print(f"\n🌐 网络:")
    print(f"  发送: {net['bytes_sent'] / (1024**2):.2f} MB")
    print(f"  接收: {net['bytes_recv'] / (1024**2):.2f} MB")
    
    # 当前进程
    proc = get_process_info()
    print(f"\n⚙️ 当前进程:")
    print(f"  PID: {proc['pid']}")
    print(f"  名称: {proc['name']}")
    print(f"  CPU: {proc['cpu_percent']}%")
    print(f"  内存: {proc['memory_percent']:.2f}% ({proc['memory_info']:.1f} MB)")
    print(f"  线程: {proc['num_threads']}")
    
    # Top进程
    top = get_top_processes()
    print(f"\n🔥 Top进程 (CPU):")
    for p in top['top_cpu']:
        print(f"  {p['name'][:20]:20s} CPU: {p['cpu']:5.1f}%")
    
    print(f"\n🔥 Top进程 (内存):")
    for p in top['top_mem']:
        print(f"  {p['name'][:20]:20s} MEM: {p['memory']:5.1f}%")
    
    # 保存指标
    if '--save' in sys.argv:
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': cpu,
            'memory': mem,
            'disk': disk,
            'network': net,
            'process': proc
        }
        save_metrics(metrics)
        print(f"\n✅ 指标已保存")

if __name__ == "__main__":
    import sys
    main()
