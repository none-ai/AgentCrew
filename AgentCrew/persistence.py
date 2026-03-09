"""
状态持久化
支持多种存储后端：JSON文件、SQLite、内存
"""
import os
import json
import time
import threading
import sqlite3
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
import shutil


class StorageBackend(ABC):
    """存储后端基类"""
    
    @abstractmethod
    def save(self, key: str, data: Any) -> bool:
        """保存数据"""
        pass
    
    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """加载数据"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除数据"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有数据"""
        pass


class JSONFileBackend(StorageBackend):
    """JSON文件存储后端"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
    
    def _get_file_path(self, key: str) -> Path:
        """获取文件路径"""
        # 将key转换为安全的文件名
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_key}.json"
    
    def save(self, key: str, data: Any) -> bool:
        """保存数据到JSON文件"""
        with self._lock:
            try:
                file_path = self._get_file_path(key)
                
                # 添加元数据
                wrapper = {
                    "_data": data,
                    "_key": key,
                    "_saved_at": datetime.now().isoformat(),
                    "_version": 1
                }
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(wrapper, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存JSON失败: {e}")
                return False
    
    def load(self, key: str) -> Optional[Any]:
        """从JSON文件加载数据"""
        with self._lock:
            try:
                file_path = self._get_file_path(key)
                if not file_path.exists():
                    return None
                
                with open(file_path, "r", encoding="utf-8") as f:
                    wrapper = json.load(f)
                
                return wrapper.get("_data")
            except Exception as e:
                print(f"加载JSON失败: {e}")
                return None
    
    def delete(self, key: str) -> bool:
        """删除JSON文件"""
        with self._lock:
            try:
                file_path = self._get_file_path(key)
                if file_path.exists():
                    file_path.unlink()
                return True
            except Exception as e:
                print(f"删除JSON失败: {e}")
                return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._get_file_path(key).exists()
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有JSON文件对应的键"""
        with self._lock:
            keys = []
            for file_path in self.base_path.glob("*.json"):
                key = file_path.stem
                if prefix == "" or key.startswith(prefix):
                    keys.append(key)
            return keys
    
    def clear(self) -> bool:
        """清空所有JSON文件"""
        with self._lock:
            try:
                for file_path in self.base_path.glob("*.json"):
                    file_path.unlink()
                return True
            except Exception as e:
                print(f"清空JSON失败: {e}")
                return False


class SQLiteBackend(StorageBackend):
    """SQLite存储后端"""
    
    def __init__(self, db_path: str = "./data/state.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    saved_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def save(self, key: str, data: Any) -> bool:
        """保存数据到SQLite"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 将数据序列化为JSON
                value = json.dumps(data, ensure_ascii=False)
                saved_at = datetime.now().isoformat()
                
                cursor.execute(
                    "INSERT OR REPLACE INTO state_store (key, value, saved_at, version) VALUES (?, ?, ?, ?)",
                    (key, value, saved_at, 1)
                )
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"保存SQLite失败: {e}")
                return False
    
    def load(self, key: str) -> Optional[Any]:
        """从SQLite加载数据"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT value FROM state_store WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                conn.close()
                
                if row:
                    return json.loads(row[0])
                return None
            except Exception as e:
                print(f"加载SQLite失败: {e}")
                return None
    
    def delete(self, key: str) -> bool:
        """从SQLite删除数据"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM state_store WHERE key = ?", (key,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"删除SQLite失败: {e}")
                return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM state_store WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None
                conn.close()
                return exists
            except Exception:
                return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if prefix:
                    cursor.execute("SELECT key FROM state_store WHERE key LIKE ?", (f"{prefix}%",))
                else:
                    cursor.execute("SELECT key FROM state_store")
                
                keys = [row[0] for row in cursor.fetchall()]
                conn.close()
                return keys
            except Exception:
                return []
    
    def clear(self) -> bool:
        """清空所有数据"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM state_store")
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"清空SQLite失败: {e}")
                return False


class MemoryBackend(StorageBackend):
    """内存存储后端（用于测试或临时存储）"""
    
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def save(self, key: str, data: Any) -> bool:
        """保存到内存"""
        with self._lock:
            self._store[key] = data
            return True
    
    def load(self, key: str) -> Optional[Any]:
        """从内存加载"""
        with self._lock:
            return self._store.get(key)
    
    def delete(self, key: str) -> bool:
        """从内存删除"""
        with self._lock:
            if key in self._store:
                del self._store[key]
            return True
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._store
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        with self._lock:
            if prefix:
                return [k for k in self._store.keys() if k.startswith(prefix)]
            return list(self._store.keys())
    
    def clear(self) -> bool:
        """清空内存"""
        with self._lock:
            self._store.clear()
            return True


