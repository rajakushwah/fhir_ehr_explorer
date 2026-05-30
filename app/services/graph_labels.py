"""Helpers for graph node display labels."""

from __future__ import annotations

from typing import Any


def short_label(text: str, max_len: int = 26) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def wrap_graph_node(data: dict[str, Any]) -> dict[str, Any]:
    label = data.get("label") or data.get("type") or "Node"
    data = {**data, "label": label, "shortLabel": short_label(label), "fullLabel": label}
    return {"data": data}
