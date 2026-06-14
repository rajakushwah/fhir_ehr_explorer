"""Lightweight graph analytics for concept co-occurrence (no GDS required)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def connected_communities(
    node_ids: list[str],
    edges: list[dict[str, Any]],
    *,
    min_weight: int = 1,
) -> dict[str, int]:
    """Assign community ids via connected components on weighted edges."""
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        weight = int(edge.get("weight") or 0)
        if weight < min_weight:
            continue
        source = edge["sourceId"]
        target = edge["targetId"]
        adjacency[source].append(target)
        adjacency[target].append(source)

    communities: dict[str, int] = {}
    community_id = 0
    for node in node_ids:
        if node in communities:
            continue
        queue: deque[str] = deque([node])
        communities[node] = community_id
        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, []):
                if neighbor in communities:
                    continue
                communities[neighbor] = community_id
                queue.append(neighbor)
        community_id += 1
    return communities


def betweenness_centrality(
    node_ids: list[str],
    edges: list[dict[str, Any]],
) -> dict[str, float]:
    """Brandes betweenness for small concept graphs."""
    nodes = list(node_ids)
    if len(nodes) < 3:
        return {node: 0.0 for node in nodes}

    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        source = edge["sourceId"]
        target = edge["targetId"]
        adjacency[source].append(target)
        adjacency[target].append(source)

    betweenness = {node: 0.0 for node in nodes}
    for source in nodes:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {node: [] for node in nodes}
        sigma: dict[str, int] = {node: 0 for node in nodes}
        dist: dict[str, int] = {node: -1 for node in nodes}
        sigma[source] = 1
        dist[source] = 0
        queue: deque[str] = deque([source])

        while queue:
            vertex = queue.popleft()
            stack.append(vertex)
            for neighbor in adjacency.get(vertex, []):
                if dist[neighbor] < 0:
                    dist[neighbor] = dist[vertex] + 1
                    queue.append(neighbor)
                if dist[neighbor] == dist[vertex] + 1:
                    sigma[neighbor] += sigma[vertex]
                    predecessors[neighbor].append(vertex)

        delta = {node: 0.0 for node in nodes}
        while stack:
            vertex = stack.pop()
            for pred in predecessors[vertex]:
                if sigma[vertex] > 0:
                    delta[pred] += (sigma[pred] / sigma[vertex]) * (1.0 + delta[vertex])
            if vertex != source:
                betweenness[vertex] += delta[vertex]

    scale = 2.0 / ((len(nodes) - 1) * (len(nodes) - 2)) if len(nodes) > 2 else 1.0
    return {node: value * scale for node, value in betweenness.items()}


def community_labels(
    communities: dict[str, int],
    concepts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize each community with top concepts by prevalence."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for concept in concepts:
        community_id = int(concept.get("communityId") or 0)
        grouped[community_id].append(concept)

    summaries: list[dict[str, Any]] = []
    for community_id in sorted(grouped):
        members = sorted(
            grouped[community_id],
            key=lambda item: (-int(item.get("patientCount") or 0), item.get("label") or ""),
        )
        top = members[:4]
        label_parts = [member.get("label") or member.get("code") for member in top[:2]]
        label = " + ".join(part for part in label_parts if part) or f"Cluster {community_id + 1}"
        summaries.append({
            "id": community_id,
            "label": label,
            "conceptCount": len(members),
            "topConcepts": [
                {
                    "system": member.get("system"),
                    "code": member.get("code"),
                    "label": member.get("label"),
                    "patientCount": member.get("patientCount"),
                }
                for member in top
            ],
            "maxPrevalence": max(int(member.get("patientCount") or 0) for member in members),
        })
    summaries.sort(key=lambda item: (-item["maxPrevalence"], item["label"]))
    return summaries
