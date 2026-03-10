#!/usr/bin/env python3
"""
定时任务模块 - 供 systemd 或 cron 调用
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AgentCrew.self_evolution import SelfEvolution

def main():
    """执行一次进化周期"""
    evolution = SelfEvolution(auto_fix=False)
    result = evolution.run_cycle(dry_run=True)
    
    print(f"进化周期完成:")
    print(f"  - 发现问题: {result['issues_found']}")
    print(f"  - 修复问题: {result['issues_fixed']}")
    print(f"  - 耗时: {result['duration_seconds']:.2f}秒")
    
    return 0 if result['issues_found'] < 100 else 1  # 问题太多返回错误

if __name__ == "__main__":
    sys.exit(main())
