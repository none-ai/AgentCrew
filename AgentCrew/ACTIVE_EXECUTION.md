# AgentCrew 主动执行模块

让 AgentCrew 不需要等待命令，主动发现问题、主动工作。

## 功能特性

1. **主动巡检** - 定期检查项目状态、代码质量、任务队列
2. **主动发现问题** - 自动识别待处理的问题并创建任务
3. **主动执行** - 根据预设规则自动执行任务
4. **主动汇报** - 完成后自动汇报结果

## 模块结构

```
AgentCrew/AgentCrew/
├── active_executor.py           # 主动执行核心模块
├── active_execution_trigger.py  # 定时触发器
├── active_execution_config.json # 配置文件
└── run_active.sh               # 启动脚本
```

## 使用方法

### 快速开始

```bash
# 运行一次主动执行
python3 active_executor.py --once

# 仅巡检（不执行）
python3 active_executor.py --patrol-only

# 巡检但不自动执行
python3 active_executor.py --no-auto

# 定时运行（每30分钟）
python3 active_executor.py --schedule 30
```

### 守护进程方式

```bash
# 启动守护进程
python3 active_execution_trigger.py start

# 停止守护进程
python3 active_execution_trigger.py stop

# 查看状态
python3 active_execution_trigger.py status

# 手动运行一次
python3 active_execution_trigger.py run
```

### 使用启动脚本

```bash
./run_active.sh start     # 启动
./run_active.sh stop      # 停止
./run_active.sh status    # 状态
./run_active.sh run       # 运行一次
```

## 巡检内容

- **项目状态** - 脚本数量、任务统计、日志文件
- **代码质量** - 调用 self_inspector 检查代码问题
- **任务队列** - 统计各状态任务、识别积压和长期未处理任务
- **系统资源** - 磁盘空间、内存使用、进程状态

## 识别规则

| 规则 | 优先级 | 自动执行 |
|------|--------|----------|
| 代码质量问题 | 3 | 是 |
| 任务积压 (>10个待处理) | 4 | 是 |
| 任务长期未处理 (>3天) | 5 | 是 |
| 磁盘空间不足 (<5GB) | 5 | 是 |
| 进程异常 | 5 | 是 |
| 待审核任务 | 3 | 是 |

## 日志输出

- 主动执行日志: `logs/active_execution.log`
- 报告历史: `logs/active_execution_reports.json`
- 触发器日志: `logs/active_execution_trigger.log`

## 配置

编辑 `active_execution_config.json`:

```json
{
  "interval_seconds": 1800,    // 巡检间隔（秒）
  "auto_execute": true,       // 是否自动执行
  "min_priority": 3,          // 最小执行优先级
  "enabled": true             // 是否启用
}
```
