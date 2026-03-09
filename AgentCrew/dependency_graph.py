"""
任务依赖图引擎
支持任务依赖关系管理、拓扑排序、循环检测
"""
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque
from datetime import datetime
import json


class DependencyNode:
    """依赖图节点"""
    
    def __init__(self, task_id: str, metadata: Dict = None):
        self.task_id = task_id
        self.metadata = metadata or {}
        self.dependencies: Set[str] = set()  # 依赖的任务ID集合
        self.dependents: Set[str] = set()    # 依赖此任务的任务ID集合
        self.status = "pending"  # pending, ready, running, completed, failed
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "metadata": self.metadata,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DependencyNode':
        node = cls(data["task_id"], data.get("metadata", {}))
        node.dependencies = set(data.get("dependencies", []))
        node.dependents = set(data.get("dependents", []))
        node.status = data.get("status", "pending")
        node.result = data.get("result")
        node.error = data.get("error")
        node.created_at = data.get("created_at", datetime.now().isoformat())
        node.started_at = data.get("started_at")
        node.completed_at = data.get("completed_at")
        return node


class DependencyGraph:
    """任务依赖图引擎"""
    
    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        self._in_degree: Dict[str, int] = {}  # 入度（依赖数量）
    
    def add_node(self, task_id: str, metadata: Dict = None) -> DependencyNode:
        """添加节点"""
        if task_id not in self.nodes:
            self.nodes[task_id] = DependencyNode(task_id, metadata)
            self._in_degree[task_id] = 0
        return self.nodes[task_id]
    
    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """添加依赖关系：task_id 依赖 depends_on"""
        # 确保节点存在
        self.add_node(task_id)
        self.add_node(depends_on)
        
        # 避免重复添加
        if depends_on in self.nodes[task_id].dependencies:
            return False
        
        # 检查循环依赖
        if self._would_create_cycle(task_id, depends_on):
            raise ValueError(f"添加依赖会创建循环: {task_id} -> {depends_on}")
        
        # 添加依赖
        self.nodes[task_id].dependencies.add(depends_on)
        self.nodes[depends_on].dependents.add(task_id)
        self._in_degree[task_id] += 1
        
        return True
    
    def add_dependencies(self, task_id: str, depends_on_list: List[str]) -> List[bool]:
        """批量添加依赖"""
        results = []
        for dep in depends_on_list:
            try:
                results.append(self.add_dependency(task_id, dep))
            except ValueError as e:
                print(f"警告: {e}")
                results.append(False)
        return results
    
    def _would_create_cycle(self, task_id: str, depends_on: str) -> bool:
        """检查是否会造成循环依赖"""
        # 如果 depends_on 依赖 task_id，则添加后会产生循环
        visited = set()
        stack = [task_id]
        
        while stack:
            current = stack.pop()
            if current == depends_on:
                return True
            if current in visited:
                continue
            visited.add(current)
            
            for dep in self.nodes[current].dependencies:
                stack.append(dep)
        
        return False
    
    def remove_dependency(self, task_id: str, depends_on: str) -> bool:
        """移除依赖关系"""
        if task_id not in self.nodes or depends_on not in self.nodes:
            return False
        
        if depends_on not in self.nodes[task_id].dependencies:
            return False
        
        self.nodes[task_id].dependencies.discard(depends_on)
        self.nodes[depends_on].dependents.discard(task_id)
        self._in_degree[task_id] -= 1
        
        return True
    
    def get_ready_tasks(self) -> List[str]:
        """获取就绪的任务（所有依赖都已完成）"""
        ready = []
        for task_id, node in self.nodes.items():
            if node.status != "pending":
                continue
            
            # 检查所有依赖是否都已完成
            all_deps_completed = all(
                self.nodes[dep].status == "completed"
                for dep in node.dependencies
            )
            
            if all_deps_completed:
                ready.append(task_id)
        
        return ready
    
    def get_topological_order(self) -> List[str]:
        """获取拓扑排序结果（可执行顺序）"""
        # 复制入度
        in_degree = self._in_degree.copy()
        queue = deque()
        
        # 找到所有入度为0的节点
        for task_id, degree in in_degree.items():
            if degree == 0 and self.nodes[task_id].status == "pending":
                queue.append(task_id)
        
        result = []
        
        while queue:
            task_id = queue.popleft()
            result.append(task_id)
            
            # 更新依赖节点的入度
            for dependent in self.nodes[task_id].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0 and self.nodes[dependent].status == "pending":
                    queue.append(dependent)
        
        # 检查是否有循环（如果结果数量不等于节点数量）
        if len(result) != len(self.nodes):
            remaining = [tid for tid in self.nodes if tid not in result]
            raise ValueError(f"存在循环依赖，无法完成拓扑排序。循环节点: {remaining}")
        
        return result
    
    def detect_cycles(self) -> List[List[str]]:
        """检测循环依赖，返回所有循环路径"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(task_id: str, path: List[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)
            
            for dep in self.nodes[task_id].dependencies:
                if dep not in visited:
                    if dfs(dep, path.copy()):
                        return True
                elif dep in rec_stack:
                    # 发现循环
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:]
                    if cycle not in cycles:
                        cycles.append(cycle)
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self.nodes:
            if task_id not in visited:
                dfs(task_id, [])
        
        return cycles
    
    def has_cycle(self) -> bool:
        """检查是否存在循环依赖"""
        return len(self.detect_cycles()) > 0
    
    def get_execution_layers(self) -> List[List[str]]:
        """获取可并行执行的层次（同一层内的任务可以并行执行）"""
        layers = []
        remaining = set(self.nodes.keys())
        completed = set()
        
        while remaining:
            # 找到这一层可以执行的任务
            current_layer = []
            
            for task_id in remaining:
                node = self.nodes[task_id]
                # 所有依赖都已完成
                if node.dependencies.issubset(completed):
                    current_layer.append(task_id)
            
            if not current_layer:
                # 没有可执行的任务，说明存在循环
                raise ValueError(f"存在循环依赖，剩余节点: {remaining}")
            
            layers.append(current_layer)
            completed.update(current_layer)
            remaining -= set(current_layer)
        
        return layers
    
    def update_status(self, task_id: str, status: str, result: Any = None, error: Optional[str] = None):
        """更新节点状态"""
        if task_id not in self.nodes:
            return False
        
        node = self.nodes[task_id]
        node.status = status
        
        if status == "running":
            node.started_at = datetime.now().isoformat()
        elif status in ("completed", "failed"):
            node.completed_at = datetime.now().isoformat()
        
        if result is not None:
            node.result = result
        if error is not None:
            node.error = error
        
        return True
    
    def get_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        if task_id not in self.nodes:
            return None
        return self.nodes[task_id].status
    
    def get_dependents(self, task_id: str) -> Set[str]:
        """获取依赖此任务的任务"""
        if task_id not in self.nodes:
            return set()
        return self.nodes[task_id].dependents
    
    def get_dependencies(self, task_id: str) -> Set[str]:
        """获取任务的依赖"""
        if task_id not in self.nodes:
            return set()
        return self.nodes[task_id].dependencies
    
    def remove_node(self, task_id: str) -> bool:
        """移除节点及其关联的依赖关系"""
        if task_id not in self.nodes:
            return False
        
        node = self.nodes[task_id]
        
        # 移除对此节点的依赖
        for dep in node.dependents:
            self.nodes[dep].dependencies.discard(task_id)
            self._in_degree[dep] -= 1
        
        # 移除此节点的依赖
        for dep in node.dependencies:
            self.nodes[dep].dependents.discard(task_id)
        
        del self.nodes[task_id]
        del self._in_degree[task_id]
        
        return True
    
    def clear(self):
        """清空所有节点"""
        self.nodes.clear()
        self._in_degree.clear()
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "nodes": {tid: node.to_dict() for tid, node in self.nodes.items()},
            "in_degree": self._in_degree.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DependencyGraph':
        """从字典反序列化"""
        graph = cls()
        nodes_data = data.get("nodes", {})
        
        for task_id, node_data in nodes_data.items():
            graph.nodes[task_id] = DependencyNode.from_dict(node_data)
        
        graph._in_degree = data.get("in_degree", {})
        
        return graph
    
    def to_json(self) -> str:
        """序列化为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DependencyGraph':
        """从JSON反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            "total_nodes": len(self.nodes),
            "pending": 0,
            "ready": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "total_dependencies": 0,
            "has_cycles": self.has_cycle()
        }
        
        for node in self.nodes.values():
            stats[node.status] = stats.get(node.status, 0) + 1
            stats["total_dependencies"] += len(node.dependencies)
        
        return stats
    
    def visualize(self) -> str:
        """生成DOT语言可视化"""
        lines = ["digraph G {"]
        
        for task_id, node in self.nodes.items():
            # 根据状态设置颜色
            color = {
                "pending": "gray",
                "ready": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red"
            }.get(node.status, "gray")
            
            label = f'"{task_id}\\n({node.status})"'
            lines.append(f"    {label} [color={color}, style=filled];")
        
        for task_id, node in self.nodes.items():
            for dep in node.dependencies:
                lines.append(f'    "{dep}" -> "{task_id}";')
        
        lines.append("}")
        return "\n".join(lines)


# 全局依赖图实例
_graph = DependencyGraph()

def get_dependency_graph() -> DependencyGraph:
    """获取全局依赖图"""
    return _graph


# 便捷函数
def add_task_dependency(task_id: str, depends_on: str):
    """添加任务依赖"""
    get_dependency_graph().add_dependency(task_id, depends_on)

def get_ready_tasks() -> List[str]:
    """获取就绪任务"""
    return get_dependency_graph().get_ready_tasks()

def get_execution_layers() -> List[List[str]]:
    """获取执行层次"""
    return get_dependency_graph().get_execution_layers()
