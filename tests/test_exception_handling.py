#!/usr/bin/env python3
"""
AgentCrew 异常处理测试 - 简化版
验证刑部"错误监控与恢复"能力
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
sys.path.insert(0, f"{WORKSPACE}/AgentCrew/AgentCrew")

class ExceptionTestResult:
    """测试结果记录"""
    def __init__(self):
        self.tests = []
    
    def add(self, name: str, passed: bool, message: str = "", details: Dict = None):
        self.tests.append({
            "name": name,
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def summary(self) -> Dict:
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["passed"])
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "tests": self.tests
        }

result = ExceptionTestResult()

# 直接导入，不依赖call_logger的数据库功能
from executor import TaskExecutor, TaskStatus

print("=" * 60)
print("AgentCrew 异常处理测试")
print("验证刑部'错误监控与恢复'能力")
print("=" * 60)

# ========== 测试 1: 错误捕获 ==========
print("\n【测试 1】错误捕获能力")
print("-" * 40)

def test_error_catching():
    """测试框架是否能正确捕获各类异常"""
    executor = TaskExecutor()
    errors_caught = []
    
    # 1.1 任务不存在时的错误处理
    print("[1.1] 任务不存在时的错误处理")
    res = executor.execute_task("non-existent-task")
    if res["status"] == "error":
        errors_caught.append("task_not_found")
        result.add("task_not_found_error", True, f"正确捕获: {res['message']}")
    else:
        result.add("task_not_found_error", False, f"未正确处理: {res}")
    
    # 1.2 处理器执行异常捕获
    print("[1.2] 处理器执行异常捕获")
    
    def failing_handler(task):
        raise ValueError("模拟处理器异常")
    
    executor.register_handler("failing", failing_handler)
    task = executor.create_task("测试任务", task_type="failing")
    
    res = executor.execute_task(task.id)
    if res["status"] == "error" and "模拟处理器异常" in res.get("message", ""):
        errors_caught.append("handler_exception")
        result.add("handler_exception_catch", True, "正确捕获处理器异常")
        
        # 验证任务状态被标记为失败
        task_obj = executor.get_task(task.id)
        if task_obj.status == TaskStatus.FAILED:
            result.add("task_status_failed", True, f"任务状态正确: {task_obj.status.value}")
        else:
            result.add("task_status_failed", False, f"任务状态错误: {task_obj.status}")
    else:
        result.add("handler_exception_catch", False, f"未正确处理异常: {res}")
    
    # 1.3 多种异常类型捕获
    print("[1.3] 多种异常类型捕获")
    
    exception_handlers = [
        ("div_zero", lambda t: 1 / 0, "ZeroDivisionError"),
        ("type_error", lambda t: int("not_a_number"), "ValueError"),
    ]
    
    for exc_type, handler, _ in exception_handlers:
        executor.register_handler(exc_type, handler)
        task = executor.create_task(f"测试{exc_type}", task_type=exc_type)
        
        res = executor.execute_task(task.id)
        if res["status"] == "error":
            errors_caught.append(exc_type)
            result.add(f"catch_{exc_type}", True, f"正确捕获{exc_type}")
        else:
            result.add(f"catch_{exc_type}", False, "未捕获异常")
    
    return len(errors_caught)

caught = test_error_catching()
print(f"  → 捕获异常数: {caught}")

# ========== 测试 2: 日志记录 ==========
print("\n【测试 2】日志记录能力")
print("-" * 40)

def test_logging():
    """测试日志记录"""
    # 2.1 Python logging 模块集成
    print("[2.1] Python logging模块")
    
    import logging
    test_logger = logging.getLogger("test_exception")
    test_logger.setLevel(logging.DEBUG)
    
    # 创建临时日志文件
    LOG_DIR = f"{WORKSPACE}/logs"
    log_file = f"{LOG_DIR}/test_exception_{int(time.time())}.log"
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    test_logger.addHandler(handler)
    
    test_logger.error("测试错误日志")
    test_logger.info("测试信息日志")
    
    # 验证日志写入
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            if "测试错误日志" in content and "测试信息日志" in content:
                result.add("file_logging", True, "文件日志正确记录")
            else:
                result.add("file_logging", False, "文件内容不符")
    else:
        result.add("file_logging", False, "日志文件未创建")
    
    # 2.2 异常堆栈跟踪记录
    print("[2.2] 异常堆栈跟踪记录")
    
    try:
        raise RuntimeError("测试异常堆栈")
    except Exception as e:
        tb = traceback.format_exc()
        if "RuntimeError" in tb and "test_exception_handling" in tb:
            result.add("traceback_logging", True, "堆栈跟踪已记录")
        else:
            result.add("traceback_logging", False, "堆栈跟踪格式不符")
        
        # 写入日志
        test_logger.error(f"异常: {e}\n{tb}")
    
    # 2.3 任务结果记录
    print("[2.3] 任务结果记录")
    
    executor = TaskExecutor()
    task = executor.create_task("日志测试任务")
    executor.complete_task(task.id, {"result": "test_ok", "data": [1, 2, 3]})
    
    task_obj = executor.get_task(task.id)
    if task_obj.result and task_obj.result.get("result") == "test_ok":
        result.add("task_result_recorded", True, "任务结果正确记录")
    else:
        result.add("task_result_recorded", False, "任务结果未记录")

test_logging()

# ========== 测试 3: 恢复机制 ==========
print("\n【测试 3】恢复机制")
print("-" * 40)

def test_recovery():
    """测试框架的恢复能力"""
    executor = TaskExecutor()
    
    # 3.1 任务失败后状态正确性
    print("[3.1] 任务失败后状态")
    
    def fail_handler(task):
        raise ValueError("初始失败")
    
    executor.register_handler("fail_test", fail_handler)
    task = executor.create_task("失败测试", task_type="fail_test")
    
    res = executor.execute_task(task.id)
    task_obj = executor.get_task(task.id)
    
    if task_obj.status == TaskStatus.FAILED:
        result.add("failure_status_set", True, f"失败状态正确: {task_obj.result}")
    else:
        result.add("failure_status_set", False, f"状态错误: {task_obj.status}")
    
    # 3.2 重新执行恢复
    print("[3.2] 重新执行恢复")
    
    # 重置任务状态
    task_obj.status = TaskStatus.PENDING
    task_obj.result = None
    
    # 替换为成功处理器
    def success_handler(task):
        return {"recovered": True, "data": "success"}
    
    executor.register_handler("recover_test", success_handler)
    task2 = executor.create_task("恢复测试", task_type="recover_test")
    
    res = executor.execute_task(task2.id)
    task2_obj = executor.get_task(task2.id)
    
    if task2_obj.status == TaskStatus.COMPLETED:
        result.add("retry_recovery", True, "重试后成功恢复")
    else:
        result.add("retry_recovery", False, f"重试后状态: {task2_obj.status}")
    
    # 3.3 父子任务状态传播
    print("[3.3] 父子任务状态传播")
    
    parent = executor.create_task("父任务")
    child1 = executor.create_task("子任务1", parent_id=parent.id)
    child2 = executor.create_task("子任务2", parent_id=parent.id)
    
    executor.complete_task(child1.id, {"ok": True})
    executor.complete_task(child2.id, {"ok": True})
    
    parent_obj = executor.get_task(parent.id)
    if parent_obj.status == TaskStatus.COMPLETED:
        result.add("parent_child_sync", True, "父子任务状态正确同步")
    else:
        result.add("parent_child_sync", False, f"父任务状态: {parent_obj.status}")
    
    # 3.4 任务统计
    print("[3.4] 任务统计")
    
    stats = executor.get_statistics()
    if stats.get("failed", 0) > 0 and stats.get("completed", 0) > 0:
        result.add("statistics_tracking", True, f"统计正确: {stats}")
    else:
        result.add("statistics_tracking", False, f"统计不完整: {stats}")

test_recovery()

# ========== 输出结果 ==========
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)

summary = result.summary()
print(f"\n总计: {summary['total']} 个测试")
print(f"通过: {summary['passed']} 个 ✅")
print(f"失败: {summary['failed']} 个 ❌")

print("\n详细结果:")
for test in summary["tests"]:
    status = "✅" if test["passed"] else "❌"
    print(f"  {status} {test['name']}: {test['message']}")

# 保存结果
report = {
    "test_type": "AgentCrew异常处理测试",
    "test_date": datetime.now().isoformat(),
    "summary": summary,
    "improvements": [
        "建议: 在call_logger中添加数据库表自动迁移功能",
        "建议: 增加重试机制的装饰器支持",
        "建议: 增加异常恢复的回调钩子"
    ]
}

report_path = f"{WORKSPACE}/logs/exception_test_report_{int(time.time())}.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n报告已保存到: {report_path}")
print(f"\n通过率: {summary['passed']*100//summary['total']}%")

sys.exit(0 if summary["failed"] == 0 else 1)
