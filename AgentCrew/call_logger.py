"""
AgentCrew 调用记录器 (SQLite版本)
用于记录每次 AgentCrew 调用/操作的详细信息，便于评估和分析
"""
import sqlite3
import uuid
import os
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from enum import Enum


class CallStatus(Enum):
    """调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"


class CallLogger:
    """调用记录器 - 使用SQLite数据库"""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # 默认路径为 workspace-taizi 下的 data 目录
        if db_path is None:
            db_path = "/home/stlin-claw/.openclaw/workspace-taizi/data/call_logs/calls.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 回调函数
        self._callbacks: List[Callable] = []
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建调用记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                params TEXT,
                result TEXT,
                status TEXT NOT NULL,
                duration_ms REAL,
                summary TEXT,
                metadata TEXT,
                tokens_used INTEGER DEFAULT 0,
                tokens_prompt INTEGER DEFAULT 0,
                tokens_completion INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON calls(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON calls(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON calls(status)")
        
        # 创建每日统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_calls INTEGER,
                success_count INTEGER,
                failed_count INTEGER,
                avg_duration_ms REAL,
                total_tokens INTEGER,
                total_cost_usd REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))
    
    def register_callback(self, callback: Callable):
        """注册回调函数"""
        self._callbacks.append(callback)
    
    def log_call(
        self,
        source: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        status: CallStatus = CallStatus.PENDING,
        duration_ms: float = 0,
        metadata: Optional[Dict[str, Any]] = None,
        call_id: Optional[str] = None,
        tokens_used: int = 0,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        cost_usd: float = 0
    ) -> str:
        """记录一次调用 (非阻塞)"""
        call_id = call_id or f"call-{uuid.uuid4().hex[:12]}"
        
        # 截断过大的数据
        truncated_params = self._truncate_data(params) if params else {}
        truncated_result = self._truncate_data(result) if result else {}
        
        # 生成摘要
        summary = self._generate_summary(action, truncated_result, status)
        
        record = {
            "call_id": call_id,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "action": action,
            "params": truncated_params,
            "result": truncated_result,
            "status": status.value,
            "duration_ms": duration_ms,
            "summary": summary,
            "metadata": metadata or {},
            "tokens_used": tokens_used,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "cost_usd": cost_usd
        }
        
        # 异步写入数据库（非阻塞）
        thread = threading.Thread(target=self._write_record, args=(record,), daemon=True)
        thread.start()
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(record)
            except Exception as e:
                print(f"回调执行失败: {e}")
        
        return call_id
    
    def _truncate_data(self, data: Any, max_size: int = 1000) -> Any:
        """截断过大的数据"""
        if isinstance(data, dict):
            return {k: self._truncate_data(v, max_size) for k, v in data.items()}
        elif isinstance(data, list):
            return data[:10]
        elif isinstance(data, str):
            return data[:max_size] if len(data) > max_size else data
        else:
            return data
    
    def _generate_summary(self, action: str, result: Dict, status: CallStatus) -> str:
        """生成摘要"""
        if status == CallStatus.SUCCESS:
            return f"{action} 完成"
        elif status == CallStatus.FAILED:
            return f"{action} 失败"
        elif status == CallStatus.RUNNING:
            return f"{action} 执行中"
        return f"{action}"
    
    def _write_record(self, record: Dict):
        """写入数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO calls 
                (call_id, timestamp, source, action, params, result, status, duration_ms, summary, metadata, tokens_used, tokens_prompt, tokens_completion, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["call_id"],
                record["timestamp"],
                record["source"],
                record["action"],
                json.dumps(record.get("params", {})),
                json.dumps(record.get("result", {})),
                record["status"],
                record.get("duration_ms", 0),
                record.get("summary", ""),
                json.dumps(record.get("metadata", {})),
                record.get("tokens_used", 0),
                record.get("tokens_prompt", 0),
                record.get("tokens_completion", 0),
                record.get("cost_usd", 0)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"写入数据库失败: {e}")
    
    def log_call_start(
        self,
        source: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录调用开始"""
        return self.log_call(
            source=source,
            action=action,
            params=params,
            status=CallStatus.RUNNING,
            metadata=metadata
        )
    
    def log_call_end(
        self,
        call_id: str,
        result: Optional[Dict[str, Any]] = None,
        status: CallStatus = CallStatus.SUCCESS,
        duration_ms: float = 0,
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        cost_usd: float = 0
    ):
        """记录调用结束"""
        truncated_result = self._truncate_data(result) if result else {}
        summary = self._generate_summary("", truncated_result, status)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE calls 
            SET result = ?, status = ?, duration_ms = ?, summary = ?, metadata = ?, tokens_used = ?, tokens_prompt = ?, tokens_completion = ?, cost_usd = ?
            WHERE call_id = ?
        """, (
            json.dumps(truncated_result),
            status.value,
            duration_ms,
            summary,
            json.dumps(metadata or {}),
            tokens_used,
            tokens_prompt,
            tokens_completion,
            cost_usd,
            call_id
        ))
        
        conn.commit()
        conn.close()
        
        for callback in self._callbacks:
            try:
                callback({"call_id": call_id, "status": status.value})
            except Exception as e:
                print(f"回调执行失败: {e}")
    
    def get_calls(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """获取调用记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if source:
            cursor.execute("""
                SELECT call_id, timestamp, source, action, params, result, status, duration_ms, summary, metadata, tokens_used, tokens_prompt, tokens_completion, cost_usd
                FROM calls 
                WHERE source = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (source, limit, offset))
        else:
            cursor.execute("""
                SELECT call_id, timestamp, source, action, params, result, status, duration_ms, summary, metadata, tokens_used, tokens_prompt, tokens_completion, cost_usd
                FROM calls 
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "call_id": row[0],
                "timestamp": row[1],
                "source": row[2],
                "action": row[3],
                "params": json.loads(row[4]) if row[4] else {},
                "result": json.loads(row[5]) if row[5] else {},
                "status": row[6],
                "duration_ms": row[7],
                "summary": row[8],
                "metadata": json.loads(row[9]) if row[9] else {},
                "tokens_used": row[10],
                "tokens_prompt": row[11],
                "tokens_completion": row[12],
                "cost_usd": row[13]
            })
        
        return results
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                COALESCE(AVG(duration_ms), 0) as avg_duration,
                COALESCE(SUM(tokens_used), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost
            FROM calls 
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_calls": row[0] or 0,
            "success_count": row[1] or 0,
            "failed_count": row[2] or 0,
            "avg_duration_ms": row[3] or 0,
            "total_tokens": row[4] or 0,
            "total_cost_usd": row[5] or 0
        }
    
    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM calls 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def vacuum(self):
        """压缩数据库"""
        conn = self._get_connection()
        conn.execute("VACUUM")
        conn.close()


# 全局实例获取函数
_logger_instance = None
def get_logger(db_path: str = None) -> CallLogger:
    """获取日志器全局实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = CallLogger(db_path)
    return _logger_instance
