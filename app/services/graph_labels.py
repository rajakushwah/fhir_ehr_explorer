"""Helpers for graph node display labels."""

from __future__ import annotations

from typing import Any

from app.services.patient_display import patient_graph_full_label


def short_label(text: str, max_len: int = 26) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def wrap_graph_node(data: dict[str, Any]) -> dict[str, Any]:
    label = data.get("label") or data.get("type") or "Node"
    node_type = data.get("type")
    patient_props = {
        "name": data.get("name"),
        "patientId": data.get("patientId"),
        "gender": data.get("gender"),
        "city": data.get("city"),
        "state": data.get("state"),
    }
    if node_type == "Patient":
        short = short_label(label, max_len=22)
        full = data.get("fullLabel") or patient_graph_full_label(patient_props)
    else:
        short = short_label(label)
        full = data.get("fullLabel") or label
    data = {**data, "label": label, "shortLabel": short, "fullLabel": full}
    return {"data": data}
