"""
OpenAgent 任务调度器
负责任务的自动调度、负载均衡和并行执行
"""
import os
import json
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import defaultdict

# 配置文件路径
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker_config.json")

def _load_worker_config() -> Dict:
    """加载 worker 配置"""
    default_config = {
        "worker": {
            "max_workers": 8,
            "min_workers": 2,
            "task_timeout_seconds": 300,
            "idle_timeout_seconds": 600,
            "auto_scale": False
        }
    }
    
    try:
        if os.path.exists(_config_path):
            with open(_config_path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    
    return default_config

# 加载配置
_worker_config = _load_worker_config()
DEFAULT_MAX_WORKERS = _worker_config.get("worker", {}).get("max_workers", 8)

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = None):
        # 如果未指定，使用配置文件中的默认值
        if max_workers is None:
            max_workers = DEFAULT_MAX_WORKERS
        self.max_workers = max_workers
        self.active_workers = 0
        self.task_queue = []
        self.running = False
        self.lock = threading.Lock()
        self.worker_stats = defaultdict(lambda: {"tasks": 0, "completed": 0, "failed": 0})
        
        # 任务执行回调
        self.executor_callback: Optional[Callable] = None
    
    def set_executor(self, callback: Callable):
        """设置任务执行回调"""
        self.executor_callback = callback
    
    def add_task(self, task: Dict, priority: int = 0) -> bool:
        """添加任务到队列"""
        with self.lock:
            # 优先级队列：数字越大优先级越高
            self.task_queue.append({
                "task": task,
                "priority": priority,
                "added_at": time.time()
            })
            # 按优先级排序
            self.task_queue.sort(key=lambda x: x["priority"], reverse=True)
            return True
    
    def get_next_task(self) -> Optional[Dict]:
        """获取下一个任务"""
        with self.lock:
            if not self.task_queue:
                return None
            
            if self.active_workers >= self.max_workers:
                return None
            
            task_item = self.task_queue.pop(0)
            self.active_workers += 1
            return task_item
    
    def complete_task(self, task_id: str, worker_id: str, success: bool):
        """完成任务"""
        with self.lock:
            self.active_workers -= 1
            if success:
                self.worker_stats[worker_id]["completed"] += 1
            else:
                self.worker_stats[worker_id]["failed"] += 1
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        with self.lock:
            return {
                "running": self.running,
                "max_workers": self.max_workers,
                "active_workers": self.active_workers,
                "queued_tasks": len(self.task_queue),
                "worker_stats": dict(self.worker_stats)
            }
    
    def get_queue_info(self) -> Dict:
        """获取队列信息"""
        with self.lock:
            return {
                "total": len(self.task_queue),
                "tasks": [
                    {
                        "id": t["task"].get("id"),
                        "title": t["task"].get("title"),
                        "priority": t["priority"]
                    }
                    for t in self.task_queue[:10]  # 只返回前10个
                ]
            }


class ParallelDispatcher:
    """并行任务分发器"""
    
    def __init__(self):
        self.schedulers: Dict[str, TaskScheduler] = {}
        self.default_scheduler = TaskScheduler(max_workers=DEFAULT_MAX_WORKERS)
        self.schedulers["default"] = self.default_scheduler
    
    def create_scheduler(self, name: str, max_workers: int = 4) -> TaskScheduler:
        """创建新的调度器"""
        scheduler = TaskScheduler(max_workers)
        self.schedulers[name] = scheduler
        return scheduler
    
    def get_scheduler(self, name: str = "default") -> Optional[TaskScheduler]:
        """获取调度器"""
        return self.schedulers.get(name)
    
    def dispatch(self, tasks: List[Dict], scheduler_name: str = "default",
                 priority_fn: Callable[[Dict], int] = None) -> Dict:
        """分发任务"""
        scheduler = self.schedulers.get(scheduler_name)
        if not scheduler:
            return {"status": "error", "message": f"Scheduler {scheduler_name} not found"}
        
        results = {
            "dispatched": 0,
            "queued": 0,
            "failed": 0
        }
        
        for task in tasks:
            try:
                priority = priority_fn(task) if priority_fn else 0
                scheduler.add_task(task, priority)
                results["dispatched"] += 1
            except Exception as e:
                results["failed"] += 1
        
        results["queued"] = scheduler.task_queue.__len__()
        return results
    
    def get_all_status(self) -> Dict:
        """获取所有调度器状态"""
        return {
            name: scheduler.get_status()
            for name, scheduler in self.schedulers.items()
        }


# 全局调度器
_dispatcher = ParallelDispatcher()

def get_dispatcher() -> ParallelDispatcher:
    """获取全局调度器"""
    return _dispatcher
