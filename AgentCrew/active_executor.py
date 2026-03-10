#!/usr/bin/env python3
"""
AgentCrew 主动执行器
让 AgentCrew 不需要等待命令，主动发现问题、主动工作
"""
import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 导入 call_logger
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from call_logger import get_logger, CallStatus
except ImportError:
    from .call_logger import get_logger, CallStatus

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
LOG_DIR = f"{WORKSPACE}/logs"
ACTIVE_EXECUTION_LOG = f"{LOG_DIR}/active_execution.log"

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ACTIVE_EXECUTION_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ActivePatrol:
    """主动巡检器 - 定期检查项目状态"""
    
    def __init__(self, workspace: str = WORKSPACE):
        self.workspace = workspace
        self.targets = [
            f"{workspace}/scripts",
            f"{workspace}/AgentCrew/AgentCrew",
            f"{workspace}/data"
        ]
        self._call_logger = get_logger()
    
    def check_project_status(self) -> Dict[str, Any]:
        """检查项目整体状态"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="check_project_status",
            params={"workspace": self.workspace}
        )
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 检查脚本目录
        scripts_dir = f"{self.workspace}/scripts"
        if os.path.exists(scripts_dir):
            files = os.listdir(scripts_dir)
            py_files = [f for f in files if f.endswith('.py')]
            result["checks"]["scripts"] = {
                "total": len(files),
                "python": len(py_files),
                "last_modified": self._get_last_modified(scripts_dir)
            }
        
        # 检查数据目录
        data_dir = f"{self.workspace}/data"
        if os.path.exists(data_dir):
            try:
                with open(f"{data_dir}/tasks_source.json", "r") as f:
                    tasks = json.load(f)
                    pending = [t for t in tasks if t.get("state") in ["Zhongshu", "Menxia", "Assigned"]]
                    result["checks"]["tasks"] = {
                        "total": len(tasks),
                        "pending": len(pending),
                        "states": self._count_states(tasks)
                    }
            except Exception as e:
                result["checks"]["tasks"] = {"error": str(e)}
        
        # 检查日志
        log_dir = f"{self.workspace}/logs"
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            result["checks"]["logs"] = {
                "count": len(log_files),
                "files": log_files[:5]
            }
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"checks_count": len(result.get("checks", {}))},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return result
    
    def check_code_quality(self) -> Dict[str, Any]:
        """检查代码质量"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="check_code_quality",
            params={"targets": self.targets}
        )
        result = {
            "timestamp": datetime.now().isoformat(),
            "issues": []
        }
        
        # 尝试调用 self_inspector
        try:
            sys.path.insert(0, f"{WORKSPACE}/AgentCrew/AgentCrew")
            from self_inspector import CodeInspector
            
            inspector = CodeInspector()
            for target in self.targets:
                if os.path.exists(target):
                    inspector.inspect_directory(target)
            
            report = inspector.get_report()
            result["issues"] = report.get("issues", [])
            result["stats"] = report.get("stats", {})
        except Exception as e:
            result["error"] = str(e)
        
        duration_ms = (time.time() - start_time) * 1000
        issues_count = len(result.get("issues", []))
        self._call_logger.log_call_end(
            call_id,
            result={"issues_found": issues_count},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return result
    
    def check_task_queue(self) -> Dict[str, Any]:
        """检查任务队列状态"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="check_task_queue",
            params={"workspace": self.workspace}
        )
        result = {
            "timestamp": datetime.now().isoformat(),
            "queue": {}
        }
        
        tasks_file = f"{self.workspace}/data/tasks_source.json"
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, "r") as f:
                    tasks = json.load(f)
                
                # 统计各状态任务
                states = self._count_states(tasks)
                
                # 找出待处理的高优先级任务
                pending = [t for t in tasks if t.get("state") in ["Zhongshu", "Menxia"]]
                urgent = [t for t in pending if t.get("priority", 0) >= 5]
                
                result["queue"] = {
                    "total": len(tasks),
                    "pending": len(pending),
                    "urgent": len(urgent),
                    "by_state": states,
                    "stale_tasks": self._find_stale_tasks(tasks)
                }
            except Exception as e:
                result["error"] = str(e)
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"pending_tasks": result.get("queue", {}).get("pending", 0)},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return result
    
    def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源状态"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="check_system_resources",
            params={"workspace": self.workspace}
        )
        result = {
            "timestamp": datetime.now().isoformat(),
            "resources": {}
        }
        
        # 检查磁盘空间
        try:
            stat = os.statvfs(self.workspace)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            result["resources"]["disk_free_gb"] = round(free_gb, 2)
        except:
            pass
        
        # 检查内存使用
        try:
            with open("/proc/meminfo", "r") as f:
                mem_info = f.read()
                for line in mem_info.split("\n"):
                    if "MemAvailable" in line:
                        available_kb = int(line.split()[1])
                        result["resources"]["mem_available_mb"] = available_kb / 1024
                        break
        except:
            pass
        
        # 检查进程
        try:
            result["resources"]["openclaw_processes"] = self._count_processes("openclaw")
        except:
            pass
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result=result.get("resources", {}),
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return result
    
    def run_full_patrol(self) -> Dict[str, Any]:
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="run_full_patrol",
            params={"workspace": self.workspace}
        )
        """运行全面巡检"""
        logger.info("🔍 开始主动巡检...")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "patrol_id": int(time.time())
        }
        
        result["project_status"] = self.check_project_status()
        result["code_quality"] = self.check_code_quality()
        result["task_queue"] = self.check_task_queue()
        result["system_resources"] = self.check_system_resources()
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"patrol_id": result.get("patrol_id")},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info("✅ 巡检完成")
        
        return result
    
    def _get_last_modified(self, path: str) -> Optional[str]:
        """获取最后修改时间"""
        try:
            mtime = os.path.getmtime(path)
            return datetime.fromtimestamp(mtime).isoformat()
        except:
            return None
    
    def _count_states(self, tasks: List[Dict]) -> Dict[str, int]:
        """统计任务状态"""
        states = {}
        for task in tasks:
            state = task.get("state", "unknown")
            states[state] = states.get(state, 0) + 1
        return states
    
    def _find_stale_tasks(self, tasks: List[Dict], days: int = 3) -> List[Dict]:
        """找出长期未处理的任务"""
        stale = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for task in tasks:
            if task.get("state") in ["Zhongshu", "Menxia", "Assigned"]:
                updated = task.get("updated")
                if updated:
                    try:
                        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        if updated_dt.replace(tzinfo=None) < cutoff:
                            stale.append({
                                "id": task.get("id"),
                                "title": task.get("title"),
                                "state": task.get("state"),
                                "days_stale": (datetime.now() - updated_dt.replace(tzinfo=None)).days
                            })
                    except:
                        pass
        
        return stale[:5]  # 最多返回5个
    
    def _count_processes(self, name: str) -> int:
        """统计进程数"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", name],
                capture_output=True,
                text=True
            )
            return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except:
            return 0


