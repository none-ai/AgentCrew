"""
记忆管理器
整合清理和记忆功能，提供统一的接口
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .vector_store import VectorStore
from .long_term import LongTermMemory
from .short_term import ShortTermMemory
from .context import ContextManager

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器"""
    
    def __init__(
        self,
        data_dir: str = "./data",
        vector_backend: str = "chroma"
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各组件
        vector_store = VectorStore(
            backend=vector_backend,
            persist_directory=str(self.data_dir / "memory")
        )
        
        self.long_term = LongTermMemory(
            vector_store=vector_store,
            storage_path=str(self.data_dir / "memory" / "long_term")
        )
        
        self.short_term = ShortTermMemory()
        
        self.context = ContextManager(
            long_term=self.long_term,
            short_term=self.short_term
        )
        
        # 加载会话状态
        self._load_session()
    
    def _get_session_file(self) -> Path:
        """获取会话状态文件"""
        return self.data_dir / "memory" / "session.json"
    
    def _load_session(self):
        """加载会话状态"""
        session_file = self._get_session_file()
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.short_term = ShortTermMemory.from_dict(data.get("short_term", {}))
                logger.info(f"加载了会话: {self.short_term.session_id}")
            except Exception as e:
                logger.warning(f"加载会话失败: {e}")
                self.short_term = ShortTermMemory()
    
    def _save_session(self):
        """保存会话状态"""
        session_file = self._get_session_file()
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "short_term": self.short_term.to_dict()
        }
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # === 短期记忆操作 ===
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """添加消息"""
        self.short_term.add_message(role, content, metadata)
        
        # 自动保存会话状态
        self._save_session()
        
        return True
    
    def get_conversation(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取对话历史"""
        messages = self.short_term.get_messages(limit=limit)
        return [m.to_dict() for m in messages]
    
    def clear_conversation(self, consolidate: bool = True):
        """清除对话"""
        self.context.clear_session(consolidate=consolidate)
        self._save_session()
    
    # === 长期记忆操作 ===
    
    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        importance: int = 5,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """添加长期记忆"""
        memory_id = self.long_term.add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        logger.info(f"添加长期记忆: {memory_id}")
        return memory_id
    
    def recall(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """检索记忆"""
        return self.long_term.search(
            query=query,
            memory_type=memory_type,
            top_k=limit
        )
    
    def forget(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.long_term.delete(memory_id)
    
    # === 上下文操作 ===
    
    def get_context(
        self,
        query: Optional[str] = None,
        include_long_term: bool = True
    ) -> Dict[str, Any]:
        """获取上下文"""
        return self.context.get_context(
            query=query,
            include_long_term=include_long_term
        )
    
    def get_prompt_context(self, query: str) -> str:
        """获取提示词上下文"""
        return self.context.get_prompt_context(query)
    
    def add_interaction(
        self,
        user_message: str,
        assistant_message: str,
        important: bool = False
    ) -> bool:
        """添加交互"""
        importance = 7 if important else 4
        
        return self.context.add_interaction(
            user_message=user_message,
            assistant_message=assistant_message,
            extract_to_long_term=important,
            importance=importance
        )
    
    # === 会话管理 ===
    
    def start_session(self, session_id: Optional[str] = None):
        """开始新会话"""
        self.context.clear_session(consolidate=True)
        self.short_term.start_new_session(session_id)
        self._save_session()
    
    def end_session(self):
        """结束当前会话"""
        self.context.consolidate_session()
        self._save_session()
    
    # === 统计和状态 ===
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "timestamp": datetime.now().isoformat(),
            "short_term": {
                "message_count": len(self.short_term.messages),
                "session_id": self.short_term.session_id,
                "topics": self.short_term.get_topics()
            },
            "long_term": self.long_term.get_stats(),
            "vector_store": self.long_term.vector_store.get_stats()
        }
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return self.short_term.get_session_info()
    
    # === 批量操作 ===
    
    def import_memories(self, memories: List[Dict[str, Any]]) -> int:
        """批量导入记忆"""
        count = 0
        for memory in memories:
            self.long_term.add(
                content=memory.get("content", ""),
                memory_type=memory.get("type", "fact"),
                importance=memory.get("importance", 5),
                metadata=memory.get("metadata", {})
            )
            count += 1
        
        return count
    
    def export_memories(self, memory_type: Optional[str] = None) -> str:
        """导出记忆"""
        return self.long_term.export_memories(memory_type)
    
    def clear_all(self, keep_session: bool = False):
        """清空所有记忆"""
        if not keep_session:
            self.long_term.clear()
        
        self.short_term.clear()
        self._save_session()
        
        logger.info("记忆已清空")
    
    def search_all(self, query: str) -> Dict[str, Any]:
        """搜索所有记忆"""
        return self.context.search_all(query)


# 全局记忆管理器实例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    data_dir: str = "./data",
    vector_backend: str = "chroma"
) -> MemoryManager:
    """获取全局记忆管理器"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(data_dir, vector_backend)
    return _memory_manager
