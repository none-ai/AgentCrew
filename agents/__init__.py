"""
OpenAgent - 多代理协作框架
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# 代理角色定义
AGENT_ROLES = {
    "pm": {
        "name": "ProjectManager",
        "title": "项目经理",
        "description": "任务分解、进度跟踪、结果汇总",
        "color": "#3498db"
    },
    "architect": {
        "name": "Architect",
        "title": "架构师",
        "description": "系统设计、技术选型、代码审查",
        "color": "#9b59b6"
    },
    "developer": {
        "name": "Developer",
        "title": "开发者",
        "description": "代码实现、功能开发",
        "color": "#2ecc71"
    },
    "qa": {
        "name": "QA",
        "title": "测试工程师",
        "description": "测试用例、缺陷发现",
        "color": "#e74c3c"
    },
    "techwriter": {
        "name": "TechWriter",
        "title": "文档工程师",
        "description": "文档编写",
        "color": "#f39c12"
    }
}

# 默认团队配置
DEFAULT_TEAMS = {
    "openagent_dev": {
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

class Agent:
    """代理基类"""
    
    def __init__(self, role: str, name: str):
        self.role = role
        self.name = name
        self.role_info = AGENT_ROLES.get(role, {})
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
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "name": self.name,
            "role": self.role,
            "role_title": self.role_info.get("title", ""),
            "active_tasks": len(self.tasks),
            "completed_tasks": len(self.completed_tasks)
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
                agent = Agent(member["role"], member["name"])
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


def load_teams(config_path: str = "data/agent_teams.json") -> Dict[str, AgentTeam]:
    """加载团队配置"""
    teams = {}
    
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


def save_teams(teams: Dict[str, AgentTeam], config_path: str = "data/agent_teams.json"):
    """保存团队配置"""
    data = {"teams": {}}
    
    for team_id, team in teams.items():
        if team_id in DEFAULT_TEAMS:
            continue  # 不保存默认团队
        
        data["teams"][team_id] = {
            "name": team.name,
            "members": [
                {"role": agent.role, "name": agent.name, "active": True}
                for agent in team.agents.values()
            ]
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
