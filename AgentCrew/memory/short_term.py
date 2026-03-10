"""
短期记忆模块
管理当前会话上下文
"""
import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Deque

logger = logging.getLogger(__name__)


class ConversationMessage:
    """对话消息"""
    
    def __init__(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.role = role  # "user", "assistant", "system"
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        msg = cls(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata", {})
        )
        if "timestamp" in data:
            msg.timestamp = datetime.fromisoformat(data["timestamp"])
        return msg


class ShortTermMemory:
    """短期记忆 - 当前会话上下文"""
    
    def __init__(
        self,
        max_messages: int = 100,
        max_age_minutes: int = 60
    ):
        self.max_messages = max_messages
        self.max_age_minutes = max_age_minutes
        
        # 消息队列
        self.messages: Deque[ConversationMessage] = deque(maxlen=max_messages)
        
        # 当前上下文
        self.current_context: Dict[str, Any] = {}
        
        # 会话元数据
        self.session_id: Optional[str] = None
        self.session_start: Optional[datetime] = None
        
        # 关键信息提取
        self.entities: Dict[str, Any] = {}  # 实体
        self.topics: List[str] = []  # 话题
        self.intents: List[str] = []  # 意图
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """添加消息"""
        message = ConversationMessage(role, content, metadata)
        self.messages.append(message)
        
        # 更新会话开始时间
        if self.session_start is None:
            self.session_start = datetime.now()
        
        # 提取实体和话题
        self._extract_info(message)
        
        logger.debug(f"添加消息: {role}, 内容长度={len(content)}")
        return message
    
    def add_user_message(self, content: str, **metadata) -> ConversationMessage:
        """添加用户消息"""
        return self.add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, **metadata) -> ConversationMessage:
        """添加助手消息"""
        return self.add_message("assistant", content, metadata)
    
    def add_system_message(self, content: str, **metadata) -> ConversationMessage:
        """添加系统消息"""
        return self.add_message("system", content, metadata)
    
    def get_messages(
        self,
        limit: Optional[int] = None,
        roles: Optional[List[str]] = None
    ) -> List[ConversationMessage]:
        """获取消息"""
        messages = list(self.messages)
        
        # 按角色过滤
        if roles:
            messages = [m for m in messages if m.role in roles]
        
        # 限制数量
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_recent_messages(self, count: int = 10) -> List[ConversationMessage]:
        """获取最近的消息"""
        return list(self.messages)[-count:]
    
    def get_conversation_context(
        self,
        include_system: bool = True,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取对话上下文
        
        Args:
            include_system: 是否包含系统消息
            max_tokens: 最大 token 数（简化处理，使用字符数）
            
        Returns:
            消息列表
        """
        messages = self.get_messages()
        
        if not include_system:
            messages = [m for m in messages if m.role != "system"]
        
        # 如果有 token 限制，进行截断
        if max_tokens:
            # 简单估算：1 token ≈ 4 字符
            max_chars = max_tokens * 4
            
            total_chars = sum(len(m.content) for m in messages)
            while total_chars > max_chars and len(messages) > 1:
                # 移除最早的消息
                messages.pop(0)
                total_chars = sum(len(m.content) for m in messages)
        
        return [m.to_dict() for m in messages]
    
    def _extract_info(self, message: ConversationMessage):
        """从消息中提取信息"""
        # 简单的实体提取（可以接入 NER 模型）
        content = message.content
        
        # 提取 @mentions
        if "@" in content:
            import re
            mentions = re.findall(r'@(\w+)', content)
            for mention in mentions:
                self.entities[mention] = {
                    "type": "mention",
                    "first_seen": datetime.now().isoformat()
                }
        
        # 提取 #话题
        if "#" in content:
            import re
            topics = re.findall(r'#(\w+)', content)
            for topic in topics:
                if topic not in self.topics:
                    self.topics.append(topic)
        
        # 提取意图关键词
        intent_keywords = {
            "create": ["创建", "新建", "添加"],
            "update": ["更新", "修改", "编辑"],
            "delete": ["删除", "移除"],
            "query": ["查询", "搜索", "找"],
            "execute": ["执行", "运行", "启动"]
        }
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    if intent not in self.intents:
                        self.intents.append(intent)
    
    def set_context(self, key: str, value: Any):
        """设置上下文"""
        self.current_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self.current_context.get(key, default)
    
    def clear_context(self):
        """清空上下文"""
        self.current_context.clear()
    
    def get_entities(self) -> Dict[str, Any]:
        """获取提取的实体"""
        return self.entities.copy()
    
    def get_topics(self) -> List[str]:
        """获取话题"""
        return self.topics.copy()
    
    def get_intents(self) -> List[str]:
        """获取意图"""
        return self.intents.copy()
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        duration = None
        if self.session_start:
            duration = (datetime.now() - self.session_start).total_seconds()
        
        return {
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "duration_seconds": duration,
            "message_count": len(self.messages),
            "user_messages": len([m for m in self.messages if m.role == "user"]),
            "assistant_messages": len([m for m in self.messages if m.role == "assistant"]),
            "current_topics": self.topics[-5:],  # 最近5个话题
            "detected_intents": self.intents
        }
    
    def start_new_session(self, session_id: Optional[str] = None):
        """开始新会话"""
        import uuid
        
        self.session_id = session_id or str(uuid.uuid4())
        self.session_start = datetime.now()
        self.messages.clear()
        self.entities.clear()
        self.topics.clear()
        self.intents.clear()
        self.current_context.clear()
        
        logger.info(f"开始新会话: {self.session_id}")
    
    def summarize(self) -> str:
        """生成会话摘要"""
        if not self.messages:
            return "无对话记录"
        
        user_msgs = [m for m in self.messages if m.role == "user"]
        assistant_msgs = [m for m in self.messages if m.role == "assistant"]
        
        topics_str = ", ".join(self.topics[-3:]) if self.topics else "无"
        
        summary = f"""会话摘要:
- 会话ID: {self.session_id or '未知'}
- 消息数: {len(self.messages)} (用户: {len(user_msgs)}, 助手: {len(assistant_msgs)})
- 话题: {topics_str}
- 意图: {', '.join(self.intents) if self.intents else '无'}
"""
        
        # 添加最后几条消息
        if self.messages:
            summary += "\n最近消息:\n"
            for msg in list(self.messages)[-3:]:
                preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                summary += f"- {msg.role}: {preview}\n"
        
        return summary
    
    def prune_old_messages(self):
        """清理旧消息"""
        cutoff = datetime.now() - timedelta(minutes=self.max_age_minutes)
        
        pruned = 0
        while self.messages and self.messages[0].timestamp < cutoff:
            self.messages.popleft()
            pruned += 1
        
        if pruned > 0:
            logger.info(f"清理了 {pruned} 条过期消息")
    
    def clear(self):
        """清空所有短期记忆"""
        self.messages.clear()
        self.entities.clear()
        self.topics.clear()
        self.intents.clear()
        self.current_context.clear()
        
        logger.info("短期记忆已清空")
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "messages": [m.to_dict() for m in self.messages],
            "entities": self.entities,
            "topics": self.topics,
            "intents": self.intents,
            "context": self.current_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShortTermMemory':
        """从字典恢复"""
        memory = cls()
        
        memory.session_id = data.get("session_id")
        if data.get("session_start"):
            memory.session_start = datetime.fromisoformat(data["session_start"])
        
        for msg_data in data.get("messages", []):
            memory.messages.append(ConversationMessage.from_dict(msg_data))
        
        memory.entities = data.get("entities", {})
        memory.topics = data.get("topics", [])
        memory.intents = data.get("intents", [])
        memory.current_context = data.get("context", {})
        
        return memory
