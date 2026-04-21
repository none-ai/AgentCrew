from pathlib import Path

from AgentCrew.agents import Agent
from AgentCrew.extensions import ExtensionManager


def test_skill_and_mcp_installation_registry():
    manager = ExtensionManager()

    skill_name = "test-skill-framework"
    mcp_name = "test-mcp-framework"

    manager.skills.remove(skill_name)
    manager.mcp.remove(mcp_name)

    try:
        skill = manager.skills.install(
            {
                "name": skill_name,
                "description": "Test skill",
                "entry_prompt": "You are a planning skill.",
                "tools": ["search", "planner"],
                "tags": ["planning"],
            }
        )
        server = manager.mcp.install(
            {
                "name": mcp_name,
                "description": "Test MCP",
                "command": "python",
                "args": ["-m", "example"],
                "capabilities": ["search"],
            }
        )

        listed_skill_names = [item["name"] for item in manager.skills.list()]
        listed_mcp_names = [item["name"] for item in manager.mcp.list()]

        assert skill["name"] in listed_skill_names
        assert server["name"] in listed_mcp_names
        assert Path(skill["path"]).exists()
        assert Path(server["path"]).exists()
    finally:
        manager.skills.remove(skill_name)
        manager.mcp.remove(mcp_name)


def test_extension_manager_builds_agent_bundle():
    manager = ExtensionManager()
    skill_name = "bundle-skill-framework"
    mcp_name = "bundle-mcp-framework"

    manager.skills.remove(skill_name)
    manager.mcp.remove(mcp_name)

    try:
        manager.skills.install(
            {
                "name": skill_name,
                "entry_prompt": "You are a market research skill.",
                "tools": ["search"],
            }
        )
        manager.mcp.install(
            {
                "name": mcp_name,
                "command": "python",
                "args": ["-m", "example"],
                "capabilities": ["fetch"],
            }
        )

        agent = Agent("researcher", "Research-1", {"skills": [skill_name], "mcp_servers": [mcp_name]})
        bundle = manager.build_agent_bundle(agent.profile)

        assert bundle["skills"][0]["name"] == skill_name
        assert bundle["mcp_servers"][0]["name"] == mcp_name
        assert bundle["agent"]["name"] == "Research-1"
    finally:
        manager.skills.remove(skill_name)
        manager.mcp.remove(mcp_name)
