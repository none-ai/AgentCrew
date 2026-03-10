"""
上下文管理器
整合长期记忆和短期记忆，提供统一的上下文接口
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .long_term import LongTermMemory
from .short_term import ShortTermMemory

logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器"""
    
    def __init__(
        self,
        long_term: Optional[LongTermMemory] = None,
        short_term: Optional[ShortTermMemory] = None,
        max_context_tokens: int = 4000
    ):
        self.long_term = long_term or LongTermMemory()
        self.short_term = short_term or ShortTermMemory()
        self.max_context_tokens = max_context_tokens
    
    def get_context(
        self,
        query: Optional[str] = None,
        include_short_term: bool = True,
        include_long_term: bool = True,
        short_term_messages: int = 10,
        long_term_memories: int = 5
    ) -> Dict[str, Any]:
        """
        获取完整上下文
        
        Args:
            query: 当前查询（用于检索相关长期记忆）
            include_short_term: 是否包含短期记忆
            include_long_term: 是否包含长期记忆
            short_term_messages: 短期记忆消息数
            long_term_memories: 长期记忆数量
            
        Returns:
            上下文字典
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "session_info": self.short_term.get_session_info(),
            "short_term": {},
            "long_term": [],
            "combined": []
        }
        
        # 短期记忆
        if include_short_term:
            context["short_term"] = {
                "messages": [
                    m.to_dict() for m in self.short_term.get_recent_messages(short_term_messages)
                ],
                "entities": self.short_term.get_entities(),
                "topics": self.short_term.get_topics(),
                "intents": self.short_term.get_intents(),
                "context": self.short_term.current_context.copy()
            }
        
        # 长期记忆（语义检索）
        if include_long_term:
            if query:
                # 语义检索
                memories = self.long_term.search(
                    query=query,
                    top_k=long_term_memories
                )
            else:
                # 获取重要记忆
                memories = self.long_term.get_important_memories(min_importance=5)
                memories = memories[:long_term_memories]
            
            context["long_term"] = memories
        
        # 合并上下文
        context["combined"] = self._build_combined_context(context)
        
        return context
    
    def _build_combined_context(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建合并的上下文"""
        combined = []
        
        # 添加系统提示
        combined.append({
            "role": "system",
            "content": "你是一个智能助手，以下是相关上下文信息。"
        })
        
        # 添加长期记忆
        for memory in context.get("long_term", []):
            combined.append({
                "role": "system",
                "content": f"[长期记忆] {memory.get('content', '')}",
                "source": "long_term",
                "memory_id": memory.get("id")
            })
        
        # 添加短期记忆消息
        for msg in context.get("short_term", {}).get("messages", []):
            combined.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        
        return combined
    
    def get_prompt_context(
        self,
        query: str,
        include_history: bool = True
    ) -> str:
        """
        获取提示词格式的上下文
        
        Args:
            query: 当前查询
            include_history: 是否包含对话历史
            
        Returns:
            格式化的上下文字符串
        """
        parts = []
        
        # 相关长期记忆
        memories = self.long_term.search(query, top_k=3)
        if memories:
            parts.append("## 相关记忆")
            for memory in memories:
                importance = memory.get("metadata", {}).get("importance", 5)
                parts.append(f"- [{importance}/10] {memory.get('content')}")
        
        # 对话历史
        if include_history:
            messages = self.short_term.get_recent_messages(5)
            if messages:
                parts.append("\n## 最近对话")
                for msg in messages:
                    parts.append(f"{msg.role}: {msg.content[:100]}")
        
        return "\n".join(parts) if parts else ""
    
    def add_interaction(
        self,
        user_message: str,
        assistant_message: str,
        extract_to_long_term: bool = False,
        importance: int = 5
    ) -> bool:
        """
        添加交互到记忆
        
        Args:
            user_message: 用户消息
            assistant_message: 助手消息
            extract_to_long_term: 是否提取到长期记忆
            importance: 重要性
            
        Returns:
            是否成功
        """
        # 添加到短期记忆
        self.short_term.add_user_message(user_message)
        self.short_term.add_assistant_message(assistant_message)
        
        # 提取到长期记忆
        if extract_to_long_term:
            # 组合为摘要
            summary = f"用户问: {user_message}\n助手答: {assistant_message}"
            
            self.long_term.add(
                content=summary,
                memory_type="experience",
                importance=importance,
                metadata={"source": "interaction"}
            )
        
        return True
    
    def consolidate_session(self) -> bool:
        """将会话摘要到长期记忆"""
        summary = self.short_term.summarize()
        
        # 获取关键信息
        entities = self.short_term.get_entities()
        topics = self.short_term.get_topics()
        
        # 构建详细的会话摘要
        content = f"""会话摘要:
{summary}

涉及实体: {json.dumps(entities, ensure_ascii=False)}
涉及话题: {', '.join(topics)}
"""
        
        return self.long_term.consolidate(content)
    
    def clear_session(self, consolidate: bool = True):
        """
        清除会话
        
        Args:
            consolidate: 是否先将会话摘要到长期记忆
        """
        if consolidate:
            self.consolidate_session()
        
        self.short_term.clear()
        logger.info("会话已清除")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        return {
            "short_term": {
                "message_count": len(self.short_term.messages),
                "session_id": self.short_term.session_id,
                "entities_count": len(self.short_term.entities),
                "topics_count": len(self.short_term.topics)
            },
            "long_term": self.long_term.get_stats()
        }
    
    def search_all(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """搜索所有记忆"""
        # 搜索长期记忆
        long_term_results = self.long_term.search(query, top_k=top_k)
        
        # 简单搜索短期记忆（基于关键词）
        short_term_results = []
        for msg in self.short_term.get_messages():
            if query.lower() in msg.content.lower():
                short_term_results.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "source": "short_term"
                })
        
        return {
            "query": query,
            "long_term_results": long_term_results,
            "short_term_results": short_term_results[:5],
            "total": len(long_term_results) + len(short_term_results)
        }
