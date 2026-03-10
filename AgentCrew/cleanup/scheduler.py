"""
清理调度器
定时执行自动清理任务
"""
import os
import sys
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

# 导入 call_logger
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from call_logger import get_logger, CallStatus
except ImportError:
    from ..call_logger import get_logger, CallStatus

logger = logging.getLogger(__name__)


class ScheduleInterval(Enum):
    """调度间隔"""
    HOURLY = "hourly"          # 每小时
    DAILY = "daily"            # 每天
    WEEKLY = "weekly"          # 每周
    MONTHLY = "monthly"        # 每月


class CleanupScheduler:
    """清理调度器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._call_logger = get_logger()
        
        # 调度配置
        self.interval = ScheduleInterval.DAILY
        self.hour = 3  # 每天凌晨3点执行
        self.day_of_week = 0  # 周日
        self.day_of_month = 1  # 每月1号
        
        # 清理配置
        self.max_age_days = 30
        self.archive = True
        self.archive_dir = "./data/archives"
        
        # 回调函数
        self.on_cleanup: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
    
    def start(self):
        """启动调度器"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="cleanup_scheduler",
            action="start",
            params={"interval": self.interval.value, "hour": self.hour}
        )
        
        if self.running:
            logger.warning("清理调度器已在运行")
            self._call_logger.log_call_end(
                call_id,
                result={"reason": "already running"},
                status=CallStatus.FAILED,
                duration_ms=0
            )
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"status": "started"},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(f"清理调度器已启动，间隔: {self.interval.value}")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("清理调度器已停止")
    
    def _run_loop(self):
        """运行调度循环"""
        while self.running:
            try:
                # 检查是否应该执行清理
                if self._should_run():
                    self._execute_cleanup()
                
                # 等待一段时间后再次检查
                time.sleep(60)  # 每分钟检查一次
            
            except Exception as e:
                logger.error(f"清理调度循环出错: {e}")
                if self.on_error:
                    try:
                        self.on_error(e)
                    except:
                        pass
    
    def _should_run(self) -> bool:
        """检查是否应该执行清理"""
        now = datetime.now()
        
        if self.interval == ScheduleInterval.HOURLY:
            return now.minute == 0
        
        elif self.interval == ScheduleInterval.DAILY:
            return now.hour == self.hour and now.minute == 0
        
        elif self.interval == ScheduleInterval.WEEKLY:
            return (now.weekday() == self.day_of_week and 
                    now.hour == self.hour and 
                    now.minute == 0)
        
        elif self.interval == ScheduleInterval.MONTHLY:
            return (now.day == self.day_of_month and 
                    now.hour == self.hour and 
                    now.minute == 0)
        
        return False
    
    def _execute_cleanup(self):
        """执行清理"""
        logger.info("开始执行定时清理任务")
        
        try:
            # 导入清理器
            from .cleaner import get_cleaner
            
            cleaner = get_cleaner(self.data_dir)
            
            # 执行清理
            results = cleaner.clean_all(
                max_age_days=self.max_age_days,
                archive=self.archive,
                archive_dir=self.archive_dir
            )
            
            # 记录结果
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "results": results
            })
            
            # 保持历史记录不超过100条
            if len(self.history) > 100:
                self.history = self.history[-100:]
            
            # 回调
            if self.on_cleanup:
                try:
                    self.on_cleanup(results)
                except Exception as e:
                    logger.error(f"清理回调失败: {e}")
            
            logger.info(f"定时清理完成: {results.get('summary', {})}")
        
        except Exception as e:
            logger.error(f"执行清理失败: {e}")
            if self.on_error:
                try:
                    self.on_error(e)
                except:
                    pass
    
    def run_now(self, **kwargs) -> Dict[str, Any]:
        """立即执行清理"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="cleanup_scheduler",
            action="run_now",
            params=kwargs
        )
        
        logger.info("立即执行清理任务")
        
        try:
            from .cleaner import get_cleaner
            
            cleaner = get_cleaner(self.data_dir)
            results = cleaner.clean_all(**kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            self._call_logger.log_call_end(
                call_id,
                result=results.get("summary", {}),
                status=CallStatus.SUCCESS,
                duration_ms=duration_ms
            )
            
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "manual": True
            })
            
            return results
        
        except Exception as e:
            logger.error(f"立即清理失败: {e}")
            return {"error": str(e)}
    
    def set_schedule(self, interval: ScheduleInterval = None, **kwargs):
        """设置调度计划"""
        if interval is not None:
            # 如果是字符串，转换为枚举
            if isinstance(interval, str):
                interval = ScheduleInterval(interval)
            self.interval = interval
        
        if "hour" in kwargs:
            self.hour = kwargs["hour"]
        if "day_of_week" in kwargs:
            self.day_of_week = kwargs["day_of_week"]
        if "day_of_month" in kwargs:
            self.day_of_month = kwargs["day_of_month"]
        
        logger.info(f"调度计划已更新: {interval.value}, hour={self.hour}")
    
    def set_cleanup_config(self, **kwargs):
        """设置清理配置"""
        if "max_age_days" in kwargs:
            self.max_age_days = kwargs["max_age_days"]
        if "archive" in kwargs:
            self.archive = kwargs["archive"]
        if "archive_dir" in kwargs:
            self.archive_dir = kwargs["archive_dir"]
        
        logger.info(f"清理配置已更新: {kwargs}")
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取清理历史"""
        return self.history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.running,
            "interval": self.interval.value,
            "hour": self.hour,
            "max_age_days": self.max_age_days,
            "archive": self.archive,
            "history_count": len(self.history),
            "last_run": self.history[-1]["timestamp"] if self.history else None
        }


# 全局调度器实例
_scheduler: Optional[CleanupScheduler] = None


def get_cleanup_scheduler(data_dir: str = "./data") -> CleanupScheduler:
    """获取全局清理调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = CleanupScheduler(data_dir)
    return _scheduler
