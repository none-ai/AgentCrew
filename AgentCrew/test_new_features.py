#!/usr/bin/env python3
"""
OpenAgent 新功能测试
测试：任务依赖图、连接池、状态持久化
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dependency_graph import DependencyGraph, get_dependency_graph
from connection_pool import ConnectionPool, PoolManager, Connection
from persistence import StateManager, JSONFileBackend, SQLiteBackend


def test_dependency_graph():
    """测试任务依赖图引擎"""
    
    graph = DependencyGraph()
    
    # 添加任务节点
    tasks = [
        ("init", "初始化项目"),
        ("config", "配置系统"),
        ("setup-deps", "安装依赖"),
        ("build", "构建项目"),
        ("test", "运行测试"),
        ("deploy", "部署上线")
    ]
    
    for task_id, desc in tasks:
        graph.add_node(task_id, {"description": desc})
    
    # 添加依赖关系
    dependencies = [
        ("config", "init"),
        ("setup-deps", "init"),
        ("build", "config"),
        ("build", "setup-deps"),
        ("test", "build"),
        ("deploy", "test")
    ]
    
    for task_id, depends_on in dependencies:
        graph.add_dependency(task_id, depends_on)
    
    
    # 测试拓扑排序
    try:
        order = graph.get_topological_order()
    except ValueError as e:
    
    # 测试执行层次
    try:
        layers = graph.get_execution_layers()
        for i, layer in enumerate(layers):
    except ValueError as e:
    
    # 测试循环检测
    
    # 更新任务状态
    graph.update_status("init", "completed")
    graph.update_status("config", "completed")
    graph.update_status("setup-deps", "completed")
    graph.update_status("build", "running")
    
    
    # 测试序列化
    json_str = graph.to_json()
    
    # 反序列化
    graph2 = DependencyGraph.from_json(json_str)
    
    return True


def test_connection_pool():
    """测试连接池管理"""
    
    # 创建简单的模拟连接
    class MockConnection(Connection):
        def __init__(self, conn_id, pool):
            super().__init__(conn_id, pool)
            self._connected = True
        
        def ping(self):
            return self._connected
        
        def close(self):
            self._connected = False
    
    # 创建连接池
    pool = ConnectionPool(
        name="test-pool",
        min_size=2,
        max_size=5,
        max_idle_time=60,
        factory=lambda: MockConnection(f"conn-{id(object())}", None)
    )
    
    
    # 启动维护
    pool.start_maintenance()
    
    # 获取连接
    with pool.get_connection() as conn:
    
    
    # 获取统计
    stats = pool.get_stats()
    for k, v in stats.items():
    
    # 关闭连接池
    pool.stop_maintenance()
    pool.close_all()
    return True


def test_persistence():
    """测试状态持久化"""
    
    # 测试JSON后端
    json_backend = JSONFileBackend("./data/test_json")
    state_manager = StateManager(json_backend)
    
    # 保存状态
    state_manager.save_state("executor/tasks", [
        {"id": "task-1", "title": "任务1", "status": "completed"},
        {"id": "task-2", "title": "任务2", "status": "pending"}
    ])
    
    state_manager.save_state("scheduler/config", {
        "max_workers": 4,
        "timeout": 30
    })
    
    # 加载状态
    tasks = state_manager.load_state("executor/tasks")
    config = state_manager.load_state("scheduler/config")
    
    
    # 列出所有状态
    all_keys = state_manager.list_states()
    
    # 测试SQLite后端
    sqlite_backend = SQLiteBackend("./data/test_state.db")
    state_manager2 = StateManager(sqlite_backend)
    
    state_manager2.save_state("system/info", {
        "version": "1.0.0",
        "platform": "linux"
    })
    
    info = state_manager2.load_state("system/info")
    
    # 清理测试文件
    import shutil
    shutil.rmtree("./data/test_json", ignore_errors=True)
    try:
        os.remove("./data/test_state.db")
    except:
        pass
    
    return True


def main():
    """主函数"""
    
    results = []
    
    try:
        results.append(("依赖图引擎", test_dependency_graph()))
    except Exception as e:
        results.append(("依赖图引擎", False))
    
    try:
        results.append(("连接池管理", test_connection_pool()))
    except Exception as e:
        results.append(("连接池管理", False))
    
    try:
        results.append(("状态持久化", test_persistence()))
    except Exception as e:
        results.append(("状态持久化", False))
    
    # 总结
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        if not passed:
            all_passed = False
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
