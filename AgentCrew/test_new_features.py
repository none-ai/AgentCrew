"""
Regression tests for AgentCrew infrastructure modules.
"""

import shutil
import tempfile
from pathlib import Path

from AgentCrew.connection_pool import Connection, ConnectionPool
from AgentCrew.dependency_graph import DependencyGraph
from AgentCrew.persistence import JSONFileBackend, SQLiteBackend, StateManager


def test_dependency_graph_execution_layers():
    graph = DependencyGraph()
    for task_id in ["init", "config", "deps", "build", "test", "deploy"]:
        graph.add_node(task_id)

    graph.add_dependency("config", "init")
    graph.add_dependency("deps", "init")
    graph.add_dependency("build", "config")
    graph.add_dependency("build", "deps")
    graph.add_dependency("test", "build")
    graph.add_dependency("deploy", "test")

    topo = graph.get_topological_order()
    assert topo[0] == "init"
    assert set(topo[1:3]) == {"config", "deps"}
    assert topo[3:] == ["build", "test", "deploy"]
    layers = graph.get_execution_layers()
    assert layers[0] == ["init"]
    assert set(layers[1]) == {"config", "deps"}
    assert layers[2:] == [["build"], ["test"], ["deploy"]]


def test_connection_pool_lifecycle():
    class MockConnection(Connection):
        def __init__(self, conn_id, pool):
            super().__init__(conn_id, pool)
            self.connected = True

        def ping(self):
            return self.connected

        def close(self):
            self.connected = False

        def reset(self):
            self.connected = True

    counter = {"value": 0}

    def factory():
        counter["value"] += 1
        return MockConnection(f"conn-{counter['value']}", None)

    pool = ConnectionPool(name="test", min_size=1, max_size=3, factory=factory)
    pool.start_maintenance()
    with pool.get_connection() as conn:
        assert conn.conn_id.startswith("conn-")
        assert conn.in_use is True
    stats = pool.get_stats()
    pool.stop_maintenance()
    pool.close_all()

    assert stats["total_created"] >= 1


def _make_temp_dir(name: str) -> Path:
    root = Path.cwd() / "test_artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_json_persistence_backend():
    temp_dir = _make_temp_dir("json")
    manager = StateManager(JSONFileBackend(str(temp_dir)))
    payload = {"status": "completed", "count": 2}
    key = f"executor/tasks/{next(tempfile._get_candidate_names())}"

    try:
        assert manager.save_state(key, payload) is True
        assert manager.load_state(key) == payload
        assert manager.list_states("executor")
    finally:
        for artifact in temp_dir.glob("*.json"):
            artifact.unlink(missing_ok=True)


def test_sqlite_persistence_backend():
    temp_dir = _make_temp_dir("sqlite")
    db_path = temp_dir / f"state-{next(tempfile._get_candidate_names())}.db"
    manager = StateManager(SQLiteBackend(str(db_path)))
    payload = {"version": "1.0.0", "platform": "test"}

    try:
        assert manager.save_state("system/info", payload) is True
        assert manager.load_state("system/info") == payload
    finally:
        db_path.unlink(missing_ok=True)
