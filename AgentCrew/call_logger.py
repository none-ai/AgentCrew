"""
AgentCrew 调用记录器
用于记录每次 AgentCrew 调用/操作的详细信息，便于评估和分析
"""
import json
import uuid
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from enum import Enum


class CallStatus(Enum):
    """调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"


class CallLogger:
    """调用记录器"""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: str = "./data/call_logs"):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前日志文件
        self.current_log_file = self.log_dir / f"calls_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        # 内存缓存（用于快速查询）
        self._cache: List[Dict] = []
        self._cache_lock = threading.RLock()
        
        # 回调函数（用于实时处理）
        self._callbacks: List[Callable] = []
        
        # 统计信息
        self._stats = {
            "total_calls": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_duration_ms": 0
        }
        self._stats_lock = threading.RLock()
    
    def register_callback(self, callback: Callable):
        """注册回调函数，每次调用记录都会触发"""
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
        call_id: Optional[str] = None
    ) -> str:
        """
        记录一次调用
        
        Args:
            source: 调用来源（模块名），如 'self_evolution', 'active_executor', 'cleanup', 'memory'
            action: 调用动作，如 'execute_task', 'create_task', 'cleanup'
            params: 调用参数
            result: 执行结果
            status: 执行状态
            duration_ms: 执行耗时（毫秒）
            metadata: 额外元数据
            call_id: 调用ID（可选，不提供则自动生成）
        
        Returns:
            call_id: 生成的调用ID
        """
        call_id = call_id or f"call-{uuid.uuid4().hex[:12]}"
        
        # 截断过大的参数和结果（避免日志文件过大）
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
            "metadata": metadata or {}
        }
        
        # 写入文件
        self._write_record(record)
        
        # 写入缓存
        with self._cache_lock:
            self._cache.append(record)
            # 保留最近1000条在内存中
            if len(self._cache) > 1000:
                self._cache = self._cache[-1000:]
        
        # 更新统计
        with self._stats_lock:
            self._stats["total_calls"] += 1
            if status == CallStatus.SUCCESS:
                self._stats["success_count"] += 1
            elif status == CallStatus.FAILED:
                self._stats["failed_count"] += 1
            self._stats["total_duration_ms"] += duration_ms
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(record)
            except Exception as e:
                print(f"回调执行失败: {e}")
        
        return call_id
    
    def log_call_start(
        self,
        source: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录调用开始（便捷方法）"""
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
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录调用结束（便捷方法，用于更新之前的记录）"""
        # 读取原始记录
        original_record = self.get_call(call_id)
        
        if original_record:
            # 更新记录
            updated_record = {
                **original_record,
                "result": self._truncate_data(result) if result else {},
                "status": status.value,
                "duration_ms": duration_ms,
                "summary": self._generate_summary(
                    original_record["action"], 
                    self._truncate_data(result) if result else {}, 
                    status
                )
            }
            if metadata:
                updated_record["metadata"].update(metadata)
            
            # 覆盖写入（通过追加标记为更新）
            self._write_record(updated_record, append=False)
            
            # 更新缓存
            with self._cache_lock:
                for i, rec in enumerate(self._cache):
                    if rec.get("call_id") == call_id:
                        self._cache[i] = updated_record
                        break
        else:
            # 如果没找到原始记录，直接创建新记录
            self.log_call(
                source=original_record.get("source", "unknown") if original_record else "unknown",
                action=original_record.get("action", "unknown") if original_record else action,
                params=original_record.get("params", {}) if original_record else {},
                result=result,
                status=status,
                duration_ms=duration_ms,
                metadata=metadata
            )
    
    def _write_record(self, record: Dict, append: bool = True):
        """写入记录到文件"""
        try:
            mode = "a" if append else "w"
            with open(self.current_log_file, mode, encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"写入调用记录失败: {e}")
    
    def _truncate_data(self, data: Any, max_depth: int = 3, max_length: int = 2000) -> Any:
        """截断过大的数据"""
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    result[k] = self._truncate_data(v, max_depth - 1, max_length)
                elif isinstance(v, str) and len(v) > max_length:
                    result[k] = v[:max_length] + "...(truncated)"
                else:
                    result[k] = v
            return result
        elif isinstance(data, list):
            if len(data) > 20:
                return data[:20] + [f"...({len(data) - 20} more items)"]
            return [self._truncate_data(item, max_depth - 1, max_length) for item in data]
        elif isinstance(data, str) and len(data) > max_length:
            return data[:max_length] + "...(truncated)"
        return data
    
    def _generate_summary(self, action: str, result: Dict, status: CallStatus) -> str:
        """生成结果摘要"""
        if status == CallStatus.FAILED:
            error = result.get("error", result.get("message", "Unknown error"))
            return f"失败: {error}"
        elif status == CallStatus.PENDING or status == CallStatus.RUNNING:
            return "执行中..."
        
        # 根据动作类型生成摘要
        if action == "execute_task" or action == "run_task":
            task_id = result.get("task_id", result.get("id", "N/A"))
            return f"任务 {task_id} 执行完成"
        elif action == "create_task":
            return f"创建任务: {result.get('title', 'N/A')}"
        elif action == "cleanup":
            cleaned = result.get("cleaned_count", result.get("items_cleaned", 0))
            return f"清理完成，清理 {cleaned} 项"
        elif action == "memory_save":
            saved = result.get("saved_keys", result.get("count", 0))
            return f"保存记忆 {saved} 条"
        elif action == "memory_load":
            loaded = result.get("loaded_keys", result.get("count", 0))
            return f"加载记忆 {loaded} 条"
        else:
            # 通用摘要
            if "message" in result:
                return str(result["message"])[:100]
            return f"{action} 完成"
    
    def get_call(self, call_id: str) -> Optional[Dict]:
        """获取单条调用记录"""
        # 先从缓存查找
        with self._cache_lock:
            for record in reversed(self._cache):
                if record.get("call_id") == call_id:
                    return record
        
        # 缓存未命中，从文件查找
        return self._search_in_file(call_id)
    
    def _search_in_file(self, call_id: str) -> Optional[Dict]:
        """从日志文件中搜索"""
        if not self.current_log_file.exists():
            return None
        
        try:
            with open(self.current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record.get("call_id") == call_id:
                            return record
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"搜索调用记录失败: {e}")
        return None
    
    def query(
        self,
        source: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[CallStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """查询调用记录"""
        results = []
        
        # 从缓存查询
        with self._cache_lock:
            for record in reversed(self._cache):
                if self._match_record(record, source, action, status, start_time, end_time):
                    results.append(record)
                    if len(results) >= limit:
                        break
        
        # 如果缓存不够，从文件补充
        if len(results) < limit and self.current_log_file.exists():
            try:
                with open(self.current_log_file, "r", encoding="utf-8") as f:
                    for line in reversed(f.readlines()):
                        if len(results) >= limit:
                            break
                        try:
                            record = json.loads(line.strip())
                            if self._match_record(record, source, action, status, start_time, end_time):
                                # 避免重复
                                if record["call_id"] not in [r["call_id"] for r in results]:
                                    results.append(record)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"查询调用记录失败: {e}")
        
        return results
    
    def _match_record(
        self,
        record: Dict,
        source: Optional[str],
        action: Optional[str],
        status: Optional[CallStatus],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> bool:
        """检查记录是否匹配条件"""
        if source and record.get("source") != source:
            return False
        if action and record.get("action") != action:
            return False
        if status and record.get("status") != status.value:
            return False
        if start_time or end_time:
            try:
                record_time = datetime.fromisoformat(record.get("timestamp", ""))
                if start_time and record_time < start_time:
                    return False
                if end_time and record_time > end_time:
                    return False
            except (ValueError, TypeError):
                pass
        return True
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        # 计算平均耗时
        if stats["total_calls"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
            stats["success_rate"] = stats["success_count"] / stats["total_calls"] * 100
        else:
            stats["avg_duration_ms"] = 0
            stats["success_rate"] = 0
        
        return stats
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict]:
        """获取最近的调用记录"""
        return self.query(limit=limit)
    
    def export_logs(self, start_date: str, end_date: str) -> List[Dict]:
        """导出指定日期范围的日志"""
        results = []
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        current = start
        while current <= end:
            log_file = self.log_dir / f"calls_{current.strftime('%Y%m%d')}.jsonl"
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                results.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    print(f"读取日志文件失败 {log_file}: {e}")
            current = (current.replace(day=current.day + 1) if current.day < 28 
                      else current.replace(month=current.month + 1, day=1))
        
        return results


# 全局单例
_logger: Optional[CallLogger] = None


def get_logger(log_dir: str = "./data/call_logs") -> CallLogger:
    """获取全局调用记录器"""
    global _logger
    if _logger is None:
        _logger = CallLogger(log_dir)
    return _logger


# 便捷装饰器
def log_call(source: str, action: str):
    """装饰器：自动记录函数调用"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            call_id = logger.log_call_start(source, action, {"args": str(args), "kwargs": str(kwargs)})
            
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.log_call_end(call_id, {"result": str(result)[:500]}, CallStatus.SUCCESS, duration)
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.log_call_end(call_id, {"error": str(e)}, CallStatus.FAILED, duration)
                raise
        return wrapper
    return decorator


