#!/usr/bin/env python3
"""
AgentCrew 主动执行定时触发器
定时执行主动巡检、问题识别、自动执行、主动汇报
"""
import os
import sys
import time
import json
import subprocess
import signal
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
AGENTCREW_DIR = f"{WORKSPACE}/AgentCrew/AgentCrew"
LOG_DIR = f"{WORKSPACE}/logs"
PID_FILE = "/tmp/agentcrew_active_execution.pid"
LOG_FILE = f"{LOG_DIR}/active_execution_trigger.log"

# 巡检间隔 (秒)
DEFAULT_INTERVAL = 1800  # 30分钟
MIN_INTERVAL = 300       # 最小5分钟


def log(msg: str):
    """日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_config() -> dict:
    """加载配置"""
    config_file = f"{AGENTCREW_DIR}/active_execution_config.json"
    default_config = {
        "interval_seconds": DEFAULT_INTERVAL,
        "auto_execute": True,
        "min_priority": 3,  # 只自动执行优先级>=3的问题
        "enabled": True,
        "patrol_targets": [
            f"{WORKSPACE}/scripts",
            f"{WORKSPACE}/AgentCrew/AgentCrew",
            f"{WORKSPACE}/data"
        ],
        "notification": False
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except:
            pass
    
    return default_config


def save_config(config: dict):
    """保存配置"""
    config_file = f"{AGENTCREW_DIR}/active_execution_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def write_pid():
    """写入 PID"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """删除 PID 文件"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def signal_handler(signum, frame):
    """信号处理"""
    log(f"📡 收到信号 {signum}, 准备停止...")
    remove_pid()
    sys.exit(0)


def run_active_execution(auto_execute: bool = True) -> dict:
    """运行主动执行周期"""
    log("⚡ 开始主动执行周期...")
    
    # 构建命令
    cmd = [
        sys.executable,
        f"{AGENTCREW_DIR}/active_executor.py"
    ]
    
    if not auto_execute:
        cmd.append("--no-auto")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            cwd=AGENTCREW_DIR
        )
        
        if result.returncode == 0:
            log("✅ 主动执行周期完成")
            # 尝试解析输出
            try:
                output = result.stdout
                if "issues_found" in output or "issues_identified" in output:
                    log(f"📊 {output.splitlines()[-1] if output else '完成'}")
            except:
                pass
            return {"status": "success", "output": result.stdout}
        else:
            log(f"❌ 主动执行周期失败: {result.stderr}")
            return {"status": "error", "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        log("⏱️ 主动执行周期超时")
        return {"status": "timeout", "error": "执行超时"}
    except Exception as e:
        log(f"❌ 主动执行周期异常: {e}")
        return {"status": "error", "error": str(e)}


def check_running() -> bool:
    """检查是否已有实例在运行"""
    if not os.path.exists(PID_FILE):
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # 检查进程是否存在
        os.kill(pid, 0)
        return True
    except:
        # PID 文件存在但进程不在，删除它
        remove_pid()
        return False


def start_daemon(interval: int = None):
    """启动守护进程"""
    if check_running():
        log("⚠️ 已有实例在运行")
        return
    
    config = load_config()
    if interval:
        config["interval_seconds"] = interval
    
    write_pid()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log(f"🚀 AgentCrew 主动执行守护进程已启动")
    log(f"   间隔: {config['interval_seconds']} 秒")
    log(f"   自动执行: {config['auto_execute']}")
    log(f"   最小优先级: {config['min_priority']}")
    
    # 立即运行一次
    run_active_execution(config["auto_execute"])
    
    while True:
        time.sleep(config["interval_seconds"])
        
        # 重新加载配置（支持热更新）
        config = load_config()
        
        if config.get("enabled", True):
            run_active_execution(config["auto_execute"])
        else:
            log("⏸️ 主动执行已禁用")


def stop_daemon():
    """停止守护进程"""
    if check_running():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            log(f"📴 已发送停止信号到 {pid}")
            remove_pid()
        except Exception as e:
            log(f"❌ 停止失败: {e}")
    else:
        log("⚠️ 没有运行的守护进程")


def status():
    """查看状态"""
    if check_running():
        with open(PID_FILE, 'r') as f:
            pid = f.read().strip()
        
        config = load_config()
        print(f"✅ 守护进程运行中 (PID: {pid})")
        print(f"   间隔: {config['interval_seconds']} 秒")
        print(f"   自动执行: {config['auto_execute']}")
    else:
        print("❌ 守护进程未运行")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentCrew 主动执行触发器")
    parser.add_argument("action", nargs="?", choices=["start", "stop", "restart", "status", "run"], 
                       help="操作: start/stop/restart/status/run")
    parser.add_argument("--interval", "-i", type=int, help="间隔秒数")
    parser.add_argument("--auto", "-a", action="store_true", help="启用自动执行")
    parser.add_argument("--no-auto", "-n", action="store_true", help="禁用自动执行")
    parser.add_argument("--once", "-o", action="store_true", help="仅运行一次")
    
    args = parser.parse_args()
    action = args.action or "run"
    
    config = load_config()
    
    if args.auto:
        config["auto_execute"] = True
        save_config(config)
    elif args.no_auto:
        config["auto_execute"] = False
        save_config(config)
    
    if action == "start":
        start_daemon(args.interval)
    elif action == "stop":
        stop_daemon()
    elif action == "restart":
        stop_daemon()
        time.sleep(2)
        start_daemon(args.interval)
    elif action == "status":
        status()
    elif action == "run":
        run_active_execution(config["auto_execute"])


if __name__ == "__main__":
    main()
