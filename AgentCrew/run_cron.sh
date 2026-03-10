#!/bin/bash
set -e
# AgentCrew 自我进化定时任务
# 添加到 crontab: crontab -e
# 0 * * * * /home/stlin-claw/.openclaw/workspace-taizi/AgentCrew/AgentCrew/run_cron.sh

cd /home/stlin-claw/.openclaw/workspace-taizi/AgentCrew/AgentCrew

# 记录开始
echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始进化周期" >> /home/stlin-claw/.openclaw/workspace-taizi/logs/cron_evolution.log

# 运行进化周期
python3 self_evolution.py >> /home/stlin-claw/.openclaw/workspace-taizi/logs/cron_evolution.log 2>&1

# 记录结束
echo "$(date '+%Y-%m-%d %H:%M:%S') - 进化周期完成" >> /home/stlin-claw/.openclaw/workspace-taizi/logs/cron_evolution.log
