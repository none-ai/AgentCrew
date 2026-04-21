from pathlib import Path

from AgentCrew.agents import AgentTeam
from AgentCrew.memory.context import ContextManager
from AgentCrew.memory.graph import GraphMemory
from AgentCrew.memory.long_term import LongTermMemory
from AgentCrew.memory.short_term import ShortTermMemory
from AgentCrew.memory.vector_store import VectorStore
from AgentCrew.runtime import get_runtime_paths


def test_agent_team_capability_matrix_and_matching():
    config = {
        "name": "General Team",
        "members": [
            {
                "role": "researcher",
                "name": "Research-1",
                "active": True,
                "skills": ["literature_review"],
                "mcp_servers": ["knowledge-base"],
            },
            {
                "role": "operator",
                "name": "Ops-1",
                "active": True,
                "domains": ["operations", "customer_success"],
                "task_types": ["operations", "support"],
            },
        ],
    }

    team = AgentTeam("general", config)
    matrix = team.get_capability_matrix()

    assert matrix["agents"]["Research-1"]["skills"] == ["literature_review"]
    assert team.match_agents("research")[0].name == "Research-1"
    assert team.match_agents("support", "customer_success")[0].name == "Ops-1"


def test_graph_memory_context_generation():
    graph_path = get_runtime_paths().data_dir / "test_graph_memory.json"
    graph = GraphMemory(str(graph_path))
    graph.clear()

    try:
        paris = graph.add_entity("Paris", node_type="city")
        france = graph.add_entity("France", node_type="country")
        graph.add_relation(paris, france, "capital_of")
        graph.learn_interaction("Paris is the capital of France", entities=["Paris", "France"])

        context = graph.get_context("Paris")

        assert context["nodes"]
        assert any(edge["relation"] == "capital_of" for edge in context["edges"])
        assert "Paris" in context["summary"]
    finally:
        graph_path.unlink(missing_ok=True)


def test_context_manager_includes_graph_memory():
    graph_path = get_runtime_paths().data_dir / "test_graph_context.json"
    graph = GraphMemory(str(graph_path))
    graph.clear()

    try:
        graph.add_entity("AgentCrew", node_type="project")
        graph.add_entity("OpenClaw", node_type="platform")
        graph.add_relation("AgentCrew", "OpenClaw", "integrates_with")

        context = ContextManager(
            long_term=LongTermMemory(vector_store=VectorStore("memory")),
            short_term=ShortTermMemory(),
            graph_memory=graph,
        )
        prompt = context.get_prompt_context("AgentCrew")

        assert "图记忆" in prompt
        assert "integrates_with" in prompt
    finally:
        graph_path.unlink(missing_ok=True)


def test_long_term_memory_supports_importance_filter():
    long_term = LongTermMemory(vector_store=VectorStore("memory"))
    long_term.vector_store.clear_all()

    long_term.add("low importance memory", importance=2)
    long_term.add("high importance memory", importance=9)

    results = long_term.get_important_memories(min_importance=7)

    assert any("high importance memory" in item["content"] for item in results)
    assert all(item["metadata"]["importance"] >= 7 for item in results)