# Context Manager 用于手动控制调用记录
class CallContext:
    """调用上下文管理器"""
    
    def __init__(self, source: str, action: str, params: Dict = None):
        self.source = source
        self.action = action
        self.params = params or {}
        self.call_id = None
        self._start_time = None
        self.logger = get_logger()
    
    def __enter__(self):
        self._start_time = datetime.now()
        self.call_id = self.logger.log_call_start(self.source, self.action, self.params)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self._start_time).total_seconds() * 1000
        
        if exc_type is None:
            self.logger.log_call_end(
                self.call_id, 
                {"status": "completed"},
                CallStatus.SUCCESS, 
                duration
            )
        else:
            self.logger.log_call_end(
                self.call_id,
                {"error": str(exc_val)},
                CallStatus.FAILED,
                duration
            )
        
        return False  # 不吞掉异常


# 使用示例
if __name__ == "__main__":
    logger = get_logger()
    
    # 方式1: 使用装饰器
    @log_call("test_module", "test_action")
    def test_function(x, y):
        return x + y
    
    result = test_function(1, 2)
    print(f"结果: {result}")
    
    # 方式2: 使用上下文管理器
    with CallContext("executor", "execute_task", {"task_id": "task-123"}) as ctx:
        print(f"执行任务: {ctx.call_id}")
        # 模拟执行
        import time
        time.sleep(0.1)
    
    # 查询记录
    print("\n=== 最近调用记录 ===")
    for call in logger.get_recent_calls(5):
        print(f"[{call['timestamp']}] {call['source']}.{call['action']} - {call['status']} ({call['duration_ms']:.2f}ms)")
        print(f"  摘要: {call['summary']}")
    
    print("\n=== 统计信息 ===")
    print(json.dumps(logger.get_statistics(), indent=2, ensure_ascii=False))
