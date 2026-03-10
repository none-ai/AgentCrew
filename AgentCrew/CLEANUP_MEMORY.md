# AgentCrew 清理和记忆模块

本模块为 AgentCrew 提供自动清理和向量记忆功能。

## 功能概述

### 1. 清理模块 (cleanup/)

自动清理过期数据，保持系统健康。

**主要功能：**
- **自动清理过期任务** - 清理已完成/失败/取消的过期任务
- **自动清理过期数据** - 清理过期的状态数据和缓存
- **自动归档已完成任务** - 将已完成任务归档保存
- **自动清理临时文件** - 清理临时文件和缓存
- **自动清理无效日志** - 清理无效和过期的日志文件

**核心组件：**

| 文件 | 功能 |
|------|------|
| `cleaner.py` | 清理器核心基类和自动清理器 |
| `task_cleaner.py` | 任务清理器 |
| `data_cleaner.py` | 数据清理器 |
| `file_cleaner.py` | 文件清理器 |
| `log_cleaner.py` | 日志清理器 |
| `scheduler.py` | 清理调度器 |

**使用示例：**

```python
from cleanup import AutoCleaner, CleanupScheduler, CleanupPolicy, get_cleaner

# 方式1: 使用全局清理器
cleaner = get_cleaner("./data")

# 方式2: 直接创建
cleaner = AutoCleaner(data_dir="./data")

# 执行清理
results = cleaner.clean_all(
    policy=CleanupPolicy.EXPIRED_ONLY,  # 清理策略
    max_age_days=30,                      # 保留30天
    archive=True,                         # 先归档
    archive_dir="./data/archives"        # 归档目录
)

# 设置定时清理
scheduler = CleanupScheduler(data_dir="./data")
scheduler.set_schedule(interval="daily", hour=3)  # 每天凌晨3点
scheduler.set_cleanup_config(max_age_days=30, archive=True)
scheduler.start()  # 启动调度器
```

---

### 2. 记忆模块 (memory/)

向量记忆功能，支持语义搜索。

**主要功能：**
- **灵活上下文管理** - 整合短期和长期记忆
- **长期记忆** - 重要信息持久化，支持向量语义搜索
- **短期记忆** - 当前会话上下文管理
- **使用向量数据库** - 支持 ChromaDB、FAISS 或内存存储
- **支持语义搜索** - 基于向量相似度检索

**核心组件：**

| 文件 | 功能 |
|------|------|
| `vector_store.py` | 向量存储（ChromaDB/FAISS/内存） |
| `long_term.py` | 长期记忆管理 |
| `short_term.py` | 短期记忆管理 |
| `context.py` | 上下文管理器 |
| `memory_manager.py` | 记忆管理器 |

**使用示例：**

```python
from memory import MemoryManager, get_memory_manager

# 方式1: 使用全局记忆管理器
memory = get_memory_manager(data_dir="./data", vector_backend="chroma")

# 方式2: 直接创建
memory = MemoryManager(data_dir="./data", vector_backend="memory")

# 添加长期记忆
memory.remember(
    content="AgentCrew支持多代理协作",
    memory_type="knowledge",
    importance=8
)

# 检索记忆
results = memory.recall("代理 协作")
for r in results:
    print(r['content'])

# 添加会话消息
memory.add_message("user", "你好")
memory.add_message("assistant", "你好！有什么可以帮你的？")

# 获取完整上下文
context = memory.get_context(query="今天天气")
```

---

## 安装依赖

```bash
# 核心依赖
pip install chromadb faiss-cpu

# 向量化模型（可选，提升语义搜索效果）
pip install sentence-transformers
```

---

## 项目结构

```
AgentCrew/
├── cleanup/                 # 清理模块
│   ├── __init__.py
│   ├── cleaner.py          # 核心清理器
│   ├── task_cleaner.py     # 任务清理
│   ├── data_cleaner.py     # 数据清理
│   ├── file_cleaner.py     # 文件清理
│   ├── log_cleaner.py      # 日志清理
│   └── scheduler.py        # 调度器
│
├── memory/                  # 记忆模块
│   ├── __init__.py
│   ├── vector_store.py    # 向量存储
│   ├── long_term.py       # 长期记忆
│   ├── short_term.py      # 短期记忆
│   ├── context.py         # 上下文管理
│   └── memory_manager.py  # 记忆管理
│
└── demo_cleanup_memory.py # 使用示例
```

---

## 运行示例

```bash
cd AgentCrew
python demo_cleanup_memory.py
```

---

## 清理策略

| 策略 | 说明 |
|------|------|
| `ALL` | 清理所有可清理项 |
| `EXPIRED_ONLY` | 仅清理过期的 |
| `ARCHIVE_FIRST` | 先归档再清理 |
| `DRY_RUN` | 模拟运行，不实际清理 |

---

## 记忆类型

| 类型 | 说明 |
|------|------|
| `fact` | 事实性信息 |
| `preference` | 偏好设置 |
| `knowledge` | 知识库 |
| `relationship` | 关系信息 |
| `experience` | 经验总结 |
| `goal` | 目标规划 |

---

## 配置说明

### 清理调度

```python
scheduler = CleanupScheduler(data_dir="./data")

# 设置每日清理
scheduler.set_schedule(interval="daily", hour=3)

# 或每周清理
scheduler.set_schedule(interval="weekly", day_of_week=0, hour=3)

# 或每月清理
scheduler.set_schedule(interval="monthly", day_of_month=1, hour=3)

# 设置清理参数
scheduler.set_cleanup_config(
    max_age_days=30,        # 数据保留天数
    archive=True,           # 是否归档
    archive_dir="./data/archives"
)

# 启动调度器
scheduler.start()
```

### 向量存储后端

```python
# 使用 ChromaDB（推荐）
memory = MemoryManager(data_dir="./data", vector_backend="chroma")

# 使用 FAISS
memory = MemoryManager(data_dir="./data", vector_backend="faiss")

# 使用内存存储（测试用）
memory = MemoryManager(data_dir="./data", vector_backend="memory")
```
