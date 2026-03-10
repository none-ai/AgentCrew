"""
文件清理器
自动清理临时文件、无效文件
"""
import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from .cleaner import BaseCleaner, CleanupPolicy

logger = logging.getLogger(__name__)


class FileItem:
    """文件清理项"""
    
    def __init__(self, path: Path):
        self.path = path
        self.id = str(path)
        self._stat = None
    
    @property
    def created_at(self) -> Optional[datetime]:
        try:
            # Linux 上使用 st_ctime 作为创建时间
            return datetime.fromtimestamp(self.path.stat().st_ctime)
        except:
            return None
    
    @property
    def modified_at(self) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(self.path.stat().st_mtime)
        except:
            return None
    
    def is_expired(self, days: int) -> bool:
        """判断文件是否过期"""
        if days <= 0:
            return False
        
        ref_time = self.modified_at or self.created_at
        if ref_time is None:
            return False
        
        return (datetime.now() - ref_time).days > days
    
    def cleanup(self) -> bool:
        """删除文件"""
        try:
            if self.path.is_file():
                self.path.unlink()
            elif self.path.is_dir():
                shutil.rmtree(self.path)
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {self.path}, {e}")
            return False
    
    def archive(self, archive_path: str) -> bool:
        """归档文件"""
        try:
            archive_dir = Path(archive_path).parent
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            dest = archive_dir / self.path.name
            shutil.move(str(self.path), str(dest))
            return True
        except Exception as e:
            logger.error(f"归档文件失败: {self.path}, {e}")
            return False


class FileCleaner(BaseCleaner):
    """文件清理器"""
    
    def __init__(self, data_dir: str = "./data"):
        super().__init__(data_dir)
        
        # 临时文件模式
        self.temp_patterns = [
            "*.tmp",
            "*.temp",
            "*.bak",
            "*.backup",
            "*~",
            ".DS_Store",
            "Thumbs.db",
            "*.pyc",
            "__pycache__",
            "*.log.tmp"
        ]
        
        # 临时目录
        self.temp_dirs = [
            "tmp",
            "temp",
            "cache",
            ".cache"
        ]
        
        # 保留的目录
        self.keep_dirs = [
            "logs",
            "archives",
            "data"
        ]
    
    def scan(self, include_temp: bool = True) -> List[FileItem]:
        """扫描所有可清理文件"""
        items = []
        
        # 扫描临时文件模式
        if include_temp:
            for pattern in self.temp_patterns:
                for file_path in self.data_dir.rglob(pattern):
                    if file_path.is_file():
                        items.append(FileItem(file_path))
        
        # 扫描临时目录
        for temp_dir in self.temp_dirs:
            temp_path = self.data_dir / temp_dir
            if temp_path.exists() and temp_path.is_dir():
                # 检查是否应该保留
                if temp_dir not in self.keep_dirs:
                    items.append(FileItem(temp_path))
        
        # 扫描大的旧文件
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size > large_file_threshold:
                        # 检查是否过期
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if (datetime.now() - mtime).days > 90:
                            items.append(FileItem(file_path))
                except:
                    pass
        
        return items
    
    def should_clean(self, item: FileItem, max_age_days: int = 7, **kwargs) -> bool:
        """判断文件是否应该清理"""
        # 保留关键目录
        for keep_dir in self.keep_dirs:
            if keep_dir in item.path.parts:
                return False
        
        # 临时文件总是可以清理
        filename = item.path.name
        for pattern in self.temp_patterns:
            if pattern.startswith("*."):
                ext = pattern[1:]
                if filename.endswith(ext):
                    return True
            elif filename == pattern or filename.startswith(pattern[:-1]):
                return True
        
        # 其他文件按时间清理
        return item.is_expired(max_age_days)
    
    def clean_item(self, item: FileItem, **kwargs) -> bool:
        """清理单个文件"""
        return item.cleanup()
    
    def scan_large_files(self, min_size_mb: int = 10) -> List[Dict[str, Any]]:
        """扫描大文件"""
        large_files = []
        
        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    
                    if size_mb >= min_size_mb:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        large_files.append({
                            "path": str(file_path.relative_to(self.data_dir)),
                            "size_mb": round(size_mb, 2),
                            "modified": mtime.isoformat(),
                            "age_days": (datetime.now() - mtime).days
                        })
                except:
                    pass
        
        return sorted(large_files, key=lambda x: x["size_mb"], reverse=True)
    
    def get_file_stats(self) -> Dict[str, Any]:
        """获取文件统计"""
        items = self.scan()
        
        stats = {
            "total_files": len(items),
            "by_type": {},
            "total_size_bytes": 0
        }
        
        for item in items:
            ext = item.path.suffix or "no_extension"
            stats["by_type"][ext] = stats["by_type"].get(ext, 0) + 1
            
            try:
                stats["total_size_bytes"] += item.path.stat().st_size
            except:
                pass
        
        return stats
