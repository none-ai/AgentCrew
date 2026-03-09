"""
Tests for OpenAgent package
"""
import pytest
from openagent import (
    load_teams,
    get_executor,
    get_communication,
    Task,
    TaskStatus,
    Message,
    MessageType,
    AgentTeam,
)
from openagent.agents import Agent, AGENT_ROLES


class TestAgents:
    """Test agent functionality"""
    
    def test_agent_creation(self):
        """Test creating an agent"""
        agent = Agent("developer", "TestDev")
        assert agent.name == "TestDev"
        assert agent.role == "developer"
        assert len(agent.tasks) == 0
        assert len(agent.completed_tasks) == 0
    
    def test_agent_assign_task(self):
        """Test assigning a task to an agent"""
        agent = Agent("developer", "TestDev")
        task = {"id": "task-1", "title": "Test Task"}
        agent.assign_task(task)
        assert len(agent.tasks) == 1
        assert agent.tasks[0]["title"] == "Test Task"
    
    def test_agent_complete_task(self):
        """Test completing a task"""
        agent = Agent("developer", "TestDev")
        task = {"id": "task-1", "title": "Test Task"}
        agent.assign_task(task)
        agent.complete_task("task-1", {"result": "success"})
        assert len(agent.tasks) == 0
        assert len(agent.completed_tasks) == 1


class TestAgentTeam:
    """Test agent team functionality"""
    
    def test_team_creation(self):
        """Test creating an agent team"""
        config = {
            "name": "Test Team",
            "members": [
                {"role": "pm", "name": "PM-001", "active": True},
                {"role": "developer", "name": "Dev-001", "active": True},
            ]
        }
        team = AgentTeam("test_team", config)
        assert team.team_id == "test_team"
        assert team.name == "Test Team"
        assert len(team.agents) == 2
    
    def test_get_agent(self):
        """Test getting an agent from team"""
        config = {
            "name": "Test Team",
            "members": [
                {"role": "pm", "name": "PM-001", "active": True},
            ]
        }
        team = AgentTeam("test_team", config)
        agent = team.get_agent("PM-001")
        assert agent is not None
        assert agent.name == "PM-001"
        
        # Non-existent agent
        assert team.get_agent("NonExistent") is None


class TestLoadTeams:
    """Test loading teams"""
    
    def test_load_teams(self):
        """Test loading default teams"""
        teams = load_teams()
        assert isinstance(teams, dict)
        assert len(teams) > 0
        assert "openagent_dev" in teams


class TestTask:
    """Test task functionality"""
    
    def test_task_creation(self):
        """Test creating a task"""
        task = Task("Test Task", "Task Description")
        assert task.title == "Test Task"
        assert task.description == "Task Description"
        assert task.status == TaskStatus.PENDING
        assert task.assignee is None
    
    def test_task_to_dict(self):
        """Test task serialization"""
        task = Task("Test Task", "Description")
        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["title"] == "Test Task"
        assert task_dict["status"] == "pending"


class TestMessage:
    """Test message functionality"""
    
    def test_message_creation(self):
        """Test creating a message"""
        msg = Message(MessageType.CHAT, "sender", "receiver", "Hello!")
        assert msg.type == MessageType.CHAT
        assert msg.sender == "sender"
        assert msg.receiver == "receiver"
        assert msg.content == "Hello!"
        assert msg.read is False
    
    def test_message_serialization(self):
        """Test message serialization"""
        msg = Message(MessageType.CHAT, "sender", "receiver", "Hello!")
        msg_dict = msg.to_dict()
        assert isinstance(msg_dict, dict)
        assert msg_dict["type"] == "chat"
        assert msg_dict["sender"] == "sender"


class TestCommunication:
    """Test communication module"""
    
    def test_send_message(self):
        """Test sending a message"""
        comm = get_communication()
        msg_id = comm.send_message(
            "sender",
            "receiver",
            "Test message",
            MessageType.CHAT
        )
        assert msg_id is not None
    
    def test_get_inbox(self):
        """Test getting inbox"""
        comm = get_communication()
        comm.send_message("sender", "test_agent", "Test", MessageType.CHAT)
        inbox = comm.get_inbox("test_agent")
        assert len(inbox) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
