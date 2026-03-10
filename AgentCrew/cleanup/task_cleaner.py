"""
任务清理器
自动清理过期任务、归档已完成任务
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

# 注意: 不直接导入 tasks 模块，避免循环依赖

from .cleaner import BaseCleaner, CleanupPolicy

logger = logging.getLogger(__name__)


class TaskAgePolicy(Enum):
    """任务年龄策略"""
    CREATED = "created"       # 基于创建时间
    MODIFIED = "modified"    # 基于修改时间
    COMPLETED = "completed"  # 基于完成时间


class TaskItem:
    """任务清理项"""
    
    def __init__(self, task_data: Dict[str, Any]):
        self.id = task_data.get("id", "")
        self.data = task_data
        self._created_at = task_data.get("created_at")
        self._completed_at = task_data.get("completed_at")
        self.status = task_data.get("status", "pending")
    
    @property
    def created_at(self) -> Optional[datetime]:
        if self._created_at:
            return datetime.fromisoformat(self._created_at)
        return None
    
    @property
    def modified_at(self) -> Optional[datetime]:
        # 修改时间可以从 data 中获取或推断
        if self._completed_at:
            return datetime.fromisoformat(self._completed_at)
        if self._created_at:
            return datetime.fromisoformat(self._created_at)
        return None
    
    @property
    def completed_at(self) -> Optional[datetime]:
        if self._completed_at:
            return datetime.fromisoformat(self._completed_at)
        return None
    
    def is_expired(self, days: int, policy: TaskAgePolicy = TaskAgePolicy.COMPLETED) -> bool:
        """判断任务是否过期"""
        if days <= 0:
            return False
        
        if self.status not in ["completed", "failed", "cancelled"]:
            return False
        
        # 基于完成时间判断
        ref_time = None
        if policy == TaskAgePolicy.COMPLETED:
            ref_time = self.completed_at
        elif policy == TaskAgePolicy.CREATED:
            ref_time = self.created_at
        else:
            ref_time = self.modified_at
        
        if ref_time is None:
            return False
        
        return (datetime.now() - ref_time).days > days
    
    def cleanup(self) -> bool:
        """删除任务数据"""
        # 实际删除由 TaskManager 处理
        return True
    
    def archive(self, archive_path: str) -> bool:
        """归档任务"""
        try:
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"归档任务失败: {self.id}, {e}")
            return False


class TaskCleaner(BaseCleaner):
    """任务清理器"""
    
    def __init__(self, data_dir: str = "./data"):
        super().__init__(data_dir)
        self.tasks_dir = self.data_dir / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.age_policy = TaskAgePolicy.COMPLETED
    
    def scan(self, status_filter: Optional[List[str]] = None) -> List[TaskItem]:
        """扫描所有任务"""
        items = []
        
        # 扫描 tasks 目录
        if self.tasks_dir.exists():
            for task_file in self.tasks_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    if isinstance(task_data, dict) and "id" in task_data:
                        if status_filter is None or task_data.get("status") in status_filter:
                            items.append(TaskItem(task_data))
                except Exception as e:
                    logger.warning(f"读取任务文件失败: {task_file}, {e}")
        
        # 也扫描旧的 tasks.json 文件
        old_tasks_file = self.data_dir / "tasks.json"
        if old_tasks_file.exists():
            try:
                with open(old_tasks_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                
                if isinstance(tasks_data, dict):
                    for task_id, task_data in tasks_data.items():
                        if isinstance(task_data, dict):
                            if status_filter is None or task_data.get("status") in status_filter:
                                items.append(TaskItem(task_data))
            except Exception as e:
                logger.warning(f"读取旧任务文件失败: {e}")
        
        # 扫描持久化数据中的任务
        persistence_file = self.data_dir / "persistence" / "tasks.json"
        if persistence_file.exists():
            try:
                with open(persistence_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                
                if isinstance(tasks_data, dict):
                    for task_id, task_data in tasks_data.items():
                        if isinstance(task_data, dict):
                            if status_filter is None or task_data.get("status") in status_filter:
                                items.append(TaskItem(task_data))
            except Exception as e:
                logger.warning(f"读取持久化任务失败: {e}")
        
        return items
    
    def should_clean(self, item: TaskItem, max_age_days: int = 30, **kwargs) -> bool:
        """判断任务是否应该清理"""
        policy = kwargs.get("age_policy", self.age_policy)
        
        # 清理已完成/失败/取消的任务
        completed_statuses = ["completed", "failed", "cancelled"]
        
        if item.status not in completed_statuses:
            return False
        
        return item.is_expired(max_age_days, policy)
    
    def clean_item(self, item: TaskItem, **kwargs) -> bool:
        """清理单个任务"""
        try:
            # 删除任务文件
            task_file = self.tasks_dir / f"{item.id}.json"
            if task_file.exists():
                task_file.unlink()
            
            # 从 tasks.json 中移除
            old_tasks_file = self.data_dir / "tasks.json"
            if old_tasks_file.exists():
                try:
                    with open(old_tasks_file, 'r', encoding='utf-8') as f:
                        tasks_data = json.load(f)
                    
                    if item.id in tasks_data:
                        del tasks_data[item.id]
                        
                        with open(old_tasks_file, 'w', encoding='utf-8') as f:
                            json.dump(tasks_data, f, indent=2)
                except Exception as e:
                    logger.warning(f"更新 tasks.json 失败: {e}")
            
            return True
        except Exception as e:
            logger.error(f"清理任务失败: {item.id}, {e}")
            return False
    
    def clean(
        self,
        policy: CleanupPolicy = CleanupPolicy.EXPIRED_ONLY,
        max_age_days: int = 30,
        archive: bool = True,
        archive_dir: str = "./data/archives",
        **kwargs
    ) -> Dict[str, Any]:
        """执行任务清理"""
        return super().clean(
            policy=policy,
            max_age_days=max_age_days,
            archive=archive,
            archive_dir=archive_dir,
            **kwargs
        )
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        items = self.scan()
        
        stats = {
            "total": len(items),
            "by_status": {},
            "oldest_completed": None,
            "oldest_failed": None,
            "oldest_cancelled": None
        }
        
        for item in items:
            status = item.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            if status == "completed" and item.completed_at:
                if stats["oldest_completed"] is None or item.completed_at < stats["oldest_completed"]:
                    stats["oldest_completed"] = item.completed_at
            
            if status == "failed" and item.completed_at:
                if stats["oldest_failed"] is None or item.completed_at < stats["oldest_failed"]:
                    stats["oldest_failed"] = item.completed_at
            
            if status == "cancelled" and item.completed_at:
                if stats["oldest_cancelled"] is None or item.completed_at < stats["oldest_cancelled"]:
                    stats["oldest_cancelled"] = item.completed_at
        
        return stats
