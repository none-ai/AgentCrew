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
    print("\n" + "="*50)
    print("测试: 任务依赖图引擎")
    print("="*50)
    
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
    
    print(f"添加了 {len(tasks)} 个任务节点")
    print(f"添加了 {len(dependencies)} 个依赖关系")
    
    # 测试拓扑排序
    try:
        order = graph.get_topological_order()
        print(f"\n拓扑排序（执行顺序）: {' -> '.join(order)}")
    except ValueError as e:
        print(f"拓扑排序错误: {e}")
    
    # 测试执行层次
    try:
        layers = graph.get_execution_layers()
        print(f"\n执行层次（可并行）:")
        for i, layer in enumerate(layers):
            print(f"  层级{i+1}: {', '.join(layer)}")
    except ValueError as e:
        print(f"执行层次错误: {e}")
    
    # 测试循环检测
    print(f"\n是否存在循环依赖: {graph.has_cycle()}")
    
    # 更新任务状态
    graph.update_status("init", "completed")
    graph.update_status("config", "completed")
    graph.update_status("setup-deps", "completed")
    graph.update_status("build", "running")
    
    print(f"\n就绪任务: {graph.get_ready_tasks()}")
    print(f"统计: {graph.get_statistics()}")
    
    # 测试序列化
    json_str = graph.to_json()
    print(f"\n序列化成功，长度: {len(json_str)} 字符")
    
    # 反序列化
    graph2 = DependencyGraph.from_json(json_str)
    print(f"反序列化成功，节点数: {len(graph2.nodes)}")
    
    print("\n✅ 依赖图引擎测试通过!")
    return True


def test_connection_pool():
    """测试连接池管理"""
    print("\n" + "="*50)
    print("测试: 连接池管理")
    print("="*50)
    
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
    
    print(f"创建连接池: {pool.name}")
    print(f"最小连接数: {pool.min_size}, 最大连接数: {pool.max_size}")
    
    # 启动维护
    pool.start_maintenance()
    print("启动后台维护")
    
    # 获取连接
    print("\n获取连接测试:")
    with pool.get_connection() as conn:
        print(f"  获取连接: {conn.conn_id}")
        print(f"  连接有效: {conn.ping()}")
        print(f"  空闲时间: {conn.get_idle_time():.2f}秒")
    
    print(f"  归还连接成功")
    
    # 获取统计
    stats = pool.get_stats()
    print(f"\n连接池统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 关闭连接池
    pool.stop_maintenance()
    pool.close_all()
    print("\n✅ 连接池测试通过!")
    return True


def test_persistence():
    """测试状态持久化"""
    print("\n" + "="*50)
    print("测试: 状态持久化")
    print("="*50)
    
    # 测试JSON后端
    print("\n--- JSON文件后端 ---")
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
    
    print(f"保存的任务: {tasks}")
    print(f"保存的配置: {config}")
    
    # 列出所有状态
    all_keys = state_manager.list_states()
    print(f"所有状态键: {all_keys}")
    
    # 测试SQLite后端
    print("\n--- SQLite后端 ---")
    sqlite_backend = SQLiteBackend("./data/test_state.db")
    state_manager2 = StateManager(sqlite_backend)
    
    state_manager2.save_state("system/info", {
        "version": "1.0.0",
        "platform": "linux"
    })
    
    info = state_manager2.load_state("system/info")
    print(f"系统信息: {info}")
    
    # 清理测试文件
    import shutil
    shutil.rmtree("./data/test_json", ignore_errors=True)
    try:
        os.remove("./data/test_state.db")
    except:
        pass
    
    print("\n✅ 状态持久化测试通过!")
    return True


def main():
    """主函数"""
    print("="*50)
    print("OpenAgent 新功能测试")
    print("="*50)
    
    results = []
    
    try:
        results.append(("依赖图引擎", test_dependency_graph()))
    except Exception as e:
        print(f"❌ 依赖图引擎测试失败: {e}")
        results.append(("依赖图引擎", False))
    
    try:
        results.append(("连接池管理", test_connection_pool()))
    except Exception as e:
        print(f"❌ 连接池管理测试失败: {e}")
        results.append(("连接池管理", False))
    
    try:
        results.append(("状态持久化", test_persistence()))
    except Exception as e:
        print(f"❌ 状态持久化测试失败: {e}")
        results.append(("状态持久化", False))
    
    # 总结
    print("\n" + "="*50)
    print("测试总结")
    print("="*50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("全部测试通过! 🎉" if all_passed else "部分测试失败!"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
