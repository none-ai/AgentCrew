"""
Graph memory for entities, relations, aliases, and episodes.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _now() -> str:
    return datetime.now().isoformat()


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _parse_time(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


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
    confidence: float = 0.5
    observations: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    last_observed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "confidence": self.confidence,
            "observations": self.observations,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_observed_at": self.last_observed_at,
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
    """Persisted graph memory with alias resolution and observation tracking."""

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

    def _dedupe(self, values: List[str]) -> List[str]:
        result = []
        seen = set()
        for value in values:
            if not value:
                continue
            normalized = _normalize(value)
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append(value)
        return result

    def _find_existing_node(self, name: str) -> Optional[GraphNode]:
        normalized = _normalize(name)
        for node in self.nodes.values():
            if _normalize(node.name) == normalized:
                return node
            if normalized in {_normalize(alias) for alias in node.aliases}:
                return node
        return None

    def resolve_entity(self, value: str) -> Optional[GraphNode]:
        if value in self.nodes:
            return self.nodes[value]
        return self._find_existing_node(value)

    def add_alias(self, name: str, alias: str) -> str:
        node = self.resolve_entity(name)
        if not node:
            raise KeyError(name)
        aliases = node.aliases + [alias]
        if _normalize(alias) != _normalize(node.name):
            node.aliases = self._dedupe(aliases)
        node.updated_at = _now()
        self._save()
        return node.id

    def merge_entities(self, canonical: str, duplicate: str) -> str:
        canonical_node = self.resolve_entity(canonical)
        duplicate_node = self.resolve_entity(duplicate)
        if not canonical_node or not duplicate_node:
            raise KeyError(f"cannot merge {canonical!r} and {duplicate!r}")
        if canonical_node.id == duplicate_node.id:
            return canonical_node.id

        canonical_node.aliases = self._dedupe(canonical_node.aliases + [duplicate_node.name] + duplicate_node.aliases)
        canonical_node.attributes.update(duplicate_node.attributes)
        canonical_node.updated_at = _now()

        for edge in self.edges.values():
            if edge.source == duplicate_node.id:
                edge.source = canonical_node.id
            if edge.target == duplicate_node.id:
                edge.target = canonical_node.id
            edge.updated_at = _now()
            edge.last_observed_at = edge.updated_at

        for episode in self.episodes.values():
            if duplicate_node.id in episode.entities:
                episode.entities = [canonical_node.id if item == duplicate_node.id else item for item in episode.entities]

        del self.nodes[duplicate_node.id]
        self._consolidate_edges()
        self._save()
        return canonical_node.id

    def _consolidate_edges(self):
        consolidated: Dict[Tuple[str, str, str], GraphEdge] = {}
        for edge in self.edges.values():
            key = (edge.source, edge.target, edge.relation)
            if key not in consolidated:
                consolidated[key] = edge
                continue

            existing = consolidated[key]
            total_observations = existing.observations + edge.observations
            existing.weight = max(existing.weight, edge.weight)
            existing.confidence = (
                (existing.confidence * existing.observations) + (edge.confidence * edge.observations)
            ) / total_observations
            existing.observations = total_observations
            existing.metadata.update(edge.metadata)
            existing.updated_at = max(existing.updated_at, edge.updated_at)
            existing.last_observed_at = max(existing.last_observed_at, edge.last_observed_at)

        self.edges = {edge.id: edge for edge in consolidated.values()}

    def add_entity(
        self,
        name: str,
        node_type: str = "concept",
        aliases: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        existing = self.resolve_entity(name)
        if existing:
            merged_aliases = existing.aliases + (aliases or [])
            if _normalize(name) != _normalize(existing.name):
                merged_aliases.append(name)
            existing.aliases = self._dedupe(merged_aliases)
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
            aliases=self._dedupe(aliases or []),
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
        confidence: float = 0.6,
    ) -> str:
        source_node = self.resolve_entity(source)
        target_node = self.resolve_entity(target)
        source_id = source_node.id if source_node else self.add_entity(source)
        target_id = target_node.id if target_node else self.add_entity(target)
        timestamp = _now()

        for edge in self.edges.values():
            if edge.source == source_id and edge.target == target_id and edge.relation == relation:
                total_observations = edge.observations + 1
                edge.weight = max(edge.weight, weight)
                edge.confidence = ((edge.confidence * edge.observations) + confidence) / total_observations
                edge.observations = total_observations
                edge.metadata.update(metadata or {})
                edge.updated_at = timestamp
                edge.last_observed_at = timestamp
                self._save()
                return edge.id

        edge_id = f"edge-{uuid.uuid4().hex[:10]}"
        edge = GraphEdge(
            id=edge_id,
            source=source_id,
            target=target_id,
            relation=relation,
            weight=weight,
            confidence=confidence,
            metadata=metadata or {},
            updated_at=timestamp,
            last_observed_at=timestamp,
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
                self.add_relation(entity_ids[index], entity_ids[index + 1], relation, metadata=metadata, confidence=0.7)
            )

        return self.add_episode(summary, entities=entity_ids, relations=relation_ids, metadata=metadata)

    def _match_nodes(self, query: str) -> List[Tuple[GraphNode, float]]:
        normalized = _normalize(query)
        matched: List[Tuple[GraphNode, float]] = []
        for node in self.nodes.values():
            score = 0.0
            if _normalize(node.name) == normalized:
                score = 3.0
            elif normalized in _normalize(node.name):
                score = 2.0
            elif any(normalized == _normalize(alias) for alias in node.aliases):
                score = 2.8
            elif any(normalized in _normalize(alias) for alias in node.aliases):
                score = 1.8

            if score <= 0:
                continue

            freshness = max((_parse_time(node.updated_at) - datetime(1970, 1, 1)).total_seconds(), 0)
            score += freshness / 1_000_000_000
            matched.append((node, score))

        matched.sort(key=lambda item: item[1], reverse=True)
        return matched

    def query_subgraph(self, query: str, depth: int = 1, limit: int = 10) -> Dict[str, Any]:
        matched_nodes = self._match_nodes(query)

        if not matched_nodes and query:
            extracted = self.extract_entities_from_text(query)
            for item in extracted:
                matched_nodes.extend(self._match_nodes(item))

        selected = [node for node, _ in matched_nodes[:limit]]
        visited: Set[str] = {node.id for node in selected}
        frontier = list(visited)

        for _ in range(max(depth, 0)):
            next_frontier = []
            for edge in self.edges.values():
                if edge.source in frontier or edge.target in frontier:
                    visited.add(edge.source)
                    visited.add(edge.target)
                    next_frontier.extend([edge.source, edge.target])
            frontier = list(set(next_frontier))

        ranked_nodes = sorted(
            (self.nodes[node_id] for node_id in visited if node_id in self.nodes),
            key=lambda node: _parse_time(node.updated_at),
            reverse=True,
        )[:limit]
        node_ids = {node.id for node in ranked_nodes}
        ranked_edges = sorted(
            (
                edge for edge in self.edges.values()
                if edge.source in node_ids and edge.target in node_ids
            ),
            key=lambda edge: (edge.confidence, edge.observations, _parse_time(edge.last_observed_at)),
            reverse=True,
        )[:limit]
        ranked_episodes = sorted(
            (
                episode for episode in self.episodes.values()
                if node_ids.intersection(episode.entities)
            ),
            key=lambda episode: _parse_time(episode.created_at),
            reverse=True,
        )[:limit]

        return {
            "query": query,
            "nodes": [node.to_dict() for node in ranked_nodes],
            "edges": [edge.to_dict() for edge in ranked_edges],
            "episodes": [episode.to_dict() for episode in ranked_episodes],
        }

    def get_context(self, query: str, depth: int = 1, limit: int = 8) -> Dict[str, Any]:
        subgraph = self.query_subgraph(query, depth=depth, limit=limit)
        summary_lines = []

        for node in subgraph["nodes"]:
            alias_suffix = f" aliases={', '.join(node['aliases'])}" if node["aliases"] else ""
            summary_lines.append(f"- 实体 {node['name']} ({node['node_type']}){alias_suffix}")
        for edge in subgraph["edges"]:
            source = self.nodes.get(edge["source"])
            target = self.nodes.get(edge["target"])
            if source and target:
                summary_lines.append(
                    f"- 关系 {source.name} -[{edge['relation']}]-> {target.name} "
                    f"(confidence={edge['confidence']:.2f}, observations={edge['observations']})"
                )

        subgraph["summary"] = "\n".join(summary_lines)
        return subgraph

    def export(self) -> Dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "episodes": [episode.to_dict() for episode in self.episodes.values()],
        }

    def get_stats(self) -> Dict[str, Any]:
        alias_count = sum(len(node.aliases) for node in self.nodes.values())
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "episodes": len(self.episodes),
            "aliases": alias_count,
            "observations": sum(edge.observations for edge in self.edges.values()),
        }

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self.episodes.clear()
        self._save()
