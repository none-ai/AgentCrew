"""
AgentCrew - Multi-Agent Collaboration Framework.
"""

from importlib import import_module

__version__ = "0.1.0"
__author__ = "AgentCrew Team"

from .executor import get_executor, Task, TaskStatus, TaskExecutor
from .scheduler import get_dispatcher, TaskScheduler
from .communication import get_communication, Message, MessageType
from .agents import Agent, AgentTeam, load_teams
from .dependency_graph import DependencyGraph, get_dependency_graph
from .connection_pool import ConnectionPool, PoolManager, get_pool_manager, create_pool
from .persistence import StateManager, JSONFileBackend, SQLiteBackend, get_state_manager
from .extensions import ExtensionManager, MCPRegistry, SkillRegistry
from .standalone import StandaloneAgentCrewApp, create_server, serve
from .workflows import Goal, ToolInvocation, WorkflowPlan, WorkflowStep

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
    "Agent",
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
    "SkillRegistry",
    "MCPRegistry",
    "ExtensionManager",
    "StandaloneAgentCrewApp",
    "create_server",
    "serve",
    "Goal",
    "ToolInvocation",
    "WorkflowPlan",
    "WorkflowStep",
    # Self Evolution
    "CodeInspector",
    "run_inspection",
    "AutoFixer",
    "run_auto_fix",
    "SelfEvolution",
    "EvolutionHistory",
]

_LAZY_IMPORTS = {
    "CodeInspector": ("AgentCrew.self_inspector", "CodeInspector"),
    "run_inspection": ("AgentCrew.self_inspector", "run_inspection"),
    "AutoFixer": ("AgentCrew.self_iteration", "AutoFixer"),
    "run_auto_fix": ("AgentCrew.self_iteration", "run_auto_fix"),
    "SelfEvolution": ("AgentCrew.self_evolution", "SelfEvolution"),
    "EvolutionHistory": ("AgentCrew.self_evolution", "EvolutionHistory"),
}


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attribute)
    globals()[name] = value
    return value
