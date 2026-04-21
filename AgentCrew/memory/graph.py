"""
Graph memory for entities, relations, and episodes.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now().isoformat()


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: str = "concept"
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "aliases": list(self.aliases),
            "attributes": dict(self.attributes),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class GraphEpisode:
    id: str
    summary: str
    entities: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "entities": list(self.entities),
            "relations": list(self.relations),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


class GraphMemory:
    """Simple persisted graph memory."""

    def __init__(self, storage_path: str = "./data/memory/graph.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.episodes: Dict[str, GraphEpisode] = {}
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        with self.storage_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        self.nodes = {
            item["id"]: GraphNode(**item)
            for item in payload.get("nodes", [])
        }
        self.edges = {
            item["id"]: GraphEdge(**item)
            for item in payload.get("edges", [])
        }
        self.episodes = {
            item["id"]: GraphEpisode(**item)
            for item in payload.get("episodes", [])
        }

    def _save(self):
        payload = {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "episodes": [episode.to_dict() for episode in self.episodes.values()],
        }
        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _find_existing_node(self, name: str) -> Optional[GraphNode]:
        normalized = name.strip().lower()
        for node in self.nodes.values():
            if node.name.lower() == normalized:
                return node
            if normalized in [alias.lower() for alias in node.aliases]:
                return node
        return None

    def add_entity(
        self,
        name: str,
        node_type: str = "concept",
        aliases: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        existing = self._find_existing_node(name)
        if existing:
            if aliases:
                existing.aliases = list(dict.fromkeys(existing.aliases + aliases))
            if attributes:
                existing.attributes.update(attributes)
            existing.updated_at = _now()
            self._save()
            return existing.id

        node_id = f"node-{uuid.uuid4().hex[:10]}"
        node = GraphNode(
            id=node_id,
            name=name,
            node_type=node_type,
            aliases=aliases or [],
            attributes=attributes or {},
        )
        self.nodes[node_id] = node
        self._save()
        return node_id

    def add_relation(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        source_id = source if source in self.nodes else self.add_entity(source)
        target_id = target if target in self.nodes else self.add_entity(target)

        for edge in self.edges.values():
            if edge.source == source_id and edge.target == target_id and edge.relation == relation:
                edge.weight = weight
                edge.metadata.update(metadata or {})
                edge.updated_at = _now()
                self._save()
                return edge.id

        edge_id = f"edge-{uuid.uuid4().hex[:10]}"
        edge = GraphEdge(
            id=edge_id,
            source=source_id,
            target=target_id,
            relation=relation,
            weight=weight,
            metadata=metadata or {},
        )
        self.edges[edge_id] = edge
        self._save()
        return edge_id

    def add_episode(
        self,
        summary: str,
        entities: Optional[List[str]] = None,
        relations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        episode_id = f"episode-{uuid.uuid4().hex[:10]}"
        episode = GraphEpisode(
            id=episode_id,
            summary=summary,
            entities=entities or [],
            relations=relations or [],
            metadata=metadata or {},
        )
        self.episodes[episode_id] = episode
        self._save()
        return episode_id

    def extract_entities_from_text(self, text: str) -> List[str]:
        tokens = re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", text)
        seen = []
        for token in tokens:
            if token not in seen:
                seen.append(token)
        return seen[:10]

    def learn_interaction(
        self,
        summary: str,
        entities: Optional[List[str]] = None,
        relation: str = "co_occurs",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        entities = entities or self.extract_entities_from_text(summary)
        entity_ids = [self.add_entity(name, node_type="entity") for name in entities]
        relation_ids = []

        for index in range(len(entity_ids) - 1):
            relation_ids.append(
                self.add_relation(entity_ids[index], entity_ids[index + 1], relation, metadata=metadata)
            )

        return self.add_episode(summary, entities=entity_ids, relations=relation_ids, metadata=metadata)

    def query_subgraph(self, query: str, depth: int = 1, limit: int = 10) -> Dict[str, Any]:
        matched_nodes = [
            node for node in self.nodes.values()
            if query.lower() in node.name.lower()
            or any(query.lower() in alias.lower() for alias in node.aliases)
        ]

        if not matched_nodes and query:
            extracted = self.extract_entities_from_text(query)
            matched_nodes = [
                node for node in self.nodes.values()
                if node.name in extracted
            ]

        selected = matched_nodes[:limit]
        visited = {node.id for node in selected}
        frontier = list(visited)

        for _ in range(max(depth, 0)):
            next_frontier = []
            for edge in self.edges.values():
                if edge.source in frontier or edge.target in frontier:
                    visited.add(edge.source)
                    visited.add(edge.target)
                    next_frontier.extend([edge.source, edge.target])
            frontier = list(set(next_frontier))

        nodes = [self.nodes[node_id].to_dict() for node_id in visited if node_id in self.nodes][:limit]
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge.to_dict()
            for edge in self.edges.values()
            if edge.source in node_ids and edge.target in node_ids
        ][:limit]
        episodes = [
            episode.to_dict()
            for episode in self.episodes.values()
            if node_ids.intersection(episode.entities)
        ][:limit]

        return {
            "query": query,
            "nodes": nodes,
            "edges": edges,
            "episodes": episodes,
        }

    def get_context(self, query: str, depth: int = 1, limit: int = 8) -> Dict[str, Any]:
        subgraph = self.query_subgraph(query, depth=depth, limit=limit)
        summary_lines = []

        for node in subgraph["nodes"]:
            summary_lines.append(f"- 实体 {node['name']} ({node['node_type']})")
        for edge in subgraph["edges"]:
            source = self.nodes.get(edge["source"])
            target = self.nodes.get(edge["target"])
            if source and target:
                summary_lines.append(f"- 关系 {source.name} -[{edge['relation']}]-> {target.name}")

        subgraph["summary"] = "\n".join(summary_lines)
        return subgraph

    def get_stats(self) -> Dict[str, Any]:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "episodes": len(self.episodes),
        }

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self.episodes.clear()
        self._save()
