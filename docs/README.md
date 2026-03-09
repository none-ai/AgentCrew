# OpenAgent Documentation

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)

---

## Installation

### Requirements

- Python 3.10+
- pip or poetry

### From PyPI

```bash
pip install AgentCrew
```

### From Source

```bash
git clone https://github.com/none-ai/AgentCrew.git
cd AgentCrew
pip install -e .
```

---

## Quick Start

### 1. Load Agent Teams

```python
from AgentCrew import load_teams

teams = load_teams()
team = teams.get("AgentCrew_dev")
print(team.get_status())
```

### 2. Create and Execute Tasks

```python
from AgentCrew import get_executor

executor = get_executor()
task = executor.create_task(
    title="My Task",
    description="Task description",
    task_type="development"
)

# Assign to agent
executor.assign_task(task.id, "Developer-A")

# Execute
result = executor.execute_task(task.id)
```

### 3. Send Messages

```python
from AgentCrew import get_communication, MessageType

comm = get_communication()
comm.send_message(
    sender="Developer-A",
    receiver="PM-001",
    content="Task completed!",
    msg_type=MessageType.NOTIFICATION
)
```

---

## Architecture

### Core Components

1. **Agent Team Management** (`agents/`)
   - Role-based agent definitions
   - Team coordination

2. **Task Execution** (`executor.py`)
   - Task creation and decomposition
   - Execution and result aggregation

3. **Task Scheduling** (`scheduler.py`)
   - Load balancing
   - Parallel execution

4. **Communication** (`communication.py`)
   - Message bus
   - Pub/sub pattern

---

## API Reference

### `load_teams(config_path: str) -> Dict[str, AgentTeam]`

Load agent teams from configuration file.

### `get_executor() -> TaskExecutor`

Get the global task executor instance.

### `get_communication() -> AgentCommunication`

Get the global communication manager instance.

### `TaskExecutor.create_task(title: str, description: str, task_type: str) -> Task`

Create a new task.

### `TaskExecutor.assign_task(task_id: str, agent_name: str) -> bool`

Assign a task to an agent.

### `TaskExecutor.execute_task(task_id: str) -> Dict`

Execute a task and return the result.

---

## Configuration

### Agent Teams Configuration

Create `data/agent_teams.json`:

```json
{
  "teams": {
    "my_team": {
      "name": "My Team",
      "members": [
        {"role": "pm", "name": "PM-001", "active": true},
        {"role": "developer", "name": "Dev-001", "active": true}
      ]
    }
  }
}
```

### Agent Roles

| Role | Description |
|------|-------------|
| `pm` | Project Manager |
| `architect` | System Architect |
| `developer` | Software Developer |
| `qa` | QA Engineer |
| `techwriter` | Technical Writer |

---

## Examples

See the `examples/` directory for more examples:

- `examples/basic_usage.py` - Basic usage patterns
- `examples/task_execution.py` - Task execution workflow
- `examples/messaging.py` - Inter-agent messaging
- `examples/team_management.py` - Team management
