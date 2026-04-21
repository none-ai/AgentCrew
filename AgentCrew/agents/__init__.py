"""
OpenAgent - 多代理协作框架
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from ..runtime import get_runtime_paths
except ImportError:
    from runtime import get_runtime_paths

# 代理角色定义
AGENT_ROLES = {
    "pm": {
        "name": "ProjectManager",
        "title": "项目经理",
        "description": "任务分解、进度跟踪、结果汇总",
        "color": "#3498db",
        "domains": ["planning", "delivery", "coordination"],
        "task_types": ["planning", "coordination", "documentation"],
        "tools": ["kanban", "reporting"]
    },
    "architect": {
        "name": "Architect",
        "title": "架构师",
        "description": "系统设计、技术选型、代码审查",
        "color": "#9b59b6",
        "domains": ["architecture", "systems", "review"],
        "task_types": ["design", "review", "planning"],
        "tools": ["diagramming", "analysis"]
    },
    "developer": {
        "name": "Developer",
        "title": "开发者",
        "description": "代码实现、功能开发",
        "color": "#2ecc71",
        "domains": ["software", "automation"],
        "task_types": ["development", "shell", "automation"],
        "tools": ["python", "shell", "git"]
    },
    "qa": {
        "name": "QA",
        "title": "测试工程师",
        "description": "测试用例、缺陷发现",
        "color": "#e74c3c",
        "domains": ["quality", "verification"],
        "task_types": ["testing", "review"],
        "tools": ["pytest", "reporting"]
    },
    "techwriter": {
        "name": "TechWriter",
        "title": "文档工程师",
        "description": "文档编写",
        "color": "#f39c12",
        "domains": ["documentation", "knowledge"],
        "task_types": ["documentation", "knowledge_capture"],
        "tools": ["markdown", "publishing"]
    },
    "researcher": {
        "name": "Researcher",
        "title": "研究员",
        "description": "信息检索、资料整合、背景分析",
        "color": "#16a085",
        "domains": ["research", "analysis"],
        "task_types": ["research", "analysis"],
        "tools": ["search", "summarization"]
    },
    "analyst": {
        "name": "Analyst",
        "title": "分析师",
        "description": "数据分析、趋势判断、决策支持",
        "color": "#2980b9",
        "domains": ["analytics", "operations"],
        "task_types": ["analysis", "reporting"],
        "tools": ["sql", "spreadsheet", "visualization"]
    },
    "operator": {
        "name": "Operator",
        "title": "运营执行",
        "description": "流程执行、任务编排、外部系统操作",
        "color": "#d35400",
        "domains": ["operations", "orchestration"],
        "task_types": ["operations", "automation", "coordination"],
        "tools": ["shell", "http", "workflow"]
    },
    "coordinator": {
        "name": "Coordinator",
        "title": "协调者",
        "description": "多智能体协同、跨域任务编排、升级决策",
        "color": "#34495e",
        "domains": ["coordination", "orchestration"],
        "task_types": ["coordination", "planning", "review"],
        "tools": ["message_bus", "scheduler", "kanban"]
    }
}

# 默认团队配置
DEFAULT_TEAMS = {
    "AgentCrew_dev": {
        "name": "OpenAgent 开发团队",
        "members": [
            {"role": "pm", "name": "PM-001", "active": True},
            {"role": "architect", "name": "Architect-001", "active": True},
            {"role": "developer", "name": "Developer-A", "active": True},
            {"role": "developer", "name": "Developer-B", "active": True},
            {"role": "qa", "name": "QA-001", "active": True}
        ]
    }
}


@dataclass
class AgentCapability:
    """描述 agent 可执行的能力。"""

    name: str
    description: str = ""
    task_types: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "task_types": list(self.task_types),
            "domains": list(self.domains),
            "tools": list(self.tools),
        }


@dataclass
class AgentProfile:
    """Agent 的通用画像。"""

    role: str
    name: str
    title: str
    description: str
    color: str
    domains: List[str] = field(default_factory=list)
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "domains": list(self.domains),
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "tools": list(self.tools),
            "skills": list(self.skills),
            "mcp_servers": list(self.mcp_servers),
            "metadata": dict(self.metadata),
        }


def _dedupe(values: List[str]) -> List[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _build_profile(role: str, name: str, config: Optional[Dict[str, Any]] = None) -> AgentProfile:
    config = config or {}
    role_info = AGENT_ROLES.get(
        role,
        {
            "name": role.title(),
            "title": role.title(),
            "description": "通用智能体",
            "color": "#7f8c8d",
            "domains": ["general"],
            "task_types": ["default"],
            "tools": [],
        },
    )

    domains = _dedupe(list(role_info.get("domains", [])) + list(config.get("domains", [])))
    tools = _dedupe(list(role_info.get("tools", [])) + list(config.get("tools", [])))
    task_types = _dedupe(list(role_info.get("task_types", [])) + list(config.get("task_types", [])))

    capabilities = [
        AgentCapability(
            name=config.get("capability_name", role_info.get("title", role)),
            description=config.get("capability_description", role_info.get("description", "")),
            task_types=task_types,
            domains=domains,
            tools=tools,
        )
    ]

    for capability in config.get("capabilities", []):
        capabilities.append(
            AgentCapability(
                name=capability.get("name", "custom"),
                description=capability.get("description", ""),
                task_types=capability.get("task_types", []),
                domains=capability.get("domains", []),
                tools=capability.get("tools", []),
            )
        )

    return AgentProfile(
        role=role,
        name=name,
        title=config.get("title", role_info.get("title", role)),
        description=config.get("description", role_info.get("description", "")),
        color=config.get("color", role_info.get("color", "#7f8c8d")),
        domains=domains,
        capabilities=capabilities,
        tools=tools,
        skills=list(config.get("skills", [])),
        mcp_servers=list(config.get("mcp_servers", [])),
        metadata=dict(config.get("metadata", {})),
    )


def _serialize_agent(agent: "Agent") -> Dict[str, Any]:
    return {
        "role": agent.role,
        "name": agent.name,
        "active": True,
        "title": agent.profile.title,
        "description": agent.profile.description,
        "color": agent.profile.color,
        "domains": list(agent.profile.domains),
        "tools": list(agent.profile.tools),
        "skills": list(agent.profile.skills),
        "mcp_servers": list(agent.profile.mcp_servers),
        "capabilities": [capability.to_dict() for capability in agent.profile.capabilities],
        "metadata": dict(agent.profile.metadata),
    }

class Agent:
    """代理基类"""
    
    def __init__(self, role: str, name: str, config: Optional[Dict[str, Any]] = None):
        self.role = role
        self.name = name
        self.role_info = AGENT_ROLES.get(role, {})
        self.profile = _build_profile(role, name, config)
        self.tasks = []
        self.completed_tasks = []
    
    def assign_task(self, task: Dict):
        """分配任务"""
        self.tasks.append(task)
    
    def complete_task(self, task_id: str, result: Dict):
        """完成任务"""
        for task in self.tasks:
            if task.get("id") == task_id:
                task["result"] = result
                task["completed_at"] = datetime.now().isoformat()
                self.completed_tasks.append(task)
                self.tasks.remove(task)
                break

    def add_skill(self, skill_name: str):
        """绑定 skill。"""
        if skill_name not in self.profile.skills:
            self.profile.skills.append(skill_name)

    def add_mcp_server(self, server_name: str):
        """绑定 MCP server。"""
        if server_name not in self.profile.mcp_servers:
            self.profile.mcp_servers.append(server_name)

    def to_config(self) -> Dict[str, Any]:
        return _serialize_agent(self)

    def can_handle(self, task_type: str, domain: Optional[str] = None) -> bool:
        """判断 agent 是否能处理任务。"""
        for capability in self.profile.capabilities:
            task_match = not capability.task_types or task_type in capability.task_types
            domain_match = domain is None or not capability.domains or domain in capability.domains
            if task_match and domain_match:
                return True
        return False
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "name": self.name,
            "role": self.role,
            "role_title": self.profile.title,
            "active_tasks": len(self.tasks),
            "completed_tasks": len(self.completed_tasks),
            "domains": list(self.profile.domains),
            "tools": list(self.profile.tools),
            "skills": list(self.profile.skills),
            "mcp_servers": list(self.profile.mcp_servers),
            "capabilities": [capability.to_dict() for capability in self.profile.capabilities],
        }


class AgentTeam:
    """代理团队"""
    
    def __init__(self, team_id: str, config: Dict):
        self.team_id = team_id
        self.name = config.get("name", "Unnamed Team")
        self.agents = {}
        
        # 初始化代理
        for member in config.get("members", []):
            if member.get("active", False):
                agent = Agent(member["role"], member["name"], member)
                self.agents[member["name"]] = agent
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """获取代理"""
        return self.agents.get(name)
    
    def get_all_agents(self) -> List[Agent]:
        """获取所有代理"""
        return list(self.agents.values())
    
    def get_status(self) -> Dict:
        """获取团队状态"""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "member_count": len(self.agents),
            "members": [agent.get_status() for agent in self.agents.values()]
        }

    def match_agents(self, task_type: str, domain: Optional[str] = None) -> List[Agent]:
        """根据任务类型和领域匹配可处理的 agents。"""
        return [
            agent for agent in self.agents.values()
            if agent.can_handle(task_type, domain)
        ]

    def attach_skill(self, agent_name: str, skill_name: str) -> Dict[str, Any]:
        agent = self.get_agent(agent_name)
        if not agent:
            raise KeyError(agent_name)
        agent.add_skill(skill_name)
        return agent.get_status()

    def attach_mcp_server(self, agent_name: str, server_name: str) -> Dict[str, Any]:
        agent = self.get_agent(agent_name)
        if not agent:
            raise KeyError(agent_name)
        agent.add_mcp_server(server_name)
        return agent.get_status()

    def get_capability_matrix(self) -> Dict[str, Any]:
        """返回团队能力矩阵。"""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "agents": {
                agent.name: {
                    "role": agent.role,
                    "domains": list(agent.profile.domains),
                    "skills": list(agent.profile.skills),
                    "mcp_servers": list(agent.profile.mcp_servers),
                    "capabilities": [capability.to_dict() for capability in agent.profile.capabilities],
                }
                for agent in self.agents.values()
            },
        }


def load_teams(config_path: Optional[str] = None) -> Dict[str, AgentTeam]:
    """加载团队配置"""
    teams = {}
    config_path = config_path or str(get_runtime_paths().data_dir / "agent_teams.json")
    
    # 加载自定义团队
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                for team_id, config in data.get("teams", {}).items():
                    teams[team_id] = AgentTeam(team_id, config)
        except Exception as e:
            print(f"Error loading teams: {e}")
    
    # 添加默认团队
    for team_id, config in DEFAULT_TEAMS.items():
        if team_id not in teams:
            teams[team_id] = AgentTeam(team_id, config)
    
    return teams


def save_teams(teams: Dict[str, AgentTeam], config_path: Optional[str] = None):
    """保存团队配置"""
    data = {"teams": {}}
    config_path = config_path or str(get_runtime_paths().data_dir / "agent_teams.json")
    
    for team_id, team in teams.items():
        data["teams"][team_id] = {
            "name": team.name,
            "members": [_serialize_agent(agent) for agent in team.agents.values()]
        }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    # 测试
    teams = load_teams()
    for team_id, team in teams.items():
        print(f"\n=== {team.name} ===")
        status = team.get_status()
        print(f"成员数: {status['member_count']}")
        for member in status['members']:
            print(f"  - {member['role_title']}: {member['name']} (活跃任务: {member['active_tasks']})")
