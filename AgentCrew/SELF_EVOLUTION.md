# AgentCrew 自我持续改进模块

让 AgentCrew 能够自我巡检、自我迭代、持续进化。

## 模块结构

```
AgentCrew/
├── self_inspector.py      # 自我巡检模块
├── self_iteration.py      # 自我迭代模块  
├── self_evolution.py     # 持续进化主控制器
├── evolution_trigger.py  # 定时触发器
├── evolution_config.json  # 配置文件
└── __init__.py           # 模块导出
```

## 功能说明

### 1. 自我巡检 (self_inspector.py)
- 检查 Python 语法错误
- 检查导入语句问题
- 检查错误处理
- 检查安全风险（硬编码密码、eval/exec 等）
- 检查代码质量（函数过长、行过长、TODO/FIXME、调试 print）

### 2. 自我迭代 (self_iteration.py)
- 自动修复代码质量问题（行过长、Shell 脚本等）
- 生成需要人工审查的建议列表

### 3. 持续进化 (self_evolution.py)
- 整合巡检和迭代功能
- 记录进化历史
- 生成回顾总结报告

### 4. 定时触发器 (evolution_trigger.py)
- 定时执行进化周期
- 支持守护进程模式

## 使用方法

### 巡检代码
```bash
cd AgentCrew/AgentCrew
python3 self_evolution.py --inspect
```

### 执行迭代（仅分析，不修复）
```bash
python3 self_evolution.py --iterate
```

### 执行迭代（实际修复）
```bash
python3 self_evolution.py --iterate --auto-fix
```

### 回顾总结
```bash
python3 self_evolution.py --reflect
```

### 定时触发器 - 运行一次
```bash
python3 evolution_trigger.py run
```

### 定时触发器 - 启动守护进程
```bash
python3 evolution_trigger.py start
```

### 定时触发器 - 查看状态
```bash
python3 evolution_trigger.py status
```

### 定时触发器 - 停止守护进程
```bash
python3 evolution_trigger.py stop
```

## 配置说明

编辑 `evolution_config.json`:

```json
{
  "interval_seconds": 3600,    // 进化间隔（秒），默认1小时
  "auto_fix": false,          // 是否自动修复问题
  "target_dirs": [            // 巡检目标目录
    "/path/to/scripts",
    "/path/to/AgentCrew"
  ],
  "enabled": true,            // 是否启用定时任务
  "notification": false       // 是否发送通知
}
```

## 日志输出

- 巡检报告: `logs/self_inspect_*.json`
- 进化历史: `logs/evolution_history.json`
- 触发器日志: `logs/evolution_trigger.log`
- 主日志: `logs/self_evolution.log`

## 巡检问题等级

- 🔴 **critical**: 严重问题（语法错误、安全风险）
- 🟡 **warning**: 警告（代码质量问题、错误处理）
- 🔵 **info**: 信息（TODO、代码风格）

## 设计原则

1. **安全优先**: 默认使用 dry-run 模式，不自动修改代码
2. **可追溯**: 所有操作都记录到历史日志
3. **可配置**: 支持灵活配置巡检范围和行为
4. **可扩展**: 巡检规则支持扩展
