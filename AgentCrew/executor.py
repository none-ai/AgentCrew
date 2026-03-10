"""
OpenAgent 任务执行引擎
负责任务的分解、调度、执行和结果汇总
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class Task:
    """任务"""
    
    def __init__(self, title: str, description: str = "", parent_id: str = None):
        self.id = f"task-{uuid.uuid4().hex[:8]}"
        self.title = title
        self.description = description
        self.parent_id = parent_id
        self.status = TaskStatus.PENDING
        self.assignee = None
        self.result = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.subtasks = []
        self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "status": self.status.value,
            "assignee": self.assignee,
            "result": self.result,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        task = cls(data.get("title", ""), data.get("description", ""), data.get("parent_id"))
        task.id = data.get("id", task.id)
        task.status = TaskStatus(data.get("status", "pending"))
        task.assignee = data.get("assignee")
        task.result = data.get("result")
        task.created_at = data.get("created_at", datetime.now().isoformat())
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        task.metadata = data.get("metadata", {})
        return task


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
    
    def create_task(self, title: str, description: str = "", 
                    task_type: str = "default", parent_id: str = None,
                    metadata: Dict = None) -> Task:
        """创建任务"""
        task = Task(title, description, parent_id)
        task.metadata["task_type"] = task_type
        if metadata:
            task.metadata.update(metadata)
        
        self.tasks[task.id] = task
        
        # 如果有父任务，添加到子任务列表
        if parent_id and parent_id in self.tasks:
            self.tasks[parent_id].subtasks.append(task)
        
        return task
    
    def assign_task(self, task_id: str, assignee: str) -> bool:
        """分配任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.assignee = assignee
        return True
    
    def start_task(self, task_id: str) -> bool:
        """开始任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now().isoformat()
        return True
    
    def complete_task(self, task_id: str, result: Dict = None) -> bool:
        """完成任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now().isoformat()
        task.result = result or {}
        
        # 检查并更新父任务
        if task.parent_id and task.parent_id in self.tasks:
            parent = self.tasks[task.parent_id]
            self._check_parent_complete(parent)
        
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now().isoformat()
        task.result = {"error": error}
        return True
    
    def _check_parent_complete(self, parent: Task):
        """检查父任务是否完成"""
        if not parent.subtasks:
            return
        
        # 检查是否所有子任务都完成
        all_completed = all(
            s.status == TaskStatus.COMPLETED for s in parent.subtasks
        )
        
        if all_completed:
            # 汇总子任务结果
            results = [s.result for s in parent.subtasks if s.result]
            parent.result = {"subtask_results": results}
            parent.status = TaskStatus.COMPLETED
            parent.completed_at = datetime.now().isoformat()
    
    def execute_task(self, task_id: str) -> Dict:
        """执行任务"""
        if task_id not in self.tasks:
            return {"status": "error", "message": "Task not found"}
        
        task = self.tasks[task_id]
        task_type = task.metadata.get("task_type", "default")
        
        # 检查是否有对应的处理器
        if task_type in self.task_handlers:
            handler = self.task_handlers[task_type]
            try:
                self.start_task(task_id)
                result = handler(task)
                self.complete_task(task_id, result)
                return {"status": "ok", "result": result}
            except Exception as e:
                self.fail_task(task_id, str(e))
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"No handler for task type: {task_type}"}
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [t for t in self.tasks.values() if t.status == status]
    
    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        """按执行人获取任务"""
        return [t for t in self.tasks.values() if t.assignee == assignee]
    
    def get_task_tree(self, root_id: str) -> Dict:
        """获取任务树"""
        def build_tree(task: Task) -> Dict:
            return {
                "task": task.to_dict(),
                "children": [build_tree(s) for s in task.subtasks]
            }
        
        if root_id not in self.tasks:
            return {}
        
        return build_tree(self.tasks[root_id])
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return [t.to_dict() for t in self.tasks.values()]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0
        }
        
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                stats["in_progress"] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILED:
                stats["failed"] += 1
        
        return stats


# 全局执行器实例
_executor = TaskExecutor()

def get_executor() -> TaskExecutor:
    """获取全局执行器"""
    return _executor
