"""
自动清理器核心模块
"""
import os
import sys
import json
import shutil
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum

# 导入 call_logger
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from call_logger import get_logger, CallStatus
except ImportError:
    from ..call_logger import get_logger, CallStatus

logger = logging.getLogger(__name__)


class CleanupPolicy(Enum):
    """清理策略"""
    ALL = "all"                    # 全部清理
    EXPIRED_ONLY = "expired"       # 仅清理过期的
    ARCHIVE_FIRST = "archive"      # 先归档再清理
    DRY_RUN = "dry_run"            # 模拟运行，不实际清理


class Cleanable(ABC):
    """可清理项基类"""
    
    @property
    @abstractmethod
    def created_at(self) -> Optional[datetime]:
        """创建时间"""
        pass
    
    @property
    @abstractmethod
    def modified_at(self) -> Optional[datetime]:
        """修改时间"""
        pass
    
    @property
    @abstractmethod
    def is_expired(self, days: int) -> bool:
        """是否已过期"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """执行清理"""
        pass
    
    @abstractmethod
    def archive(self, archive_path: str) -> bool:
        """归档"""
        pass


class BaseCleaner(ABC):
    """清理器基类"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            "total_scanned": 0,
            "cleaned": 0,
            "archived": 0,
            "errors": 0
        }
    
    @abstractmethod
    def scan(self, **kwargs) -> List[Any]:
        """扫描可清理项"""
        pass
    
    @abstractmethod
    def should_clean(self, item: Any, **kwargs) -> bool:
        """判断是否应该清理"""
        pass
    
    @abstractmethod
    def clean_item(self, item: Any, **kwargs) -> bool:
        """清理单个项"""
        pass
    
    def clean(
        self, 
        policy: CleanupPolicy = CleanupPolicy.EXPIRED_ONLY,
        max_age_days: int = 30,
        archive: bool = True,
        archive_dir: str = "./data/archives",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行清理
        
        Args:
            policy: 清理策略
            max_age_days: 最大保留天数
            archive: 是否先归档
            archive_dir: 归档目录
            
        Returns:
            清理统计信息
        """
        self.stats = {
            "total_scanned": 0,
            "cleaned": 0,
            "archived": 0,
            "errors": 0,
            "skipped": 0
        }
        
        # 扫描
        items = self.scan(**kwargs)
        self.stats["total_scanned"] = len(items)
        
        logger.info(f"扫描到 {len(items)} 个可清理项")
        
        if policy == CleanupPolicy.DRY_RUN:
            logger.info("模拟运行模式，仅扫描不清理")
            return self.stats
        
        # 归档目录
        archive_path = Path(archive_dir)
        if archive:
            archive_path.mkdir(parents=True, exist_ok=True)
        
        for item in items:
            try:
                if not self.should_clean(item, max_age_days=max_age_days, **kwargs):
                    self.stats["skipped"] += 1
                    continue
                
                # 归档
                if archive and hasattr(item, "archive"):
                    archive_file = archive_path / f"{type(item).__name__}_{item.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                    if item.archive(str(archive_file)):
                        self.stats["archived"] += 1
                
                # 清理
                if self.clean_item(item, **kwargs):
                    self.stats["cleaned"] += 1
                else:
                    self.stats["errors"] += 1
                    
            except Exception as e:
                logger.error(f"清理项失败: {e}")
                self.stats["errors"] += 1
        
        logger.info(f"清理完成: 扫描{self.stats['total_scanned']}, 清理{self.stats['cleaned']}, 归档{self.stats['archived']}, 错误{self.stats['errors']}")
        
        return self.stats


class AutoCleaner:
    """自动清理器 - 整合所有清理功能"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 导入各清理器
        from .task_cleaner import TaskCleaner
        from .data_cleaner import DataCleaner
        from .file_cleaner import FileCleaner
        from .log_cleaner import LogCleaner
        
        self.cleaners = {
            "tasks": TaskCleaner(data_dir),
            "data": DataCleaner(data_dir),
            "files": FileCleaner(data_dir),
            "logs": LogCleaner(data_dir)
        }
        
        self._call_logger = get_logger()
    
    def clean_all(
        self,
        policy: CleanupPolicy = CleanupPolicy.EXPIRED_ONLY,
        max_age_days: int = 30,
        archive: bool = True,
        archive_dir: str = "./data/archives",
        clean_tasks: bool = True,
        clean_data: bool = True,
        clean_files: bool = True,
        clean_logs: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行所有清理
        
        Args:
            policy: 清理策略
            max_age_days: 最大保留天数
            archive: 是否归档
            archive_dir: 归档目录
            clean_tasks: 是否清理任务
            clean_data: 是否清理数据
            clean_files: 是否清理文件
            clean_logs: 是否清理日志
            
        Returns:
            总体统计信息
        """
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="cleanup",
            action="clean_all",
            params={
                "policy": policy.value,
                "max_age_days": max_age_days,
                "archive": archive,
                "clean_tasks": clean_tasks,
                "clean_data": clean_data,
                "clean_files": clean_files,
                "clean_logs": clean_logs
            }
        )
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "policy": policy.value,
            "details": {}
        }
        
        total_stats = {
            "total_scanned": 0,
            "cleaned": 0,
            "archived": 0,
            "errors": 0,
            "skipped": 0
        }
        
        if clean_tasks:
            task_stats = self.cleaners["tasks"].clean(
                policy=policy, max_age_days=max_age_days, 
                archive=archive, archive_dir=archive_dir, **kwargs
            )
            results["details"]["tasks"] = task_stats
            for k, v in task_stats.items():
                total_stats[k] += v
        
        if clean_data:
            data_stats = self.cleaners["data"].clean(
                policy=policy, max_age_days=max_age_days,
                archive=archive, archive_dir=archive_dir, **kwargs
            )
            results["details"]["data"] = data_stats
            for k, v in data_stats.items():
                total_stats[k] += v
        
        if clean_files:
            file_stats = self.cleaners["files"].clean(
                policy=policy, max_age_days=max_age_days,
                archive=archive, archive_dir=archive_dir, **kwargs
            )
            results["details"]["files"] = file_stats
            for k, v in file_stats.items():
                total_stats[k] += v
        
        if clean_logs:
            log_stats = self.cleaners["logs"].clean(
                policy=policy, max_age_days=max_age_days,
                archive=archive, archive_dir=archive_dir, **kwargs
            )
            results["details"]["logs"] = log_stats
            for k, v in log_stats.items():
                total_stats[k] += v
        
        results["summary"] = total_stats
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result=total_stats,
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        # 保存清理日志
        self._save_cleanup_log(results)
        
        return results
    
    def clean_expired_tasks(self, max_age_days: int = 30, **kwargs) -> Dict[str, Any]:
        """清理过期任务"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="cleanup",
            action="clean_expired_tasks",
            params={"max_age_days": max_age_days}
        )
        
        result = self.cleaners["tasks"].clean(
            policy=CleanupPolicy.EXPIRED_ONLY,
            max_age_days=max_age_days,
            **kwargs
        )
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result=result,
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return result
        """清理过期任务"""
        return self.cleaners["tasks"].clean(
            policy=CleanupPolicy.EXPIRED_ONLY,
            max_age_days=max_age_days,
            **kwargs
        )
    
    def archive_completed_tasks(self, archive_dir: str = "./data/archives") -> Dict[str, Any]:
        """归档已完成任务"""
        return self.cleaners["tasks"].clean(
            policy=CleanupPolicy.ARCHIVE_FIRST,
            max_age_days=0,
            archive=True,
            archive_dir=archive_dir
        )
    
    def clean_temp_files(self, **kwargs) -> Dict[str, Any]:
        """清理临时文件"""
        return self.cleaners["files"].clean(
            policy=CleanupPolicy.ALL,
            **kwargs
        )
    
    def clean_invalid_logs(self, max_age_days: int = 7, **kwargs) -> Dict[str, Any]:
        """清理无效日志"""
        return self.cleaners["logs"].clean(
            policy=CleanupPolicy.EXPIRED_ONLY,
            max_age_days=max_age_days,
            **kwargs
        )
    
    def _save_cleanup_log(self, results: Dict[str, Any]):
        """保存清理日志"""
        log_dir = self.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"cleanup_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 读取现有日志
        existing = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        
        existing.append(results)
        
        # 写入日志
        with open(log_file, 'w') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    
    def get_cleanup_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取清理历史"""
        log_dir = self.data_dir / "logs"
        if not log_dir.exists():
            return []
        
        history = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for log_file in log_dir.glob("cleanup_*.json"):
            try:
                with open(log_file, 'r') as f:
                    entries = json.load(f)
                    for entry in entries:
                        entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                        if entry_time >= cutoff:
                            history.append(entry)
            except Exception as e:
                logger.error(f"读取清理日志失败: {log_file}, {e}")
        
        return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)


# 全局清理器实例
_cleaner: Optional[AutoCleaner] = None


def get_cleaner(data_dir: str = "./data") -> AutoCleaner:
    """获取全局清理器实例"""
    global _cleaner
    if _cleaner is None:
        _cleaner = AutoCleaner(data_dir)
    return _cleaner
