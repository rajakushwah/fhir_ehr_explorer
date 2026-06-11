"""Shared patient display helpers for graph labels and inspector text."""

from __future__ import annotations

from typing import Any, Optional


def patient_graph_label(props: dict[str, Any]) -> str:
    name = props.get("name")
    if name:
        return str(name)
    gender = props.get("gender") or "?"
    location = props.get("city") or props.get("state") or "?"
    return f"Patient ({gender}, {location})"


def order_patient_properties(props: dict[str, Any]) -> dict[str, Any]:
    if not props or "name" not in props:
        return props
    ordered = {"name": props["name"]}
    for key, value in props.items():
        if key != "name":
            ordered[key] = value
    return ordered
