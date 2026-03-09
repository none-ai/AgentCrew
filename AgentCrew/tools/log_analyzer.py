#!/usr/bin/env python3
"""
AgentCrew 日志分析工具
分析系统日志，提取关键信息
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

LOG_DIR = Path("/home/stlin-claw/.openclaw/workspace-taizi/logs")

def find_log_files():
    """查找日志文件"""
    if LOG_DIR.exists():
        return list(LOG_DIR.glob("*.log"))
    return []

def parse_log_line(line):
    """解析日志行"""
    # 尝试匹配常见日志格式
    patterns = [
        # 格式: 2024-01-01 12:00:00 [LEVEL] message
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.*)',
        # 格式: 2024-01-01T12:00:00 LEVEL: message
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+(\w+):\s+(.*)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            return {
                'timestamp': match.group(1),
                'level': match.group(2),
                'message': match.group(3)
            }
    
    return None

def analyze_logs(log_files):
    """分析日志文件"""
    levels = Counter()
    messages = []
    errors = []
    warnings = []
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed = parse_log_line(line)
                    if parsed:
                        levels[parsed['level']] += 1
                        messages.append(parsed)
                        
                        if parsed['level'] in ['ERROR', 'CRITICAL']:
                            errors.append(parsed)
                        elif parsed['level'] in ['WARNING', 'WARN']:
                            warnings.append(parsed)
        except Exception as e:
            print(f"读取日志文件失败 {log_file}: {e}")
    
    return {
        'levels': levels,
        'messages': messages,
        'errors': errors,
        'warnings': warnings,
        'total': len(messages)
    }

def find_error_patterns(errors):
    """查找错误模式"""
    patterns = Counter()
    
    for error in errors:
        msg = error.get('message', '')
        # 提取关键错误信息
        if 'Exception' in msg:
            patterns['Exception'] += 1
        if 'Timeout' in msg:
            patterns['Timeout'] += 1
        if 'Connection' in msg:
            patterns['Connection'] += 1
        if 'Memory' in msg:
            patterns['Memory'] += 1
        if 'Permission' in msg:
            patterns['Permission'] += 1
        # 提取具体异常类型
        exc_match = re.search(r'(\w+Exception|\w+Error)', msg)
        if exc_match:
            patterns[exc_match.group(1)] += 1
    
    return patterns

def main():
    print("📜 AgentCrew 日志分析")
    print("=" * 50)
    
    log_files = find_log_files()
    
    if not log_files:
        print("未找到日志文件")
        return
    
    print(f"找到 {len(log_files)} 个日志文件")
    
    result = analyze_logs(log_files)
    
    # 日志级别统计
    print(f"\n📊 日志级别统计 (共 {result['total']} 条):")
    for level, count in result['levels'].most_common():
        pct = count / result['total'] * 100
        bar = '█' * int(pct / 5)
        print(f"  {level:10s}: {count:5d} ({pct:5.1f}%) {bar}")
    
    # 错误统计
    if result['errors']:
        print(f"\n❌ 错误日志 ({len(result['errors'])} 条):")
        error_patterns = find_error_patterns(result['errors'])
        print("  错误模式:")
        for pattern, count in error_patterns.most_common(10):
            print(f"    {pattern}: {count}")
        
        print("\n  最近错误:")
        for error in result['errors'][:5]:
            print(f"    {error['timestamp']} - {error['message'][:80]}")
    
    # 警告统计
    if result['warnings']:
        print(f"\n⚠️  警告日志 ({len(result['warnings'])} 条):")
        for warning in result['warnings'][:5]:
            print(f"    {warning['timestamp']} - {warning['message'][:80]}")

if __name__ == "__main__":
    main()
