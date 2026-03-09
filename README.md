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

## 架构

```
OpenAgent/
├── agent_team.py      # 核心代理团队管理
├── tasks/            # 任务定义
├── agents/           # 代理实现
└── config/           # 配置文件
```

## 使用方法

```bash
# 列出所有团队
python3 scripts/agent_team.py list

# 查看团队状态
python3 scripts/agent_team.py status --team openagent_dev

# 分发任务
python3 scripts/agent_team.py dispatch JJC-xxx --team openagent_dev --task "任务描述"
```

## 状态

🛠 开发中

---

**创建日期**: 2026-03-09
