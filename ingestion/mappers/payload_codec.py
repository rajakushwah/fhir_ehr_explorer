"""Serialize GraphPayload for multiprocessing and bulk CSV export."""

from __future__ import annotations

from typing import Any

from ingestion.mappers.bundle_mapper import GraphPayload


def payload_to_dict(payload: GraphPayload) -> dict[str, Any]:
    return {
        "nodes": payload.nodes,
        "patient_links": payload.patient_links,
        "concept_links": payload.concept_links,
        "encounter_links": payload.encounter_links,
        "org_links": payload.org_links,
        "location_links": payload.location_links,
    }


def payload_from_dict(data: dict[str, Any]) -> GraphPayload:
    return GraphPayload(
        nodes=data.get("nodes") or {},
        patient_links=data.get("patient_links") or [],
        concept_links=data.get("concept_links") or [],
        encounter_links=data.get("encounter_links") or [],
        org_links=data.get("org_links") or [],
        location_links=data.get("location_links") or [],
    )
