"""
OpenAgent 消息通信模块
支持代理之间的消息传递和事件通知
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
from collections import defaultdict

class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PROGRESS = "task_progress"
    CHAT = "chat"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"

class Message:
    """消息"""
    
    def __init__(self, msg_type: MessageType, sender: str, receiver: str = None,
                 content: str = "", metadata: Dict = None):
        self.id = f"msg-{uuid.uuid4().hex[:8]}"
        self.type = msg_type
        self.sender = sender
        self.receiver = receiver  # None 表示广播
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.read = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "read": self.read
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        msg = cls(
            MessageType(data.get("type", "chat")),
            data.get("sender", ""),
            data.get("receiver"),
            data.get("content", ""),
            data.get("metadata")
        )
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        msg.read = data.get("read", False)
        return msg


class MessageBus:
    """消息总线"""
    
    def __init__(self):
        self.messages: List[Message] = []
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.lock = False  # 简化版本不使用锁
    
    def publish(self, message: Message) -> str:
        """发布消息"""
        self.messages.append(message)
        
        # 通知订阅者
        if message.receiver:
            # 发送给特定接收者
            key = f"{message.receiver}:{message.type.value}"
            if key in self.subscribers:
                for callback in self.subscribers[key]:
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"Error in subscriber: {e}")
        else:
            # 广播
            key = f"broadcast:{message.type.value}"
            if key in self.subscribers:
                for callback in self.subscribers[key]:
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"Error in subscriber: {e}")
        
        return message.id
    
    def subscribe(self, receiver: str, msg_type: MessageType, callback: Callable):
        """订阅消息"""
        key = f"{receiver}:{msg_type.value}"
        self.subscribers[key].append(callback)
    
    def unsubscribe(self, receiver: str, msg_type: MessageType, callback: Callable):
        """取消订阅"""
        key = f"{receiver}:{msg_type.value}"
        if key in self.subscribers:
            try:
                self.subscribers[key].remove(callback)
            except ValueError:
                pass
    
    def get_messages(self, receiver: str = None, msg_type: MessageType = None,
                     unread_only: bool = False) -> List[Message]:
        """获取消息"""
        result = self.messages
        
        if receiver:
            result = [m for m in result if m.receiver == receiver or m.receiver is None]
        
        if msg_type:
            result = [m for m in result if m.type == msg_type]
        
        if unread_only:
            result = [m for m in result if not m.read]
        
        return result
    
    def mark_read(self, message_id: str) -> bool:
        """标记已读"""
        for msg in self.messages:
            if msg.id == message_id:
                msg.read = True
                return True
        return False
    
    def mark_all_read(self, receiver: str) -> int:
        """标记所有消息已读"""
        count = 0
        for msg in self.messages:
            if msg.receiver == receiver and not msg.read:
                msg.read = True
                count += 1
        return count
    
    def clear(self, before: datetime = None):
        """清理消息"""
        if before:
            self.messages = [m for m in self.messages 
                           if datetime.fromisoformat(m.timestamp) > before]
        else:
            self.messages = []


class AgentCommunication:
    """代理通信管理器"""
    
    def __init__(self):
        self.message_bus = MessageBus()
        self.agent_registry: Dict[str, Dict] = {}
    
    def register_agent(self, agent_id: str, agent_info: Dict):
        """注册代理"""
        self.agent_registry[agent_id] = {
            "info": agent_info,
            "online": True,
            "last_seen": datetime.now().isoformat()
        }
    
    def unregister_agent(self, agent_id: str):
        """注销代理"""
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id]["online"] = False
    
    def send_message(self, sender: str, receiver: str, content: str,
                    msg_type: MessageType = MessageType.CHAT,
                    metadata: Dict = None) -> str:
        """发送消息"""
        message = Message(msg_type, sender, receiver, content, metadata)
        return self.message_bus.publish(message)
    
    def broadcast(self, sender: str, content: str,
                  msg_type: MessageType = MessageType.BROADCAST,
                  metadata: Dict = None) -> str:
        """广播消息"""
        message = Message(msg_type, sender, None, content, metadata)
        return self.message_bus.publish(message)
    
    def get_inbox(self, agent_id: str, unread_only: bool = False) -> List[Message]:
        """获取收件箱"""
        return self.message_bus.get_messages(agent_id, unread_only=unread_only)
    
    def get_online_agents(self) -> List[str]:
        """获取在线代理列表"""
        return [aid for aid, info in self.agent_registry.items() 
                if info.get("online", False)]


# 全局通信管理器
_communication = AgentCommunication()

def get_communication() -> AgentCommunication:
    """获取全局通信管理器"""
    return _communication
