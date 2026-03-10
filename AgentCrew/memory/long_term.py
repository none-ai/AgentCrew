"""
长期记忆模块
持久化重要信息，支持语义搜索
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .vector_store import VectorStore, MemoryItem

logger = logging.getLogger(__name__)


class LongTermMemory:
    """长期记忆"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        storage_path: str = "./data/memory/long_term"
    ):
        self.vector_store = vector_store or VectorStore()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 记忆类型
        self.memory_types = [
            "fact",           # 事实
            "preference",     # 偏好
            "knowledge",      # 知识
            "relationship",   # 关系
            "experience",     # 经验
            "goal"           # 目标
        ]
    
    def add(
        self,
        content: str,
        memory_type: str = "fact",
        importance: int = 5,  # 1-10
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加长期记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性 1-10
            metadata: 额外元数据
            
        Returns:
            记忆 ID
        """
        if memory_type not in self.memory_types:
            logger.warning(f"未知记忆类型: {memory_type}")
            memory_type = "fact"
        
        meta = metadata or {}
        meta.update({
            "type": memory_type,
            "importance": importance,
            "memory_category": "long_term"
        })
        
        # 添加到向量存储
        memory_id = self.vector_store.add_memory(
            content=content,
            metadata=meta
        )
        
        # 同时保存到文件
        if memory_id:
            self._save_to_file(memory_id, content, meta)
        
        logger.info(f"添加长期记忆: {memory_id}, 类型={memory_type}, 重要性={importance}")
        return memory_id
    
    def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        min_importance: int = 1,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 查询文本
            memory_type: 过滤类型
            min_importance: 最低重要性
            top_k: 返回数量
            
        Returns:
            记忆列表
        """
        filters = {
            "memory_category": "long_term",
            "importance": {"$gte": min_importance}
        }
        
        if memory_type:
            filters["type"] = memory_type
        
        results = self.vector_store.search_memories(
            query=query,
            top_k=top_k,
            filters=filters
        )
        
        return results
    
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆"""
        return self.vector_store.get_memory(memory_id)
    
    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[int] = None
    ) -> bool:
        """更新记忆"""
        metadata = {}
        if importance is not None:
            metadata["importance"] = importance
        
        return self.vector_store.update_memory(
            memory_id=memory_id,
            content=content,
            metadata=metadata if metadata else None
        )
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        # 删除文件
        file_path = self.storage_path / f"{memory_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        return self.vector_store.delete_memory(memory_id)
    
    def _save_to_file(self, memory_id: str, content: str, metadata: Dict):
        """保存到文件"""
        file_path = self.storage_path / f"{memory_id}.json"
        
        data = {
            "id": memory_id,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_by_type(self, memory_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的记忆"""
        return self.search(
            query="",  # 空查询会返回所有
            memory_type=memory_type,
            top_k=100
        )
    
    def get_important_memories(self, min_importance: int = 7) -> List[Dict[str, Any]]:
        """获取重要记忆"""
        return self.search(
            query="",
            min_importance=min_importance,
            top_k=50
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        all_memories = self.search("", top_k=1000)
        
        stats = {
            "total": len(all_memories),
            "by_type": {},
            "avg_importance": 0
        }
        
        total_importance = 0
        
        for memory in all_memories:
            m_type = memory.get("metadata", {}).get("type", "unknown")
            stats["by_type"][m_type] = stats["by_type"].get(m_type, 0) + 1
            
            importance = memory.get("metadata", {}).get("importance", 0)
            total_importance += importance
        
        if all_memories:
            stats["avg_importance"] = total_importance / len(all_memories)
        
        return stats
    
    def consolidate(self, session_summary: str) -> bool:
        """
        将会话摘要整合到长期记忆
        
        Args:
            session_summary: 会话摘要
            
        Returns:
            是否成功
        """
        return self.add(
            content=session_summary,
            memory_type="experience",
            importance=6,
            metadata={"consolidated_from": "session"}
        ) is not None
    
    def export_memories(self, memory_type: Optional[str] = None) -> str:
        """导出记忆到 JSON 文件"""
        if memory_type:
            memories = self.get_by_type(memory_type)
        else:
            memories = self.search("", top_k=1000)
        
        export_file = self.storage_path / f"export_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)
        
        return str(export_file)
    
    def clear(self, memory_type: Optional[str] = None) -> int:
        """清空记忆"""
        if memory_type:
            memories = self.get_by_type(memory_type)
        else:
            memories = self.search("", top_k=1000)
        
        count = 0
        for memory in memories:
            if self.delete(memory["id"]):
                count += 1
        
        return count
