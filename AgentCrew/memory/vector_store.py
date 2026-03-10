"""
向量存储模块
支持 ChromaDB 和 FAISS 两种向量数据库
"""
import os
import sys
import time
import logging
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# 导入 call_logger
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from call_logger import get_logger, CallStatus
except ImportError:
    from ..call_logger import get_logger, CallStatus

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class VectorStoreBase(ABC):
    """向量存储基类"""
    
    @abstractmethod
    def add(self, items: List[MemoryItem]) -> bool:
        """添加记忆"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """语义搜索"""
        pass
    
    @abstractmethod
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取单个记忆"""
        pass
    
    @abstractmethod
    def update(self, item_id: str, content: str = None, metadata: Dict = None) -> bool:
        """更新记忆"""
        pass
    
    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """获取记忆数量"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有记忆"""
        pass


class InMemoryVectorStore(VectorStoreBase):
    """内存向量存储（简单实现，用于测试）"""
    
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.items: Dict[str, MemoryItem] = {}
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """初始化嵌入模型（简化版）"""
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("使用 SentenceTransformer 进行向量化")
        except ImportError:
            logger.warning("SentenceTransformer 未安装，使用简单哈希作为向量化")
            self.encoder = None
    
    def _encode(self, text: str) -> List[float]:
        """将文本编码为向量"""
        if self.encoder:
            return self.encoder.encode(text).tolist()
        else:
            # 简单哈希作为替代
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            # 转换为固定维度的向量
            vector = []
            for i in range(self.dim):
                vector.append(((hash_val >> i) & 1) * 2 - 1)
            return vector
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)
    
    def add(self, items: List[MemoryItem]) -> bool:
        """添加记忆"""
        try:
            for item in items:
                if item.embedding is None:
                    item.embedding = self._encode(item.content)
                self.items[item.id] = item
            return True
        except Exception as e:
            logger.error(f"添加记忆失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """语义搜索"""
        try:
            query_embedding = self._encode(query)
            
            # 计算相似度
            similarities = []
            for item in self.items.values():
                if item.embedding:
                    sim = self._cosine_similarity(query_embedding, item.embedding)
                    similarities.append((item, sim))
            
            # 排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return [item for item, _ in similarities[:top_k]]
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return self.items.get(item_id)
    
    def update(self, item_id: str, content: str = None, metadata: Dict = None) -> bool:
        """更新记忆"""
        item = self.items.get(item_id)
        if not item:
            return False
        
        if content:
            item.content = content
            item.embedding = self._encode(content)
        
        if metadata:
            item.metadata.update(metadata)
        
        return True
    
    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False
    
    def count(self) -> int:
        """获取数量"""
        return len(self.items)
    
    def clear(self) -> bool:
        """清空"""
        self.items.clear()
        return True


class ChromaVectorStore(VectorStoreBase):
    """ChromaDB 向量存储"""
    
    def __init__(self, persist_directory: str = "./data/memory/chroma"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """初始化 ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="agent_memory",
                metadata={"description": "Agent memory storage"}
            )
            
            logger.info(f"ChromaDB 初始化成功: {self.persist_directory}")
            
        except ImportError:
            logger.warning("ChromaDB 未安装，回退到内存存储")
            self.client = None
            self.collection = None
    
    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        if self.client is None:
            return InMemoryVectorStore()
        
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("SentenceTransformer 未安装，使用 ChromaDB 默认嵌入")
            self.encoder = None
    
    def _encode(self, texts: List[str]) -> List[List[float]]:
        """编码文本"""
        if self.encoder:
            return self.encoder.encode(texts).tolist()
        return None
    
    def add(self, items: List[MemoryItem]) -> bool:
        """添加记忆"""
        try:
            if self.collection is None:
                logger.error("ChromaDB 未初始化")
                return False
            
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for item in items:
                ids.append(item.id)
                documents.append(item.content)
                metadatas.append(item.metadata)
                
                if item.embedding:
                    embeddings.append(item.embedding)
                elif self.encoder:
                    embeddings.append(self._encode([item.content])[0])
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings if embeddings else None
            )
            
            return True
        except Exception as e:
            logger.error(f"添加记忆到 ChromaDB 失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """语义搜索"""
        try:
            if self.collection is None:
                return []
            
            # 编码查询
            query_embedding = None
            if self.encoder:
                query_embedding = self._encode([query])[0]
            
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                query_embeddings=[query_embedding] if query_embedding else None
            )
            
            items = []
            if results and results.get("ids"):
                for i, item_id in enumerate(results["ids"][0]):
                    items.append(MemoryItem(
                        id=item_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                        embedding=results["embeddings"][0][i] if results.get("embeddings") else None
                    ))
            
            return items
        except Exception as e:
            logger.error(f"ChromaDB 搜索失败: {e}")
            return []
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        try:
            if self.collection is None:
                return None
            
            results = self.collection.get(ids=[item_id])
            
            if results and results.get("ids"):
                return MemoryItem(
                    id=results["ids"][0],
                    content=results["documents"][0],
                    metadata=results["metadatas"][0] if results.get("metadatas") else {},
                    embedding=results["embeddings"][0] if results.get("embeddings") else None
                )
            return None
        except Exception as e:
            logger.error(f"获取记忆失败: {e}")
            return None
    
    def update(self, item_id: str, content: str = None, metadata: Dict = None) -> bool:
        """更新记忆"""
        try:
            if self.collection is None:
                return False
            
            update_data = {}
            if content:
                update_data["documents"] = [content]
            if metadata:
                update_data["metadatas"] = [metadata]
            
            if update_data:
                self.collection.update(ids=[item_id], **update_data)
            
            return True
        except Exception as e:
            logger.error(f"更新记忆失败: {e}")
            return False
    
    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        try:
            if self.collection is None:
                return False
            
            self.collection.delete(ids=[item_id])
            return True
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
    
    def count(self) -> int:
        """获取数量"""
        try:
            if self.collection is None:
                return 0
            return self.collection.count()
        except:
            return 0
    
    def clear(self) -> bool:
        """清空"""
        try:
            if self.collection:
                self.client.delete_collection("agent_memory")
                self.collection = self.client.get_or_create_collection(
                    name="agent_memory",
                    metadata={"description": "Agent memory storage"}
                )
            return True
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return False


class FAISSVectorStore(VectorStoreBase):
    """FAISS 向量存储"""
    
    def __init__(self, index_path: str = "./data/memory/faiss"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index = None
        self.items: Dict[int, MemoryItem] = {}
        self.id_mapping: Dict[str, int] = {}
        self._next_id = 0
        self._initialize()
    
    def _initialize(self):
        """初始化 FAISS"""
        try:
            import faiss
            import numpy as np
            
            # 创建索引（简化版，使用内积）
            dimension = 384  # 与 SentenceTransformer 输出维度匹配
            self.index = faiss.IndexFlatIP(dimension)
            self.np = np
            self.faiss = faiss
            
            logger.info("FAISS 索引初始化成功")
            
            # 加载已存在的索引
            self._load_index()
            
        except ImportError:
            logger.warning("FAISS 未安装，回退到内存存储")
            self.index = None
    
    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        if self.index is None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("SentenceTransformer 未安装")
            self.encoder = None
    
    def _encode(self, texts: List[str]) -> List[List[float]]:
        """编码文本"""
        if self.encoder:
            embeddings = self.encoder.encode(texts)
            # 归一化
            norms = self.np.linalg.norm(embeddings, axis=1, keepdims=True)
            return (embeddings / norms).tolist()
        return None
    
    def add(self, items: List[MemoryItem]) -> bool:
        """添加记忆"""
        try:
            if self.index is None:
                logger.error("FAISS 未初始化")
                return False
            
            embeddings = []
            for item in items:
                if item.embedding is None:
                    if self.encoder:
                        item.embedding = self._encode([item.content])[0]
                    else:
                        continue
                
                # 添加到映射
                self.id_mapping[item.id] = self._next_id
                self.items[self._next_id] = item
                
                # 添加到索引
                embedding = self.np.array([item.embedding], dtype='float32')
                self.index.add(embedding)
                self._next_id += 1
            
            # 保存索引
            self._save_index()
            
            return True
        except Exception as e:
            logger.error(f"添加记忆到 FAISS 失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """语义搜索"""
        try:
            if self.index is None or self.index.ntotal == 0:
                return []
            
            # 编码查询
            if self.encoder:
                query_embedding = self._encode([query])[0]
            else:
                return []
            
            # 搜索
            query_vector = self.np.array([query_embedding], dtype='float32')
            distances, indices = self.index.search(query_vector, top_k)
            
            # 获取结果
            results = []
            for idx in indices[0]:
                if idx >= 0 and idx in self.items:
                    results.append(self.items[idx])
            
            return results
        except Exception as e:
            logger.error(f"FAISS 搜索失败: {e}")
            return []
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        idx = self.id_mapping.get(item_id)
        if idx is not None:
            return self.items.get(idx)
        return None
    
    def update(self, item_id: str, content: str = None, metadata: Dict = None) -> bool:
        """更新记忆（FAISS 不支持更新，需要重新添加）"""
        item = self.get(item_id)
        if not item:
            return False
        
        if content:
            item.content = content
            if self.encoder:
                item.embedding = self._encode([content])[0]
        
        if metadata:
            item.metadata.update(metadata)
        
        # FAISS 更新需要删除后重新添加，这里简化处理
        return True
    
    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        # FAISS 不支持删除，这里标记但不实际删除
        item = self.get(item_id)
        if item:
            item.metadata["deleted"] = True
            return True
        return False
    
    def count(self) -> int:
        """获取数量"""
        if self.index:
            return self.index.ntotal
        return len(self.items)
    
    def clear(self) -> bool:
        """清空"""
        try:
            if self.index:
                self.index.reset()
            self.items.clear()
            self.id_mapping.clear()
            self._next_id = 0
            
            # 删除保存的索引
            index_file = self.index_path / "index.faiss"
            meta_file = self.index_path / "metadata.json"
            
            if index_file.exists():
                index_file.unlink()
            if meta_file.exists():
                meta_file.unlink()
            
            return True
        except Exception as e:
            logger.error(f"清空 FAISS 失败: {e}")
            return False
    
    def _save_index(self):
        """保存索引"""
        try:
            if self.index:
                faiss.write_index(self.index, str(self.index_path / "index.faiss"))
                
                # 保存元数据
                metadata = {
                    "id_mapping": self.id_mapping,
                    "next_id": self._next_id,
                    "items": {
                        str(k): {
                            "id": v.id,
                            "content": v.content,
                            "metadata": v.metadata,
                            "created_at": v.created_at
                        }
                        for k, v in self.items.items()
                    }
                }
                
                with open(self.index_path / "metadata.json", 'w') as f:
                    json.dump(metadata, f)
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def _load_index(self):
        """加载索引"""
        try:
            index_file = self.index_path / "index.faiss"
            meta_file = self.index_path / "metadata.json"
            
            if index_file.exists() and meta_file.exists():
                self.index = faiss.read_index(str(index_file))
                
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                self.id_mapping = metadata.get("id_mapping", {})
                self._next_id = metadata.get("next_id", 0)
                
                items_data = metadata.get("items", {})
                for k, v in items_data.items():
                    self.items[int(k)] = MemoryItem(**v)
                
                logger.info(f"加载了 {len(self.items)} 条 MemoryItem(**v记忆")
        except Exception as e:
            logger.error(f"加载索引失败: {e}")


def get_vector_store(
    backend: str = "chroma",
    persist_directory: str = "./data/memory"
) -> VectorStoreBase:
    """
    获取向量存储实例
    
    Args:
        backend: 后端类型 "chroma", "faiss", "memory"
        persist_directory: 持久化目录
        
    Returns:
        向量存储实例
    """
    if backend == "chroma":
        return ChromaVectorStore(persist_directory)
    elif backend == "faiss":
        return FAISSVectorStore(persist_directory)
    else:
        return InMemoryVectorStore()


class VectorStore:
    """向量存储包装类"""
    
    def __init__(self, backend: str = "chroma", persist_directory: str = "./data/memory"):
        self.backend = get_vector_store(backend, persist_directory)
        self._call_logger = get_logger()
    
    def add_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
        memory_id: Optional[str] = None
    ) -> Optional[str]:
        """添加记忆"""
        import uuid
        
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="vector_store",
            action="add_memory",
            params={"content_length": len(content), "memory_id": memory_id}
        )
        
        memory_id = memory_id or str(uuid.uuid4())
        
        item = MemoryItem(
            id=memory_id,
            content=content,
            metadata=metadata
        )
        
        result = self.backend.add([item])
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"memory_id": memory_id if result else None},
            status=CallStatus.SUCCESS if result else CallStatus.FAILED,
            duration_ms=duration_ms
        )
        
        if result:
            return memory_id
        return None
    
    def search_memories(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索记忆"""
        start_time = time.time()
        call_id = self._call_logger.log_call_start(
            source="vector_store",
            action="search_memories",
            params={"query": query, "top_k": top_k}
        )
        
        results = self.backend.search(query, top_k)
        
        # 应用过滤器
        if filters:
            results = [
                r for r in results
                if all(r.metadata.get(k) == v for k, v in filters.items())
            ]
        
        duration_ms = (time.time() - start_time) * 1000
        self._call_logger.log_call_end(
            call_id,
            result={"results_count": len(results)},
            status=CallStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        return [
            {
                "id": r.id,
                "content": r.content,
                "metadata": r.metadata,
                "created_at": r.created_at
            }
            for r in results
        ]
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆"""
        item = self.backend.get(memory_id)
        if item:
            return {
                "id": item.id,
                "content": item.content,
                "metadata": item.metadata,
                "created_at": item.created_at
            }
        return None
    
    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新记忆"""
        return self.backend.update(memory_id, content, metadata)
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.backend.delete(memory_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": self.backend.count(),
            "backend": type(self.backend).__name__
        }
    
    def clear_all(self) -> bool:
        """清空所有记忆"""
        return self.backend.clear()
