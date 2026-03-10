"""
数据清理器
自动清理过期数据、无效缓存
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from .cleaner import BaseCleaner, CleanupPolicy

logger = logging.getLogger(__name__)


class DataItem:
    """数据清理项"""
    
    def __init__(self, key: str, data: Any, saved_at: Optional[datetime] = None):
        self.id = key
        self.key = key
        self.data = data
        self._saved_at = saved_at
        self._modified_at = saved_at
    
    @property
    def created_at(self) -> Optional[datetime]:
        return self._saved_at
    
    @property
    def modified_at(self) -> Optional[datetime]:
        return self._modified_at
    
    def is_expired(self, days: int) -> bool:
        """判断数据是否过期"""
        if days <= 0:
            return False
        
        if self._saved_at is None:
            return False
        
        return (datetime.now() - self._saved_at).days > days
    
    def cleanup(self) -> bool:
        """删除数据"""
        return True
    
    def archive(self, archive_path: str) -> bool:
        """归档数据"""
        try:
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "key": self.key,
                    "data": self.data,
                    "saved_at": self._saved_at.isoformat() if self._saved_at else None
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"归档数据失败: {self.key}, {e}")
            return False


class DataCleaner(BaseCleaner):
    """数据清理器"""
    
    def __init__(self, data_dir: str = "./data"):
        super().__init__(data_dir)
        self.state_dir = self.data_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据保留策略
        self.keep_patterns = [
            "config",
            "settings",
            "user_preferences",
            "system_",
            ".protected"
        ]
        
        # 缓存过期时间（天）
        self.cache_expiry_days = 7
    
    def scan(self, include_cache: bool = True) -> List[DataItem]:
        """扫描所有可清理数据"""
        items = []
        
        # 扫描 state 目录
        if self.state_dir.exists():
            for state_file in self.state_dir.glob("*.json"):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        wrapper = json.load(f)
                    
                    saved_at = None
                    if "_saved_at" in wrapper and wrapper["_saved_at"]:
                        saved_at = datetime.fromisoformat(wrapper["_saved_at"])
                    
                    items.append(DataItem(
                        key=wrapper.get("key", state_file.stem),
                        data=wrapper.get("data"),
                        saved_at=saved_at
                    ))
                except Exception as e:
                    logger.warning(f"读取状态文件失败: {state_file}, {e}")
        
        # 扫描缓存目录
        if include_cache and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("**/*"):
                if cache_file.is_file():
                    try:
                        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                        relative_path = cache_file.relative_to(self.cache_dir)
                        
                        items.append(DataItem(
                            key=str(relative_path),
                            data=None,
                            saved_at=mtime
                        ))
                    except Exception as e:
                        logger.warning(f"处理缓存文件失败: {cache_file}, {e}")
        
        return items
    
    def should_clean(self, item: DataItem, max_age_days: int = 30, **kwargs) -> bool:
        """判断数据是否应该清理"""
        # 检查是否应该保留
        for pattern in self.keep_patterns:
            if item.key.startswith(pattern) or pattern in item.key:
                return False
        
        # 检查缓存
        if "cache" in item.key.lower():
            return item.is_expired(self.cache_expiry_days)
        
        return item.is_expired(max_age_days)
    
    def clean_item(self, item: DataItem, **kwargs) -> bool:
        """清理单个数据项"""
        try:
            # 尝试删除 state 文件
            state_file = self.state_dir / f"{item.key}.json"
            if state_file.exists():
                state_file.unlink()
            
            # 尝试删除缓存文件
            cache_file = self.cache_dir / item.key
            if cache_file.exists():
                if cache_file.is_file():
                    cache_file.unlink()
                else:
                    # 是目录，递归删除
                    import shutil
                    shutil.rmtree(cache_file)
            
            # 尝试清理 SQLite 数据库中的旧数据
            self._clean_sqlite_old_data(item.key)
            
            return True
        except Exception as e:
            logger.error(f"清理数据失败: {item.key}, {e}")
            return False
    
    def _clean_sqlite_old_data(self, key_prefix: str):
        """清理 SQLite 数据库中的旧数据"""
        db_file = self.data_dir / "state.db"
        if not db_file.exists():
            return
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_store'")
            if not cursor.fetchone():
                conn.close()
                return
            
            # 删除过期数据（保留近30天）
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute("DELETE FROM state_store WHERE saved_at < ?", (cutoff,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"从 SQLite 清理了 {deleted} 条过期记录")
                
        except Exception as e:
            logger.warning(f"清理 SQLite 数据失败: {e}")
    
    def clean(self, **kwargs) -> Dict[str, Any]:
        """执行数据清理"""
        return super().clean(**kwargs)
    
    def get_data_stats(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        items = self.scan()
        
        stats = {
            "total": len(items),
            "by_type": {
                "state": 0,
                "cache": 0
            },
            "total_size_bytes": 0,
            "oldest_item": None
        }
        
        oldest_time = None
        
        for item in items:
            if "cache" in item.key.lower():
                stats["by_type"]["cache"] += 1
            else:
                stats["by_type"]["state"] += 1
            
            if item.created_at:
                if oldest_time is None or item.created_at < oldest_time:
                    oldest_time = item.created_at
        
        stats["oldest_item"] = oldest_time.isoformat() if oldest_time else None
        
        # 计算存储大小
        for d in [self.state_dir, self.cache_dir]:
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        stats["total_size_bytes"] += f.stat().st_size
        
        return stats
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """清理缓存"""
        count = 0
        
        if not self.cache_dir.exists():
            return 0
        
        if pattern:
            for cache_file in self.cache_dir.rglob(pattern):
                if cache_file.is_file():
                    cache_file.unlink()
                    count += 1
        else:
            for cache_file in self.cache_dir.rglob("*"):
                if cache_file.is_file():
                    cache_file.unlink()
                    count += 1
                elif cache_file.is_dir():
                    import shutil
                    shutil.rmtree(cache_file)
                    count += 1
        
        logger.info(f"清理了 {count} 个缓存项")
        return count
