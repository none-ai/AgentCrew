#!/bin/bash
set -e
# AgentCrew 主动执行启动脚本

cd "$(dirname "$0")"

case "$1" in
    start)
        python3 active_execution_trigger.py start "$@"
        ;;
    stop)
        python3 active_execution_trigger.py stop
        ;;
    restart)
        python3 active_execution_trigger.py restart "$@"
        ;;
    status)
        python3 active_execution_trigger.py status
        ;;
    run)
        python3 active_execution_trigger.py run
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|run}"
        echo ""
        echo "  start   - 启动守护进程 (后台运行)"
        echo "  stop    - 停止守护进程"
        echo "  restart - 重启守护进程"
        echo "  status  - 查看状态"
        echo "  run     - 运行一次主动执行"
        exit 1
        ;;
esac