class StateManager:
    """状态管理器"""
    
    def __init__(self, backend: Optional[StorageBackend] = None):
        self.backend = backend or MemoryBackend()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
    
    def save_state(self, key: str, data: Any) -> bool:
        """保存状态"""
        with self._lock:
            result = self.backend.save(key, data)
            
            if result and key in self._subscribers:
                for callback in self._subscribers[key]:
                    try:
                        callback("save", data)
                    except Exception as e:
                        print(f"订阅者回调失败: {e}")
            
            return result
    
    def load_state(self, key: str) -> Optional[Any]:
        """加载状态"""
        with self._lock:
            return self.backend.load(key)
    
    def delete_state(self, key: str) -> bool:
        """删除状态"""
        with self._lock:
            return self.backend.delete(key)
    
    def state_exists(self, key: str) -> bool:
        """检查状态是否存在"""
        return self.backend.exists(key)
    
    def list_states(self, prefix: str = "") -> List[str]:
        """列出所有状态"""
        return self.backend.list_keys(prefix)
    
    def subscribe(self, key: str, callback: Callable):
        """订阅状态变化"""
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable):
        """取消订阅"""
        with self._lock:
            if key in self._subscribers:
                self._subscribers[key].remove(callback)
    
    def clear_all(self) -> bool:
        """清空所有状态"""
        with self._lock:
            return self.backend.clear()
    
    def export_all(self) -> Dict[str, Any]:
        """导出所有状态"""
        with self._lock:
            keys = self.backend.list_keys()
            return {key: self.backend.load(key) for key in keys}
    
    def import_states(self, states: Dict[str, Any]) -> bool:
        """批量导入状态"""
        with self._lock:
            try:
                for key, value in states.items():
                    self.backend.save(key, value)
                return True
            except Exception:
                return False


class TaskPersistenceMixin:
    """任务持久化混入类"""
    
    def __init__(self):
        self._state_manager: Optional[StateManager] = None
        self._auto_save = True
        self._save_interval = 30  # 秒
    
    def init_persistence(self, backend: Optional[StorageBackend] = None, auto_save: bool = True):
        """初始化持久化"""
        self._state_manager = StateManager(backend)
        self._auto_save = auto_save
        
        if auto_save:
            self._start_auto_save()
    
    def _start_auto_save(self):
        """启动自动保存"""
        def auto_save_loop():
            while self._auto_save:
                time.sleep(self._save_interval)
                try:
                    self._do_auto_save()
                except Exception as e:
                    print(f"自动保存失败: {e}")
        
        thread = threading.Thread(target=auto_save_loop, daemon=True)
        thread.start()
    
    def _do_auto_save(self):
        """执行自动保存"""
        # 子类实现
        pass
    
    def save_state(self, key: str, data: Any) -> bool:
        """保存状态"""
        if self._state_manager:
            return self._state_manager.save_state(key, data)
        return False
    
    def load_state(self, key: str) -> Optional[Any]:
        """加载状态"""
        if self._state_manager:
            return self._state_manager.load_state(key)
        return None
    
    def subscribe(self, key: str, callback: Callable):
        """订阅状态变化"""
        if self._state_manager:
            self._state_manager.subscribe(key, callback)


# 便捷函数
_default_manager: Optional[StateManager] = None

def get_state_manager(backend: Optional[StorageBackend] = None) -> StateManager:
    """获取全局状态管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = StateManager(backend)
    return _default_manager

def save_tasks_state(key: str, tasks: Any) -> bool:
    """保存任务状态"""
    return get_state_manager().save_state(key, tasks)

def load_tasks_state(key: str) -> Optional[Any]:
    """加载任务状态"""
    return get_state_manager().load_state(key)


# 使用示例
if __name__ == "__main__":
    # 测试JSON文件后端
    print("=== 测试 JSON 文件后端 ===")
    json_backend = JSONFileBackend("./data/test_json")
    state_manager = StateManager(json_backend)
    
    state_manager.save_state("task-1", {"title": "测试任务", "status": "completed"})
    state_manager.save_state("task-2", {"title": "测试任务2", "status": "pending"})
    
    print(f"任务1: {state_manager.load_state('task-1')}")
    print(f"所有键: {state_manager.list_states()}")
    
    # 测试SQLite后端
    print("\n=== 测试 SQLite 后端 ===")
    sqlite_backend = SQLiteBackend("./data/test_state.db")
    state_manager2 = StateManager(sqlite_backend)
    
    state_manager2.save_state("config", {"max_workers": 4, "timeout": 30})
    print(f"配置: {state_manager2.load_state('config')}")
    
    # 清理测试文件
    import shutil
    shutil.rmtree("./data/test_json", ignore_errors=True)
    Path("./data/test_state.db").unlink(missing_ok=True)
