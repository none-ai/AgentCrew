<!-- markdownlint-disable MD041 -->
<div align="center">

<!-- logo -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/-OpenAgent-007ACC?style=for-the-badge&labelColor=1e1e2e&color=89b4fa">
  <source media="(prefers-color-scheme: light)" srcset="https://img.shields.io/badge/-OpenAgent-007ACC?style=for-the-badge&labelColor=f5f5f5&color=007ACC">
  <img alt="OpenAgent" src="https://img.shields.io/badge/-OpenAgent-007ACC?style=for-the-badge">
</picture>

<!-- badges -->
<p>

[![License](https://img.shields.io/github/license/none-ai/openagent?style=flat&color=green)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue?style=flat&color=007ACC)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-developing-yellow?style=flat&color=yellow)](https://github.com/none-ai/openagent)
[![PyPI Version](https://img.shields.io/pypi/v/openagent?style=flat&color=blue)](https://pypi.org/project/openagent/)
[![Last Commit](https://img.shields.io/github/last-commit/none-ai/openagent/main?style=flat&color=orange)](https://github.com/none-ai/openagent/commits)

</p>

<!-- tagline -->
<h3>🤖 Multi-Agent Collaboration Framework</h3>
<p>Intelligent agent team framework with task decomposition, parallel execution, and result aggregation</p>

<!-- quick links -->
<p>

[📖 Documentation](#quick-start) ·
[🏗️ Architecture](#architecture) ·
[👥 Team Roles](#team-roles) ·
[🚀 Contributing](#contributing)

</p>

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|

| 🤖 **Multi-Agent Collaboration** | Supports professional roles: ProjectManager, Architect, Developer, QA, TechWriter |
| 📋 **Task Management** | Intelligent task decomposition, real-time progress tracking, automatic result aggregation |
| 🔄 **Parallel Execution** | Multi-agent parallel processing for maximum concurrency efficiency |
| 📊 **State Tracking** | Deep integration with Kanban system for real-time task status monitoring |
| 💬 **Message Communication** | Inter-agent messaging, event notifications, pub/sub pattern |

## 📦 Installation

```bash
# Install via pip
pip install openagent

# Or install from source
git clone https://github.com/none-ai/openagent.git
cd openagent
pip install -e .
```

## 🚀 Quick Start

```python
from openagent import load_teams, get_executor, get_communication, MessageType

# 1. Load agent teams
teams = load_teams()
team = teams.get("openagent_dev")

# 2. Create a task
executor = get_executor()
task = executor.create_task(
    title="Develop User Auth Module",
    description="Implement login, registration, and permission validation",
    task_type="development"
)

# 3. Assign task
executor.assign_task(task.id, "Developer-A")

# 4. Execute task
result = executor.execute_task(task.id)

# 5. Send notification
comm = get_communication()
comm.send_message(
    sender="System",
    receiver="PM-001",
    content=f"Task {task.title} completed",
    msg_type=MessageType.NOTIFICATION
)
```

## 🏗️ Architecture

```
openagent/
├── agents/              # Agent definitions and team management
│   └── __init__.py      # Agent, AgentTeam classes
├── tasks/               # Task definitions
├── config/              # Configuration files
├── executor.py          # Task execution engine
├── scheduler.py         # Task scheduler
├── communication.py    # Message communication module
└── data/               # Data storage
```

### Core Modules

| Module | Function |
|--------|----------|
| `agents/` | Agent role definitions, team management |
| `executor.py` | Task decomposition, execution, result aggregation |
| `scheduler.py` | Task scheduling, load balancing, parallel execution |
| `communication.py` | Message bus, pub/sub, agent communication |

## 👥 Team Roles

| Role | Code | Responsibility |
|------|------|----------------|
| 🧑‍💼 Project Manager | pm | Task decomposition, progress tracking, result aggregation |
| 🏗️ Architect | architect | System design, technology selection, code review |
| 💻 Developer | developer | Code implementation, feature development |
| 🧪 QA Engineer | qa | Test case creation, defect discovery |
| 📝 Tech Writer | techwriter | Documentation writing |

## 🤝 Contributing

Welcome to submit Pull Requests! Please read the [Contributing Guide](CONTRIBUTING.md) first.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Created**: 2026-03-09 · **Last Updated**: 2026-03-09

⭐ Star us · 🍴 Fork us · 🐛 Report Issues

</div>
