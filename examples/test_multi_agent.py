#!/usr/bin/env python3
"""
AgentCrew 多代理协作测试脚本
演示任务分配、执行、结果汇总的完整流程
"""

import sys
import os

# 添加 AgentCrew 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'openagent', 'AgentCrew'))

from executor import get_executor, TaskStatus
from agents import load_teams
from communication import get_communication, MessageType


def main():
    print("=" * 60)
    print("🤖 AgentCrew 多代理协作测试")
    print("=" * 60)
    
    # 1. 加载智能体团队
    print("\n📋 第一步：加载智能体团队")
    print("-" * 40)
    teams = load_teams()
    team = teams.get("AgentCrew_dev")
    
    print(f"团队名称: {team.name}")
    print(f"成员数量: {len(team.agents)}")
    
    for agent in team.agents.values():
        print(f"  - {agent.role_info.get('title')} ({agent.name})")
    
    # 2. 创建任务
    print("\n📝 第二步：创建测试任务")
    print("-" * 40)
    executor = get_executor()
    
    # 创建一个父任务（项目任务）
    main_task = executor.create_task(
        title="开发用户认证模块",
        description="实现一个完整的用户认证系统，包括登录、注册和权限验证",
        task_type="development"
    )
    print(f"主任务创建成功: {main_task.id}")
    print(f"  标题: {main_task.title}")
    print(f"  描述: {main_task.description}")
    
    # 创建子任务（分配给不同角色）
    subtask1 = executor.create_task(
        title="设计数据库架构",
        description="设计用户表、角色表、权限表的结构和关系",
        task_type="design",
        parent_id=main_task.id
    )
    
    subtask2 = executor.create_task(
        title="实现用户注册功能",
        description="实现用户注册API，包含邮箱验证",
        task_type="development",
        parent_id=main_task.id
    )
    
    subtask3 = executor.create_task(
        title="实现用户登录功能",
        description="实现用户登录API，JWT令牌生成",
        task_type="development",
        parent_id=main_task.id
    )
    
    subtask4 = executor.create_task(
        title="编写测试用例",
        description="为认证模块编写单元测试和集成测试",
        task_type="testing",
        parent_id=main_task.id
    )
    
    subtask5 = executor.create_task(
        title="编写API文档",
        description="编写认证模块的API文档",
        task_type="documentation",
        parent_id=main_task.id
    )
    
    print(f"\n子任务创建成功:")
    for i, subtask in enumerate([subtask1, subtask2, subtask3, subtask4, subtask5], 1):
        print(f"  {i}. {subtask.title} ({subtask.id})")
    
    # 3. 分配任务给不同的代理
    print("\n👥 第三步：分配任务给代理")
    print("-" * 40)
    
    # 获取团队成员
    pm = team.get_agent("PM-001")
    architect = team.get_agent("Architect-001")
    dev_a = team.get_agent("Developer-A")
    dev_b = team.get_agent("Developer-B")
    qa = team.get_agent("QA-001")
    
    # 分配任务
    executor.assign_task(subtask1.id, architect.name)
    executor.assign_task(subtask2.id, dev_a.name)
    executor.assign_task(subtask3.id, dev_b.name)
    executor.assign_task(subtask4.id, qa.name)
    executor.assign_task(subtask5.id, pm.name)  # PM 也可以写文档
    
    print("任务分配完成:")
    print(f"  - {subtask1.title} → {architect.name}")
    print(f"  - {subtask2.title} → {dev_a.name}")
    print(f"  - {subtask3.title} → {dev_b.name}")
    print(f"  - {subtask4.title} → {qa.name}")
    print(f"  - {subtask5.title} → {pm.name}")
    
    # 4. 注册任务处理器并执行
    print("\n⚡ 第四步：执行任务")
    print("-" * 40)
    
    # 定义简单的任务处理器
    def design_handler(task):
        return {"status": "completed", "output": "数据库架构设计完成", "details": {
            "tables": ["users", "roles", "permissions"],
            "relationships": "users -> roles -> permissions"
        }}
    
    def dev_handler(task):
        return {"status": "completed", "output": f"{task.title} 开发完成", "details": {
            "files_created": ["auth.py", "models.py"],
            "lines_of_code": 500
        }}
    
    def test_handler(task):
        return {"status": "completed", "output": "测试完成", "details": {
            "tests_run": 50,
            "passed": 48,
            "failed": 2
        }}
    
    def doc_handler(task):
        return {"status": "completed", "output": "文档编写完成", "details": {
            "pages": 5,
            "sections": ["API Reference", "Usage Guide", "Examples"]
        }}
    
    # 注册处理器
    executor.register_handler("design", design_handler)
    executor.register_handler("development", dev_handler)
    executor.register_handler("testing", test_handler)
    executor.register_handler("documentation", doc_handler)
    
    # 执行子任务（模拟并行执行）
    print("\n执行子任务...")
    
    # 使用模拟执行（不调用真实处理器，只模拟状态）
    for subtask in [subtask1, subtask2, subtask3, subtask4, subtask5]:
        executor.start_task(subtask.id)
        task_type = subtask.metadata.get("task_type")
        
        if task_type == "design":
            result = design_handler(subtask)
        elif task_type == "development":
            result = dev_handler(subtask)
        elif task_type == "testing":
            result = test_handler(subtask)
        elif task_type == "documentation":
            result = doc_handler(subtask)
        else:
            result = {"status": "completed"}
        
        executor.complete_task(subtask.id, result)
        print(f"  ✅ {subtask.title} → 完成")
    
    # 5. 结果汇总
    print("\n📊 第五步：结果汇总")
    print("-" * 40)
    
    # 获取主任务状态
    main_task = executor.get_task(main_task.id)
    print(f"\n主任务: {main_task.title}")
    print(f"状态: {main_task.status.value}")
    
    # 汇总子任务结果
    print("\n子任务执行结果:")
    total_code = 0
    total_tests = 0
    
    for subtask in main_task.subtasks:
        print(f"\n  📌 {subtask.title}")
        print(f"     状态: {subtask.status.value}")
        print(f"     执行人: {subtask.assignee}")
        if subtask.result:
            print(f"     结果: {subtask.result.get('output', 'N/A')}")
            if subtask.result.get('details'):
                details = subtask.result['details']
                if 'lines_of_code' in details:
                    total_code += details['lines_of_code']
                if 'tests_run' in details:
                    total_tests += details['tests_run']
    
    print(f"\n📈 统计:")
    print(f"  - 总代码行数: {total_code}")
    print(f"  - 总测试用例: {total_tests}")
    print(f"  - 完成子任务: {len([s for s in main_task.subtasks if s.status == TaskStatus.COMPLETED])}/{len(main_task.subtasks)}")
    
    # 6. 消息通信演示
    print("\n💬 第六步：消息通信演示")
    print("-" * 40)
    
    comm = get_communication()
    
    # 发送任务完成通知
    comm.send_message(
        sender="System",
        receiver=pm.name,
        content=f"任务 '{main_task.title}' 已全部完成",
        msg_type=MessageType.NOTIFICATION,
        metadata={"task_id": main_task.id}
    )
    
    # 广播消息
    comm.broadcast(
        sender="System",
        content="用户认证模块开发完成，已提交测试",
        msg_type=MessageType.BROADCAST
    )
    
    print("消息发送成功:")
    print(f"  - 通知消息: 发送给 {pm.name}")
    print(f"  - 广播消息: 发送给所有团队成员")
    
    # 获取消息
    inbox = comm.get_inbox(pm.name)
    print(f"\n{pm.name} 的收件箱 ({len(inbox)} 条消息):")
    for msg in inbox:
        print(f"  - [{msg.type.value}] {msg.content}")
    
    # 7. 最终统计
    print("\n" + "=" * 60)
    print("📋 任务执行统计")
    print("=" * 60)
    
    stats = executor.get_statistics()
    print(f"总任务数: {stats['total']}")
    print(f"待处理: {stats['pending']}")
    print(f"进行中: {stats['in_progress']}")
    print(f"已完成: {stats['completed']}")
    print(f"失败: {stats['failed']}")
    
    print("\n✅ AgentCrew 多代理协作测试完成！")
    print("=" * 60)
    
    return {
        "status": "success",
        "main_task_id": main_task.id,
        "subtasks_completed": stats['completed'],
        "total_code_lines": total_code,
        "total_tests": total_tests
    }


if __name__ == "__main__":
    result = main()
