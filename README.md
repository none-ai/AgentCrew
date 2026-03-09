# OpenAgent

基于 Agent Team 集群的智能代理框架，支持多代理协作编程。

## 项目目标

- 实现多代理协作编程框架
- 支持任务分解、并行执行、结果汇总
- 与 OpenClaw 系统深度集成

## 核心特性

- 🤖 **多代理协作**：支持 ProjectManager、Architect、Developer、QA、TechWriter 等角色
- 📋 **任务管理**：支持任务分解、进度跟踪、结果汇总
- 🔄 **并行执行**：支持多代理并行处理任务
- 📊 **状态追踪**：与看板系统深度集成
- 💬 **消息通信**：支持代理间消息传递和事件通知

## 架构

```
OpenAgent/
├── agents/              # 代理定义和团队管理
│   └── __init__.py      # Agent、AgentTeam 类
├── tasks/              # 任务定义
├── config/             # 配置文件
├── executor.py         # 任务执行引擎
├── scheduler.py        # 任务调度器
├── communication.py    # 消息通信模块
└── data/              # 数据存储
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `agents/` | 代理角色定义、团队管理 |
| `executor.py` | 任务分解、执行、结果汇总 |
| `scheduler.py` | 任务调度、负载均衡、并行执行 |
| `communication.py` | 消息总线、订阅发布、代理通信 |

## 快速开始

```python
from agents import AgentTeam, load_teams
from executor import get_executor, Task
from scheduler import get_dispatcher
from communication import get_communication

# 1. 加载团队
teams = load_teams()
team = teams.get("openagent_dev")

# 2. 创建任务
executor = get_executor()
task = executor.create_task(
    title="开发用户认证模块",
    description="实现登录、注册、权限验证功能",
    task_type="development"
)

# 3. 分配任务
executor.assign_task(task.id, "Developer-A")

# 4. 执行任务
result = executor.execute_task(task.id)

# 5. 发送通知
comm = get_communication()
comm.send_message(
    sender="System",
    receiver="PM-001",
    content=f"任务 {task.title} 已完成",
    msg_type=MessageType.NOTIFICATION
)
```

## 团队角色

| 角色 | 代号 | 职责 |
|------|------|------|
| 项目经理 | pm | 任务分解、进度跟踪、结果汇总 |
| 架构师 | architect | 系统设计、技术选型、代码审查 |
| 开发者 | developer | 代码实现、功能开发 |
| 测试工程师 | qa | 测试用例、缺陷发现 |
| 文档工程师 | techwriter | 文档编写 |

## 状态

🛠 开发中

---

**创建日期**: 2026-03-09
**最后更新**: 2026-03-09
