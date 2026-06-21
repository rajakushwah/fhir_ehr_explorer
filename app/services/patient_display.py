"""Shared patient display helpers for graph labels and inspector text."""

from __future__ import annotations

from typing import Any, Optional


def patient_graph_label(props: dict[str, Any]) -> str:
    """Primary label for graph nodes — patient name, not ID."""
    name = (props.get("name") or "").strip()
    if name:
        return name
    short_id = props.get("patientId")
    if short_id is not None:
        return f"Patient #{short_id}"
    gender = props.get("gender") or "?"
    location = props.get("city") or props.get("state") or "?"
    return f"Patient ({gender}, {location})"


def patient_graph_full_label(props: dict[str, Any]) -> str:
    """Tooltip / inspector — ID plus name when both exist."""
    name = (props.get("name") or "").strip()
    short_id = props.get("patientId")
    if name and short_id is not None:
        return f"#{short_id} · {name}"
    return patient_graph_label(props)


def order_patient_properties(props: dict[str, Any]) -> dict[str, Any]:
    if not props:
        return props
    ordered: dict[str, Any] = {}
    for key in ("patientId", "name", "fhirId"):
        if key in props and props[key] is not None:
            ordered[key] = props[key]
    for key, value in props.items():
        if key not in ordered:
            ordered[key] = value
    return ordered
