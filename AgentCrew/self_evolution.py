#!/usr/bin/env python3
"""
AgentCrew 持续进化模块
整合自我巡检、自我迭代、定期回顾
"""
import os
import sys
import json
import time
import logging
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 支持直接运行和模块导入两种方式
try:
    from .call_logger import get_logger, CallStatus
    from .self_inspector import CodeInspector, run_inspection
    from .self_iteration import AutoFixer, run_auto_fix, suggest_improvements
except ImportError:
    from call_logger import get_logger, CallStatus
    from self_inspector import CodeInspector, run_inspection
    from self_iteration import AutoFixer, run_auto_fix, suggest_improvements

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
LOG_DIR = f"{WORKSPACE}/logs"
EVOLUTION_DB = f"{LOG_DIR}/evolution.db"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/self_evolution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EvolutionHistory:
    """进化历史记录 - SQLite版本"""
    
    def __init__(self, db_path: str = EVOLUTION_DB):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER,
                timestamp TEXT NOT NULL,
                issues_found INTEGER,
                issues_fixed INTEGER,
                duration_ms REAL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON evolution_history(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def add_record(self, record: Dict):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO evolution_history 
            (cycle_id, timestamp, issues_found, issues_fixed, duration_ms, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record.get("cycle_id", 0),
            datetime.now().isoformat(),
            record.get("issues_found", 0),
            record.get("issues_fixed", 0),
            record.get("duration_ms", 0),
            json.dumps(record.get("details", {}))
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent(self, days: int = 7) -> List[Dict]:
        """获取最近 N 天的记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, cycle_id, timestamp, issues_found, issues_fixed, duration_ms, details
            FROM evolution_history
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        """, (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "cycle_id": row[1],
                "timestamp": row[2],
                "issues_found": row[3],
                "issues_fixed": row[4],
                "duration_ms": row[5],
                "details": json.loads(row[6]) if row[6] else {}
            }
            for row in rows
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(issues_found) as total_found,
                SUM(issues_fixed) as total_fixed,
                AVG(issues_found) as avg_found,
                AVG(issues_fixed) as avg_fixed
            FROM evolution_history
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_runs": row[0] or 0,
            "total_issues_found": row[1] or 0,
            "total_issues_fixed": row[2] or 0,
            "avg_issues_found": row[3] or 0,
            "avg_issues_fixed": row[4] or 0
        }
        """获取统计摘要"""
        if not self.history:
            return {"total_cycles": 0, "issues_found": 0, "issues_fixed": 0}
        
        total_issues = sum(r.get("issues_found", 0) for r in self.history)
        total_fixed = sum(r.get("issues_fixed", 0) for r in self.history)
        
        return {
            "total_cycles": len(self.history),
            "issues_found": total_issues,
            "issues_fixed": total_fixed,
            "last_cycle": self.history[-1] if self.history else None
        }


class SelfEvolution:
    """自我持续进化控制器"""
    
    def __init__(self, workspace: str = WORKSPACE, auto_fix: bool = False):
        self.workspace = workspace
        self.auto_fix = auto_fix
        self.inspector = CodeInspector()
        self.history = EvolutionHistory()
        # 重新启用 call_logger
        self._call_logger = get_logger()
        self.stats = {
            "total_runs": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "uptime_start": datetime.now().isoformat()
        }
    
    def inspect(self, target_dir: str = None) -> Dict[str, Any]:
        """执行自我巡检"""
        start_time = time.time()
        if self._call_logger:
            call_id = self._call_logger.log_call_start(
                source="self_evolution",
                action="inspect",
                params={"target_dir": target_dir}
            )
        
        logger.info("🔍 开始自我巡检...")
        
        if target_dir:
            self.inspector.inspect_directory(target_dir)
        else:
            # 默认巡检关键目录
            self.inspector.inspect_directory(f"{self.workspace}/scripts")
            self.inspector.inspect_directory(f"{self.workspace}/AgentCrew/AgentCrew")
        
        report = self.inspector.get_report()
        
        duration_ms = (time.time() - start_time) * 1000
        if self._call_logger:
            self._call_logger.log_call_end(
                call_id,
                result={"issues_found": report['stats']['issues_found']},
                status=CallStatus.SUCCESS,
                duration_ms=duration_ms
            )
        
        logger.info(f"📊 巡检完成: 发现 {report['stats']['issues_found']} 个问题")
        
        return report
    
    def iterate(self, issues: List[Dict], dry_run: bool = True) -> Dict[str, Any]:
        """执行自我迭代/修复"""
        if not self.auto_fix:
            dry_run = True
            logger.info("🔧 自动修复已禁用，仅进行问题分析")
        
        logger.info(f"🔧 开始自我迭代 (dry_run={dry_run})...")
        
        fixer = AutoFixer(dry_run=dry_run)
        result = fixer.apply_fixes(issues)
        
        logger.info(f"📊 迭代完成: 尝试修复 {result['auto_fixable_attempted']} 个问题")
        
        return result
    
    def reflect(self) -> Dict[str, Any]:
        """定期回顾总结"""
        logger.info("📝 开始自我回顾...")
        
        # 获取最近一周的记录
        recent = self.history.get_recent(days=7)
        
        summary = {
            "period": "7 days",
            "total_cycles": len(recent),
            "issues_trend": [],
            "top_issues": {}
        }
        
        # 分析趋势
        for record in recent:
            summary["issues_trend"].append({
                "date": record.get("timestamp", "")[:10],
                "found": record.get("issues_found", 0),
                "fixed": record.get("issues_fixed", 0)
            })
        
        # 统计常见问题类型
        issue_counts = {}
        for record in recent:
            for issue in record.get("issues", []):
                category = issue.get("category", "unknown")
                issue_counts[category] = issue_counts.get(category, 0) + 1
        
        summary["top_issues"] = dict(sorted(
            issue_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5])
        
        # 生成改进建议
        suggestions = []
        if summary["top_issues"]:
            suggestions.append(f"过去7天最常见问题类型: {list(summary['top_issues'].keys())[0]}")
        
        summary["suggestions"] = suggestions
        
        logger.info(f"📊 回顾完成: 共 {len(recent)} 次巡检周期")
        
        return summary
    
    def run_cycle(self, target_dir: str = None, dry_run: bool = True) -> Dict[str, Any]:
        """运行一个完整的进化周期"""
        self.stats["total_runs"] += 1
        
        cycle_start = datetime.now()
        result = {
            "cycle_id": self.stats["total_runs"],
            "start_time": cycle_start.isoformat(),
        }
        
        # 1. 巡检
        inspection = self.inspect(target_dir)
        result["issues_found"] = inspection["stats"]["issues_found"]
        result["issues"] = inspection["issues"]
        
        # 2. 迭代修复
        iteration = self.iterate(inspection["issues"], dry_run=dry_run)
        result["issues_fixed"] = len(iteration.get("fixes_applied", []))
        
        # 3. 记录历史
        cycle_end = datetime.now()
        result["end_time"] = cycle_end.isoformat()
        result["duration_seconds"] = (cycle_end - cycle_start).total_seconds()
        
        self.history.add_record(result)
        
        logger.info(f"✅ 进化周期 {result['cycle_id']} 完成: "
                   f"发现 {result['issues_found']} 个问题, "
                   f"修复 {result['issues_fixed']} 个")
        
        return result
    
    def run_scheduled(self, interval_minutes: int = 60):
        """定时运行进化周期"""
        logger.info(f"⏰ 启动定时进化 (间隔: {interval_minutes} 分钟)")
        
        while True:
            try:
                self.run_cycle(dry_run=not self.auto_fix)
                logger.info(f"😴 等待 {interval_minutes} 分钟...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("⏹️ 定时进化已停止")
                break
            except Exception as e:
                logger.error(f"❌ 进化周期出错: {e}")
                time.sleep(60)  # 出错后等1分钟重试


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentCrew 自我持续改进")
    parser.add_argument("--inspect", "-i", action="store_true", help="仅巡检")
    parser.add_argument("--iterate", "-t", action="store_true", help="执行迭代修复")
    parser.add_argument("--reflect", "-r", action="store_true", help="执行回顾总结")
    parser.add_argument("--auto-fix", "-a", action="store_true", help="启用自动修复")
    parser.add_argument("--schedule", "-s", type=int, help="定时运行(分钟)")
    parser.add_argument("--target", "-d", type=str, help="巡检目标目录")
    parser.add_argument("--no-dry-run", action="store_true", help="实际执行修复(危险)")
    
    args = parser.parse_args()
    
    evolution = SelfEvolution(auto_fix=args.auto_fix or args.no_dry_run)
    
    if args.schedule:
        evolution.runScheduled(interval_minutes=args.schedule)
    elif args.reflect:
        result = evolution.reflect()
        print("\n📊 回顾总结:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.iterate:
        report = evolution.inspect(args.target)
        result = evolution.iterate(report["issues"], dry_run=not args.no_dry_run)
        print("\n📊 迭代结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.inspect:
        report = evolution.inspect(args.target)
        print("\n📊 巡检报告:")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # 默认：运行完整周期
        result = evolution.run_cycle(args.target, dry_run=not args.no_dry_run)
        print("\n📊 进化周期结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