class IssueIdentifier:
    """问题识别器 - 根据巡检结果自动判断需要做什么"""
    
    def __init__(self):
        self.rules = self._load_rules()
        self._call_logger = get_logger()
    
    def identify(self, patrol_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别问题并生成行动建议"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action="issue_identify",
            params={"rules_count": len(self.rules)}
        )
    
    def _load_rules(self) -> List[Dict]:
        """加载识别规则"""
        return [
            {
                "name": "代码质量问题",
                "condition": lambda r: r.get("code_quality", {}).get("stats", {}).get("issues_found", 0) > 0,
                "action": "fix_code_issues",
                "priority": 3
            },
            {
                "name": "任务积压",
                "condition": lambda r: r.get("task_queue", {}).get("queue", {}).get("pending", 0) > 10,
                "action": "escalate_tasks",
                "priority": 4
            },
            {
                "name": "任务长期未处理",
                "condition": lambda r: len(r.get("task_queue", {}).get("queue", {}).get("stale_tasks", [])) > 0,
                "action": "handle_stale_tasks",
                "priority": 5
            },
            {
                "name": "磁盘空间不足",
                "condition": lambda r: r.get("system_resources", {}).get("resources", {}).get("disk_free_gb", 100) < 5,
                "action": "cleanup_disk",
                "priority": 5
            },
            {
                "name": "进程异常",
                "condition": lambda r: r.get("system_resources", {}).get("resources", {}).get("openclaw_processes", 1) == 0,
                "action": "restart_service",
                "priority": 5
            },
            {
                "name": "待审核任务",
                "condition": lambda r: r.get("task_queue", {}).get("queue", {}).get("by_state", {}).get("Menxia", 0) > 0,
                "action": "notify_review",
                "priority": 3
            }
        ]
    
    def identify(self, patrol_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别问题并决定行动"""
        issues = []
        
        for rule in self.rules:
            try:
                if rule["condition"](patrol_result):
                    issues.append({
                        "name": rule["name"],
                        "action": rule["action"],
                        "priority": rule["priority"],
                        "details": self._extract_details(patrol_result, rule["action"])
                    })
            except Exception as e:
                logger.warning(f"规则检查失败 {rule['name']}: {e}")
        
        # 按优先级排序
        issues.sort(key=lambda x: x["priority"], reverse=True)
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"issues_identified": len(issues)},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(f"📋 识别到 {len(issues)} 个需要处理的问题")
        
        return issues
    
    def _extract_details(self, patrol_result: Dict, action: str) -> Dict:
        """提取详细信息"""
        details = {}
        
        if action == "fix_code_issues":
            issues = patrol_result.get("code_quality", {}).get("issues", [])
            details["count"] = len(issues)
            details["sample"] = issues[:3] if issues else []
        
        elif action == "handle_stale_tasks":
            stale = patrol_result.get("task_queue", {}).get("queue", {}).get("stale_tasks", [])
            details["stale_tasks"] = stale
        
        elif action == "escalate_tasks":
            pending = patrol_result.get("task_queue", {}).get("queue", {}).get("pending", 0)
            details["pending_count"] = pending
        
        return details


class AutoExecutor:
    """自动执行器 - 根据预设规则自动执行任务"""
    
    def __init__(self, workspace: str = WORKSPACE):
        self.workspace = workspace
        self.actions = self._register_actions()
        self.execution_log = []
        self._call_logger = get_logger()
    
    def _register_actions(self) -> Dict[str, Callable]:
        """注册可执行的动作"""
        return {
            "fix_code_issues": self._fix_code_issues,
            "handle_stale_tasks": self._handle_stale_tasks,
            "escalate_tasks": self._escalate_tasks,
            "cleanup_disk": self._cleanup_disk,
            "restart_service": self._restart_service,
            "notify_review": self._notify_review
        }
    
    def execute(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定动作"""
        start_time = time.time()
        action = issue.get("action")
        call_id = self._call_logger.log_call_start(
            source="active_executor",
            action=f"execute_{action}",
            params={"issue_name": issue.get("name")}
        )
        
        if action not in self.actions:
            self._call_logger.log_call_end(
                call_id,
                result={"reason": f"未知动作: {action}"},
                status=CallStatus.FAILED,
                duration_ms=0
            )
            return {"status": "skipped", "reason": f"未知动作: {action}"}
        
        logger.info(f"⚡ 开始执行: {issue.get('name')}")
        
        try:
            result = self.actions[action](issue)
            self.execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "issue": issue.get("name"),
                "action": action,
                "result": result
            })
            
            duration_ms = (time.time() - start_time) * 1000
            self._call_logger.log_call_end(
                call_id,
                result=result,
                status=CallStatus.SUCCESS,
                duration_ms=duration_ms
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._call_logger.log_call_end(
                call_id,
                result={"error": str(e)},
                status=CallStatus.FAILED,
                duration_ms=duration_ms
            )
            logger.error(f"❌ 执行失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def _fix_code_issues(self, issue: Dict) -> Dict:
        """修复代码问题"""
        # 调用自我迭代模块
        try:
            sys.path.insert(0, f"{WORKSPACE}/AgentCrew/AgentCrew")
            from self_iteration import AutoFixer
            
            fixer = AutoFixer(dry_run=False)
            # 获取问题列表
            details = issue.get("details", {})
            issues = details.get("sample", [])
            
            result = fixer.apply_fixes(issues)
            return {"status": "success", "fixed": len(result.get("fixes_applied", []))}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _handle_stale_tasks(self, issue: Dict) -> Dict:
        """处理长期未处理的任务"""
        stale = issue.get("details", {}).get("stale_tasks", [])
        
        results = []
        for task in stale:
            task_id = task.get("id")
            if task_id:
                # 发送提醒
                results.append(self._remind_task(task_id))
        
        return {"status": "success", "reminded": len(results)}
    
    def _remind_task(self, task_id: str) -> Dict:
        """提醒任务"""
        # 更新任务状态，添加提醒标记
        try:
            cmd = [
                sys.executable,
                f"{self.workspace}/scripts/kanban_update.py",
                "state",
                task_id,
                "Zhongshu",
                f"主动执行器提醒: 任务已积压 {task.get('days_stale', 0)} 天"
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            return {"task_id": task_id, "reminded": True}
        except Exception as e:
            return {"task_id": task_id, "error": str(e)}
    
    def _escalate_tasks(self, issue: Dict) -> Dict:
        """升级积压任务"""
        # 向尚书省发送提醒
        pending = issue.get("details", {}).get("pending_count", 0)
        logger.warning(f"⚠️ 任务积压: {pending} 个待处理")
        
        return {"status": "notified", "pending_count": pending}
    
    def _cleanup_disk(self, issue: Dict) -> Dict:
        """清理磁盘空间"""
        # 清理日志文件
        cleaned = 0
        
        log_dir = f"{self.workspace}/logs"
        if os.path.exists(log_dir):
            for f in os.listdir(log_dir):
                if f.endswith(".log") and os.path.getsize(f"{log_dir}/{f}") > 10*1024*1024:
                    try:
                        os.remove(f"{log_dir}/{f}")
                        cleaned += 1
                    except:
                        pass
        
        return {"status": "success", "cleaned_files": cleaned}
    
    def _restart_service(self, issue: Dict) -> Dict:
        """重启服务"""
        # 尝试启动 OpenClaw gateway
        try:
            subprocess.run(
                ["openclaw", "gateway", "start"],
                capture_output=True,
                timeout=30
            )
            return {"status": "success", "action": "gateway_started"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _notify_review(self, issue: Dict) -> Dict:
        """通知审核"""
        # 通知门下省有任务待审核
        by_state = issue.get("details", {}).get("by_state", {})
        menxia_count = by_state.get("Menxia", 0)
        
        logger.info(f"📋 门下省有 {menxia_count} 个任务待审核")
        
        return {"status": "notified", "count": menxia_count}


class ActiveReporter:
    """主动汇报器 - 完成任务后自动汇报结果"""
    
    def __init__(self, workspace: str = WORKSPACE):
        self.workspace = workspace
        self.report_log = f"{LOG_DIR}/active_execution_reports.json"
        self.reports = self._load_reports()
    
    def _load_reports(self) -> List[Dict]:
        """加载历史报告"""
        if os.path.exists(self.report_log):
            try:
                with open(self.report_log, "r") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_reports(self):
        """保存报告"""
        with open(self.report_log, "w") as f:
            json.dump(self.reports, f, indent=2, ensure_ascii=False)
    
    def report(self, patrol_result: Dict, issues_identified: List, executions: List) -> Dict:
        """生成并汇报结果"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "patrol_id": patrol_result.get("patrol_id"),
            "issues_found": len(issues_identified),
            "issues_handled": len([e for e in executions if e.get("status") == "success"]),
            "executions": executions,
            "summary": self._generate_summary(patrol_result, issues_identified, executions)
        }
        
        self.reports.append(report)
        self._save_reports()
        
        # 打印汇报
        self._print_report(report)
        
        return report
    
    def _generate_summary(self, patrol_result: Dict, issues: List, executions: List) -> str:
        """生成摘要"""
        parts = []
        
        if issues:
            parts.append(f"发现 {len(issues)} 个问题")
        
        success = sum(1 for e in executions if e.get("status") == "success")
        if executions:
            parts.append(f"已处理 {success}/{len(executions)} 个")
        
        # 添加关键指标
        task_queue = patrol_result.get("task_queue", {}).get("queue", {})
        if task_queue.get("pending", 0) > 0:
            parts.append(f"待处理任务: {task_queue['pending']}")
        
        return "; ".join(parts) if parts else "一切正常"
    
    def _print_report(self, report: Dict):
        """打印报告"""
        logger.info("=" * 50)
        logger.info(f"📊 主动执行报告 - {report['timestamp']}")
        logger.info(f"   发现问题: {report['issues_found']}")
        logger.info(f"   已处理: {report['issues_handled']}")
        logger.info(f"   摘要: {report['summary']}")
        logger.info("=" * 50)


class ActiveExecutor:
    """主动执行器主控制器 - 整合巡检、识别、执行、汇报"""
    
    def __init__(self, workspace: str = WORKSPACE, auto_execute: bool = True):
        self.workspace = workspace
        self.auto_execute = auto_execute
        
        self.patrol = ActivePatrol(workspace)
        self.identifier = IssueIdentifier()
        self.executor = AutoExecutor(workspace)
        self.reporter = ActiveReporter(workspace)
        
        self.stats = {
            "total_runs": 0,
            "issues_identified": 0,
            "issues_fixed": 0
        }
    
    def run_cycle(self) -> Dict:
        """运行一个完整的主动执行周期"""
        self.stats["total_runs"] += 1
        
        cycle_start = datetime.now()
        logger.info(f"🔄 开始主动执行周期 #{self.stats['total_runs']}")
        
        result = {
            "cycle_id": self.stats["total_runs"],
            "start_time": cycle_start.isoformat()
        }
        
        # 1. 主动巡检
        patrol_result = self.patrol.run_full_patrol()
        result["patrol"] = patrol_result
        
        # 2. 识别问题
        issues = self.identifier.identify(patrol_result)
        result["issues_identified"] = len(issues)
        result["issues"] = issues
        self.stats["issues_identified"] += len(issues)
        
        # 3. 自动执行
        executions = []
        if self.auto_execute and issues:
            for issue in issues:
                # 只执行高优先级的
                if issue.get("priority", 0) >= 3:
                    exec_result = self.executor.execute(issue)
                    executions.append({
                        "issue": issue.get("name"),
                        "action": issue.get("action"),
                        "result": exec_result
                    })
                    if exec_result.get("status") == "success":
                        self.stats["issues_fixed"] += 1
        
        result["executions"] = executions
        
        # 4. 主动汇报
        report = self.reporter.report(patrol_result, issues, executions)
        result["report"] = report
        
        cycle_end = datetime.now()
        result["end_time"] = cycle_end.isoformat()
        result["duration_seconds"] = (cycle_end - cycle_start).total_seconds()
        
        logger.info(f"✅ 主动执行周期完成: {result['duration_seconds']:.1f}秒")
        
        return result
    
    def run_scheduled(self, interval_minutes: int = 30):
        """定时运行主动执行"""
        logger.info(f"⏰ 启动定时主动执行 (间隔: {interval_minutes} 分钟)")
        
        while True:
            try:
                self.run_cycle()
                logger.info(f"😴 等待 {interval_minutes} 分钟...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("⏹️ 定时主动执行已停止")
                break
            except Exception as e:
                logger.error(f"❌ 主动执行周期出错: {e}")
                time.sleep(60)


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentCrew 主动执行器")
    parser.add_argument("--once", "-o", action="store_true", help="仅运行一次")
    parser.add_argument("--schedule", "-s", type=int, help="定时运行(分钟)")
    parser.add_argument("--no-auto", action="store_true", help="仅巡检，不自动执行")
    parser.add_argument("--patrol-only", "-p", action="store_true", help="仅巡检，不识别不执行")
    
    args = parser.parse_args()
    
    executor = ActiveExecutor(auto_execute=not args.no_auto)
    
    if args.patrol_only:
        # 仅巡检
        result = executor.patrol.run_full_patrol()
        print("\n📊 巡检结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.schedule:
        executor.run_scheduled(interval_minutes=args.schedule)
    else:
        # 默认：运行一次完整周期
        result = executor.run_cycle()
        print("\n📊 执行结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
