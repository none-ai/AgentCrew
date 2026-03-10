"""
OpenAgent - Multi-Agent Collaboration Framework

A powerful framework for building intelligent agent teams with:
- Task decomposition and parallel execution
- Role-based agent collaboration (PM, Architect, Developer, QA, TechWriter)
- Real-time progress tracking
- Message-based communication between agents
- Task dependency graph engine
- Connection pool management
- State persistence
"""

__version__ = "0.1.0"
__author__ = "OpenAgent Team"

from .executor import get_executor, Task, TaskStatus, TaskExecutor
from .scheduler import get_dispatcher, TaskScheduler
from .communication import get_communication, Message, MessageType
from .agents import AgentTeam, load_teams
from .dependency_graph import DependencyGraph, get_dependency_graph
from .connection_pool import ConnectionPool, PoolManager, get_pool_manager, create_pool
from .persistence import StateManager, JSONFileBackend, SQLiteBackend, get_state_manager

from .self_inspector import CodeInspector, run_inspection
from .self_iteration import AutoFixer, run_auto_fix
from .self_evolution import SelfEvolution, EvolutionHistory

__all__ = [
    # Core
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
    # Dependency Graph
    "DependencyGraph",
    "get_dependency_graph",
    # Connection Pool
    "ConnectionPool",
    "PoolManager",
    "get_pool_manager",
    "create_pool",
    # Persistence
    "StateManager",
    "JSONFileBackend",
    "SQLiteBackend",
    "get_state_manager",
    # Self Evolution
    "CodeInspector",
    "run_inspection",
    "AutoFixer",
    "run_auto_fix",
    "SelfEvolution",
    "EvolutionHistory",
]
