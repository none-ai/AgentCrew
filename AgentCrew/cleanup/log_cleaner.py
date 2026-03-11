"""
日志清理器
自动清理无效日志、过期日志
"""
import gzip
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from .cleaner import BaseCleaner, CleanupPolicy

logger = logging.getLogger(__name__)


class LogItem:
    """日志清理项"""
    
    def __init__(self, path: Path):
        self.path = path
        self.id = str(path)
    
    @property
    def created_at(self) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(self.path.stat().st_ctime)
        except Exception:
            return None
    
    @property
    def modified_at(self) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(self.path.stat().st_mtime)
        except Exception:
            return None
    
    def is_expired(self, days: int) -> bool:
        """判断日志是否过期"""
        if days <= 0:
            return False
        
        ref_time = self.modified_at or self.created_at
        if ref_time is None:
            return False
        
        return (datetime.now() - ref_time).days > days
    
    def is_invalid(self) -> bool:
        """判断日志是否无效（空文件、损坏）"""
        try:
            # 检查文件大小
            if self.path.stat().st_size == 0:
                return True
            
            # 尝试读取日志文件检查是否损坏
            if self.path.suffix == ".gz":
                with gzip.open(self.path, 'rt') as f:
                    f.read(1024)  # 尝试读取1KB
            else:
                with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.read(1024)  # 尝试读取1KB
            
            return False
        except Exception as e:
            logger.debug(f"日志文件可能损坏: {self.path}, {e}")
            return True
    
    def cleanup(self) -> bool:
        """删除日志"""
        try:
            self.path.unlink()
            return True
        except Exception as e:
            logger.error(f"删除日志失败: {self.path}, {e}")
            return False
    
    def archive(self, archive_path: str) -> bool:
        """归档日志"""
        try:
            archive_dir = Path(archive_path)
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            dest = archive_dir / self.path.name
            if dest.exists():
                # 添加时间戳
                dest = archive_dir / f"{self.path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{self.path.suffix}"
            
            self.path.rename(dest)
            return True
        except Exception as e:
            logger.error(f"归档日志失败: {self.path}, {e}")
            return False


class LogCleaner(BaseCleaner):
    """日志清理器"""
    
    def __init__(self, data_dir: str = "./data"):
        super().__init__(data_dir)
        
        self.log_dir = self.data_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件模式
        self.log_patterns = [
            "*.log",
            "*.log.*",
            "*.log.gz"
        ]
        
        # 保留的日志类型
        self.keep_logs = [
            "error.log",
            "critical.log",
            "cleanup_*.json"  # 清理日志保留
        ]
        
        # 日志保留天数
        self.default_expiry_days = 30
    
    def scan(self, include_archived: bool = True) -> List[LogItem]:
        """扫描所有日志"""
        items = []
        
        if not self.log_dir.exists():
            return items
        
        # 扫描日志文件
        for pattern in self.log_patterns:
            for log_file in self.log_dir.rglob(pattern):
                if log_file.is_file():
                    # 检查是否应该保留
                    should_keep = False
                    for keep_pattern in self.keep_logs:
                        if keep_pattern.replace("*", "") in log_file.name:
                            # 保留 error 和 critical 日志
                            if "error" in log_file.name.lower() or "critical" in log_file.name.lower():
                                should_keep = True
                            # cleanup 日志
                            if "cleanup" in log_file.name:
                                should_keep = True
                    
                    if not should_keep:
                        items.append(LogItem(log_file))
        
        # 扫描其他位置的日志
        for log_file in self.data_dir.glob("*.log"):
            if log_file.is_file():
                items.append(LogItem(log_file))
        
        return items
    
    def should_clean(self, item: LogItem, max_age_days: int = 30, **kwargs) -> bool:
        """判断日志是否应该清理"""
        # 检查是否过期
        if not item.is_expired(max_age_days):
            return False
        
        # 检查是否无效
        if item.is_invalid():
            return True
        
        return True
    
    def clean_item(self, item: LogItem, **kwargs) -> bool:
        """清理单个日志"""
        return item.cleanup()
    
    def clean_invalid_logs(self) -> Dict[str, Any]:
        """清理无效日志"""
        items = self.scan()
        
        cleaned = 0
        errors = 0
        
        for item in items:
            if item.is_invalid():
                try:
                    if item.cleanup():
                        cleaned += 1
                    else:
                        errors += 1
                except Exception as e:
                    logger.error(f"清理无效日志失败: {item.path}, {e}")
                    errors += 1
        
        return {
            "cleaned": cleaned,
            "errors": errors
        }
    
    def compress_old_logs(self, max_age_days: int = 7) -> int:
        """压缩旧日志"""
        compressed = 0
        
        for log_file in self.log_dir.glob("*.log"):
            if log_file.is_file():
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if (datetime.now() - mtime).days > max_age_days:
                    # 压缩日志
                    try:
                        compressed_file = Path(str(log_file) + ".gz")
                        
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                f_out.writelines(f_in)
                        
                        log_file.unlink()
                        compressed += 1
                        
                        logger.info(f"压缩日志: {log_file.name} -> {compressed_file.name}")
                    except Exception as e:
                        logger.error(f"压缩日志失败: {log_file}, {e}")
        
        return compressed
    
    def analyze_logs(self) -> Dict[str, Any]:
        """分析日志文件"""
        items = self.scan()
        
        stats = {
            "total_logs": len(items),
            "total_size_bytes": 0,
            "by_level": {
                "error": 0,
                "warning": 0,
                "info": 0,
                "debug": 0
            },
            "oldest_log": None,
            "newest_log": None,
            "invalid_logs": 0
        }
        
        oldest_time = None
        newest_time = None
        
        for item in items:
            try:
                stats["total_size_bytes"] += item.path.stat().st_size
            except Exception:
                pass
            
            ref_time = item.modified_at
            if ref_time:
                if oldest_time is None or ref_time < oldest_time:
                    oldest_time = ref_time
                if newest_time is None or ref_time > newest_time:
                    newest_time = ref_time
            
            if item.is_invalid():
                stats["invalid_logs"] += 1
            
            # 简单分析日志级别
            try:
                with open(item.path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = [f.readline() for _ in range(10)]
                    
                    for line in first_lines:
                        if "ERROR" in line.upper():
                            stats["by_level"]["error"] += 1
                            break
                        elif "WARN" in line.upper():
                            stats["by_level"]["warning"] += 1
                            break
                        elif "INFO" in line.upper():
                            stats["by_level"]["info"] += 1
                            break
                        elif "DEBUG" in line.upper():
                            stats["by_level"]["debug"] += 1
                            break
            except Exception:
                pass
        
        stats["oldest_log"] = oldest_time.isoformat() if oldest_time else None
        stats["newest_log"] = newest_time.isoformat() if newest_time else None
        
        return stats
    
    def get_log_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取日志摘要"""
        summary = {
            "period_days": days,
            "logs_created": 0,
            "logs_modified": 0,
            "total_size_bytes": 0
        }
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for log_file in self.log_dir.rglob("*.log*"):
            if log_file.is_file():
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    ctime = datetime.fromtimestamp(log_file.stat().st_ctime)
                    
                    if mtime >= cutoff:
                        summary["logs_modified"] += 1
                    
                    if ctime >= cutoff:
                        summary["logs_created"] += 1
                    
                    summary["total_size_bytes"] += log_file.stat().st_size
                except Exception:
                    pass
        
        return summary
