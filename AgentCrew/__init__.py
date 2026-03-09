"""
OpenAgent - Multi-Agent Collaboration Framework

A powerful framework for building intelligent agent teams with:
- Task decomposition and parallel execution
- Role-based agent collaboration (PM, Architect, Developer, QA, TechWriter)
- Real-time progress tracking
- Message-based communication between agents
"""

__version__ = "0.1.0"
__author__ = "OpenAgent Team"

from .executor import get_executor, Task, TaskStatus, TaskExecutor
from .scheduler import get_dispatcher, TaskScheduler
from .communication import get_communication, Message, MessageType
from .agents import AgentTeam, load_teams

__all__ = [
    "get_executor",
    "Task",
    "TaskStatus", 
    "TaskExecutor",
    "get_dispatcher",
    "TaskScheduler",
    "get_communication",
    "Message",
    "MessageType",
    "AgentTeam",
    "load_teams",
]
