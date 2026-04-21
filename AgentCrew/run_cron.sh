#!/bin/bash
set -e
# AgentCrew 自我进化定时任务
# 添加到 crontab: crontab -e
# 0 * * * * /path/to/AgentCrew/AgentCrew/run_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTCREW_HOME="${AGENTCREW_HOME:-$HOME/.agentcrew}"
LOG_DIR="${AGENTCREW_HOME}/logs"
mkdir -p "${LOG_DIR}"

cd "${SCRIPT_DIR}"

# 记录开始
echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始进化周期" >> "${LOG_DIR}/cron_evolution.log"

# 运行进化周期
python3 self_evolution.py >> "${LOG_DIR}/cron_evolution.log" 2>&1

# 记录结束
echo "$(date '+%Y-%m-%d %H:%M:%S') - 进化周期完成" >> "${LOG_DIR}/cron_evolution.log"
