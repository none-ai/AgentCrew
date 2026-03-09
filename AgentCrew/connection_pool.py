"""
连接池管理
支持多种连接类型：HTTP、数据库、WebSocket等
"""
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from collections import deque
from contextlib import contextmanager
from datetime import datetime
import json


class Connection:
    """连接基类"""
    
    def __init__(self, conn_id: str, pool: 'ConnectionPool'):
        self.conn_id = conn_id
        self.pool = pool
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.in_use = False
        self.is_valid = True
        self.metadata: Dict = {}
    
    def ping(self) -> bool:
        """检查连接是否有效"""
        raise NotImplementedError
    
    def close(self):
        """关闭连接"""
        raise NotImplementedError
    
    def reset(self):
        """重置连接"""
        raise NotImplementedError
    
    def get_age(self) -> float:
        """获取连接存活时间（秒）"""
        return time.time() - self.created_at
    
    def get_idle_time(self) -> float:
        """获取空闲时间（秒）"""
        return time.time() - self.last_used_at
    
    def mark_used(self):
        """标记为已使用"""
        self.last_used_at = time.time()


class HTTPConnection(Connection):
    """HTTP连接（封装requests会话）"""
    
    def __init__(self, conn_id: str, pool: 'ConnectionPool', session=None):
        super().__init__(conn_id, pool)
        self.session = session
    
    def ping(self) -> bool:
        """检查连接是否有效"""
        try:
            if self.session:
                # 简单的健康检查
                return True
            return False
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.session = None
    
    def reset(self):
        """重置连接"""
        self.close()
        # 重新创建session的逻辑可以在这里添加


class DBConnection(Connection):
    """数据库连接"""
    
    def __init__(self, conn_id: str, pool: 'ConnectionPool', conn=None):
        super().__init__(conn_id, pool)
        self.conn = conn
    
    def ping(self) -> bool:
        """检查连接是否有效"""
        try:
            if self.conn:
                # 根据数据库类型做不同的健康检查
                return True
            return False
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
    
    def reset(self):
        """重置连接"""
        self.close()


class WSConnection(Connection):
    """WebSocket连接"""
    
    def __init__(self, conn_id: str, pool: 'ConnectionPool', ws=None):
        super().__init__(conn_id, pool)
        self.ws = ws
    
    def ping(self) -> bool:
        """检查连接是否有效"""
        try:
            if self.ws:
                return self.ws.connected
            return False
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
    
    def reset(self):
        """重置连接"""
        self.close()


class ConnectionPool:
    """连接池"""
    
    def __init__(
        self,
        name: str = "default",
        min_size: int = 2,
        max_size: int = 10,
        max_idle_time: float = 300,
        max_lifetime: float = 3600,
        validation_interval: float = 60,
        factory: Optional[Callable[[], Connection]] = None
    ):
        self.name = name
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time  # 最大空闲时间（秒）
        self.max_lifetime = max_lifetime     # 最大生命周期（秒）
        self.validation_interval = validation_interval  # 验证间隔
        
        self.factory = factory  # 连接工厂函数
        
        # 连接存储
        self._connections: deque = deque()
        self._in_use: Dict[str, Connection] = {}
        
        # 统计
        self._total_created = 0
        self._total_destroyed = 0
        self._validation_failures = 0
        
        # 锁
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        
        # 后台任务
        self._running = False
        self._maintenance_thread: Optional[threading.Thread] = None
        
        # 初始化最小连接数
        self._initialize()
    
    def _initialize(self):
        """初始化连接池，创建最小数量的连接"""
        with self._lock:
            for _ in range(self.min_size):
                conn = self._create_connection()
                if conn:
                    self._connections.append(conn)
    
    def _create_connection(self) -> Optional[Connection]:
        """创建新连接"""
        if self._total_created - self._total_destroyed >= self.max_size:
            return None
        
        try:
            if self.factory:
                conn = self.factory()
                if conn:
                    conn.pool = self
                    self._total_created += 1
                    return conn
        except Exception as e:
            print(f"创建连接失败: {e}")
        
        return None
    
    def _destroy_connection(self, conn: Connection):
        """销毁连接"""
        try:
            conn.close()
        except Exception:
            pass
        self._total_destroyed += 1
    
    def _validate_connection(self, conn: Connection) -> bool:
        """验证连接是否有效"""
        try:
            return conn.ping()
        except Exception:
            return False
    
    def _maintenance(self):
        """后台维护任务"""
        while self._running:
            time.sleep(self.validation_interval)
            
            with self._lock:
                # 1. 检查空闲连接是否过期
                to_remove = []
                for conn in self._connections:
                    if conn.get_idle_time() > self.max_idle_time:
                        to_remove.append(conn)
                
                for conn in to_remove:
                    self._connections.remove(conn)
                    self._destroy_connection(conn)
                
                # 2. 检查连接是否有效
                for conn in list(self._connections):
                    if not self._validate_connection(conn):
                        self._connections.remove(conn)
                        self._destroy_connection(conn)
                        self._validation_failures += 1
                
                # 3. 补充最小连接数
                while (len(self._connections) + len(self._in_use) < self.min_size 
                       and self._total_created - self._total_destroyed < self.max_size):
                    conn = self._create_connection()
                    if conn:
                        self._connections.append(conn)
    
    def start_maintenance(self):
        """启动后台维护"""
        if not self._running:
            self._running = True
            self._maintenance_thread = threading.Thread(target=self._maintenance, daemon=True)
            self._maintenance_thread.start()
    
    def stop_maintenance(self):
        """停止后台维护"""
        self._running = False
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=5)
    
    @contextmanager
    def get_connection(self, timeout: float = 30):
        """获取连接（上下文管理器）"""
        conn = None
        acquired = False
        
        try:
            with self._lock:
                # 尝试从池中获取
                while self._connections:
                    conn = self._connections.popleft()
                    
                    # 验证连接
                    if self._validate_connection(conn):
                        break
                    else:
                        self._destroy_connection(conn)
                        conn = None
                
                # 如果池中没有，创建新连接
                if conn is None:
                    conn = self._create_connection()
                
                if conn is None:
                    raise RuntimeError("无法获取连接：池已满且无法创建新连接")
                
                conn.in_use = True
                conn.mark_used()
                acquired = True
            
            yield conn
            
        finally:
            if acquired and conn:
                with self._lock:
                    conn.in_use = False
                    
                    # 如果连接仍然有效且池未满，归还池中
                    if (self._validate_connection(conn) and 
                        len(self._connections) + len(self._in_use) < self.max_size):
                        self._connections.append(conn)
                    else:
                        self._destroy_connection(conn)
    
    def acquire(self, timeout: float = 30) -> Optional[Connection]:
        """手动获取连接"""
        try:
            with self.get_connection(timeout) as conn:
                return conn
        except Exception:
            return None
    
    def release(self, conn: Connection):
        """手动释放连接"""
        with self._lock:
            if conn.in_use:
                conn.in_use = False
                if self._validate_connection(conn):
                    self._connections.append(conn)
                else:
                    self._destroy_connection(conn)
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            while self._connections:
                conn = self._connections.popleft()
                self._destroy_connection(conn)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self.name,
                "min_size": self.min_size,
                "max_size": self.max_size,
                "idle_count": len(self._connections),
                "in_use_count": len(self._in_use),
                "total_created": self._total_created,
                "total_destroyed": self._total_destroyed,
                "validation_failures": self._validation_failures,
                "running": self._running
            }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
        self.stop_maintenance()


