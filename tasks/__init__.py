"""
任务管理模块
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务"""
    
    def __init__(self, task_id: str, title: str, description: str = "", 
                 assignee: str = None, priority: int = 3):
        self.id = task_id
        self.title = title
        self.description = description
        self.assignee = assignee
        self.priority = priority  # 1=最高, 5=最低
        self.status = TaskStatus.PENDING
        self.result = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.dependencies = []
        self.subtasks = []
    
    def assign(self, assignee: str):
        """分配任务"""
        self.assignee = assignee
    
    def start(self):
        """开始任务"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now().isoformat()
    
    def complete(self, result: Dict = None):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.result = result or {}
    
    def fail(self, error: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now().isoformat()
        self.result = {"error": error}
    
    def add_dependency(self, task_id: str):
        """添加依赖"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
    
    def add_subtask(self, subtask: 'Task'):
        """添加子任务"""
        self.subtasks.append(subtask)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "priority": self.priority,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dependencies": self.dependencies,
            "subtasks": [s.to_dict() for s in self.subtasks]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        """从字典创建"""
        task = cls(
            data["id"],
            data["title"],
            data.get("description", ""),
            data.get("assignee"),
            data.get("priority", 3)
        )
        task.status = TaskStatus(data.get("status", "pending"))
        task.result = data.get("result")
        task.created_at = data.get("created_at", datetime.now().isoformat())
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        task.dependencies = data.get("dependencies", [])
        return task


class TaskManager:
    """任务管理器"""
    
    def __init__(self, storage_path: str = "data/tasks.json"):
        self.storage_path = storage_path
        self.tasks: Dict[str, Task] = {}
        self.load()
    
    def create_task(self, task_id: str, title: str, description: str = "",
                    assignee: str = None, priority: int = 3) -> Task:
        """创建任务"""
        task = Task(task_id, title, description, assignee, priority)
        self.tasks[task_id] = task
        self.save()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [t for t in self.tasks.values() if t.status == status]
    
    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        """按负责人获取任务"""
        return [t for t in self.tasks.values() if t.assignee == assignee]
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """更新任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self.save()
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save()
            return True
        return False
    
    def get_ready_tasks(self) -> List[Task]:
        """获取就绪任务（所有依赖都已完成）"""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # 检查依赖
            deps_completed = True
            for dep_id in task.dependencies:
                dep = self.tasks.get(dep_id)
                if not dep or dep.status != TaskStatus.COMPLETED:
                    deps_completed = False
                    break
            
            if deps_completed:
                ready.append(task)
        
        return ready
    
    def save(self):
        """保存到文件"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        data = {
            task_id: task.to_dict() 
            for task_id, task in self.tasks.items()
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """从文件加载"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        self.tasks[task_id] = Task.from_dict(task_data)
            except Exception as e:
                print(f"Error loading tasks: {e}")


# 全局任务管理器实例
_task_manager = None

def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
