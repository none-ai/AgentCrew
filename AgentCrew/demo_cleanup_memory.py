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
    print("\n" + "="*50)
    print("清理模块演示")
    print("="*50)
    
    # 创建清理器
    cleaner = AutoCleaner(data_dir="./data")
    
    # 查看统计信息
    print("\n1. 查看清理统计...")
    try:
        from cleanup.task_cleaner import TaskCleaner
        task_cleaner = TaskCleaner("./data")
        stats = task_cleaner.get_task_stats()
        print(f"   任务统计: {stats}")
    except Exception as e:
        print(f"   暂无任务数据: {e}")
    
    # 模拟清理任务（干运行）
    print("\n2. 模拟清理（干运行模式）...")
    results = cleaner.clean_all(
        policy=CleanupPolicy.DRY_RUN,
        max_age_days=30,
        archive=True
    )
    print(f"   将清理: {results.get('summary', {})}")
    
    # 设置定时清理
    print("\n3. 设置定时清理...")
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
    print(f"   调度状态: {scheduler.get_status()}")
    
    return cleaner, scheduler


def demo_memory():
    """演示记忆模块"""
    print("\n" + "="*50)
    print("记忆模块演示")
    print("="*50)
    
    # 创建记忆管理器
    print("\n1. 创建记忆管理器...")
    memory = get_memory_manager(data_dir="./data", vector_backend="memory")
    
    # 添加一些记忆
    print("\n2. 添加长期记忆...")
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
    
    print("   已添加3条长期记忆")
    
    # 添加会话消息
    print("\n3. 添加会话消息...")
    memory.add_message("user", "你好,帮我介绍一下AgentCrew")
    memory.add_message("assistant", "AgentCrew是一个智能代理框架...")
    memory.add_message("user", "它支持哪些功能?")
    memory.add_message("assistant", "AgentCrew支持多代理协作、任务调度等功能")
    
    # 检索记忆
    print("\n4. 检索相关记忆...")
    results = memory.recall("代理 框架")
    print(f"   检索到 {len(results)} 条记忆:")
    for r in results:
        print(f"   - {r.get('content', '')[:50]}...")
    
    # 获取上下文
    print("\n5. 获取完整上下文...")
    context = memory.get_context(query="代理功能", include_long_term=True)
    print(f"   会话消息数: {len(context.get('short_term', {}).get('messages', []))}")
    print(f"   相关记忆数: {len(context.get('long_term', []))}")
    
    # 获取统计
    print("\n6. 获取记忆统计...")
    stats = memory.get_stats()
    print(f"   短期记忆消息: {stats['short_term']['message_count']}")
    print(f"   长期记忆总数: {stats['long_term']['total']}")
    
    # 添加交互并提取到长期记忆
    print("\n7. 添加重要交互...")
    memory.add_interaction(
        user_message="记住,我喜欢详细的技术解释",
        assistant_message="好的,我以后会提供详细的技术说明",
        important=True
    )
    
    # 再次检索
    print("\n8. 再次检索...")
    results = memory.recall("详细 技术 解释")
    print(f"   检索到 {len(results)} 条记忆")
    
    return memory


def main():
    """主函数"""
    print("="*50)
    print("AgentCrew 清理和记忆模块演示")
    print("="*50)
    
    # 演示清理模块
    cleaner, scheduler = demo_cleanup()
    
    # 演示记忆模块
    memory = demo_memory()
    
    print("\n" + "="*50)
    print("演示完成!")
    print("="*50)
    
    # 显示最终统计
    print("\n最终统计:")
    print(f"  记忆总数: {memory.get_stats()['long_term']['total']}")


if __name__ == "__main__":
    main()