class PoolManager:
    """连接池管理器"""
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.Lock()
    
    def create_pool(
        self,
        name: str,
        min_size: int = 2,
        max_size: int = 10,
        max_idle_time: float = 300,
        max_lifetime: float = 3600,
        factory: Optional[Callable[[], Connection]] = None
    ) -> ConnectionPool:
        """创建连接池"""
        with self._lock:
            if name in self._pools:
                return self._pools[name]
            
            pool = ConnectionPool(
                name=name,
                min_size=min_size,
                max_size=max_size,
                max_idle_time=max_idle_time,
                max_lifetime=max_lifetime,
                factory=factory
            )
            
            self._pools[name] = pool
            return pool
    
    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """获取连接池"""
        return self._pools.get(name)
    
    def remove_pool(self, name: str) -> bool:
        """移除连接池"""
        with self._lock:
            if name not in self._pools:
                return False
            
            pool = self._pools[name]
            pool.close_all()
            pool.stop_maintenance()
            del self._pools[name]
            return True
    
    def get_all_stats(self) -> Dict:
        """获取所有连接池统计"""
        return {
            name: pool.get_stats()
            for name, pool in self._pools.items()
        }
    
    def close_all(self):
        """关闭所有连接池"""
        with self._lock:
            for pool in self._pools.values():
                pool.close_all()
                pool.stop_maintenance()
            self._pools.clear()


# 全局连接池管理器
_manager = PoolManager()

def get_pool_manager() -> PoolManager:
    """获取全局连接池管理器"""
    return _manager

def create_pool(
    name: str,
    min_size: int = 2,
    max_size: int = 10,
    max_idle_time: float = 300,
    max_lifetime: float = 3600,
    factory: Optional[Callable[[], Connection]] = None
) -> ConnectionPool:
    """创建连接池（便捷函数）"""
    return _manager.create_pool(name, min_size, max_size, max_idle_time, max_lifetime, factory)

def get_pool(name: str) -> Optional[ConnectionPool]:
    """获取连接池（便捷函数）"""
    return _manager.get_pool(name)


# 使用示例
if __name__ == "__main__":
    # 创建HTTP连接池示例
    import requests
    
    def http_factory():
        session = requests.Session()
        return HTTPConnection(f"http-{time.time()}", None, session)
    
    pool = create_pool("http_pool", factory=http_factory)
    pool.start_maintenance()
    
    with pool.get_connection() as conn:
        print(f"获取连接: {conn.conn_id}")
        print(f"连接有效: {conn.ping()}")
    
    print(pool.get_stats())
    
    _manager.close_all()
