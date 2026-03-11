"""
AgentCrew 清理和记忆模块使用示例
"""
import os
import sys

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cleanup import AutoCleaner, CleanupScheduler, CleanupPolicy
from memory import MemoryManager, get_memory_manager


def demo_cleanup():
    """演示清理模块"""
    
    # 创建清理器
    cleaner = AutoCleaner(data_dir="./data")
    
    # 查看统计信息
    try:
        from cleanup.task_cleaner import TaskCleaner
        task_cleaner = TaskCleaner("./data")
        stats = task_cleaner.get_task_stats()
    except Exception as e:
    
    # 模拟清理任务（干运行）
    results = cleaner.clean_all(
        policy=CleanupPolicy.DRY_RUN,
        max_age_days=30,
        archive=True
    )
    
    # 设置定时清理
    scheduler = CleanupScheduler(data_dir="./data")
    scheduler.set_schedule(
        interval="daily",  # 每天
        hour=3  # 凌晨3点
    )
    scheduler.set_cleanup_config(
        max_age_days=30,
        archive=True,
        archive_dir="./data/archives"
    )
    
    return cleaner, scheduler


def demo_memory():
    """演示记忆模块"""
    
    # 创建记忆管理器
    memory = get_memory_manager(data_dir="./data", vector_backend="memory")
    
    # 添加一些记忆
    memory.remember(
        content="AgentCrew是一个智能代理框架,支持多代理协作",
        memory_type="knowledge",
        importance=8
    )
    
    memory.remember(
        content="用户偏好: 简洁风格的回复",
        memory_type="preference",
        importance=7
    )
    
    memory.remember(
        content="项目使用Python开发,依赖chromadb进行向量存储",
        memory_type="fact",
        importance=6
    )
    
    
    # 添加会话消息
    memory.add_message("user", "你好,帮我介绍一下AgentCrew")
    memory.add_message("assistant", "AgentCrew是一个智能代理框架...")
    memory.add_message("user", "它支持哪些功能?")
    memory.add_message("assistant", "AgentCrew支持多代理协作、任务调度等功能")
    
    # 检索记忆
    results = memory.recall("代理 框架")
    for r in results:
    
    # 获取上下文
    context = memory.get_context(query="代理功能", include_long_term=True)
    
    # 获取统计
    stats = memory.get_stats()
    
    # 添加交互并提取到长期记忆
    memory.add_interaction(
        user_message="记住,我喜欢详细的技术解释",
        assistant_message="好的,我以后会提供详细的技术说明",
        important=True
    )
    
    # 再次检索
    results = memory.recall("详细 技术 解释")
    
    return memory


def main():
    """主函数"""
    
    # 演示清理模块
    cleaner, scheduler = demo_cleanup()
    
    # 演示记忆模块
    memory = demo_memory()
    
    
    # 显示最终统计


if __name__ == "__main__":
    main()
