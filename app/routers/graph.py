import logging

from fastapi import APIRouter, HTTPException

from app.schemas.graph import ExpandRequest
from app.services.expand_service import (
    build_clinical_category_expand,
    build_gender_filters,
    build_patient_clinical_categories,
    build_patient_group_from_concept,
    build_patients,
    build_region_filters,
)
from app.utils.neo4j_errors import handle_db_error
from app.utils.timing import timed_step

router = APIRouter(prefix="/graph")
logger = logging.getLogger("graph.expand")


def _dispatch_expand(node_type: str, ctx: dict) -> list:
    if node_type == "Concept":
        return build_patient_group_from_concept(ctx["conceptSystem"], ctx["conceptCode"])

    if node_type == "PatientGroup":
        return build_gender_filters(ctx["conceptSystem"], ctx["conceptCode"])

    if node_type == "Gender":
        return build_region_filters(ctx["conceptSystem"], ctx["conceptCode"], ctx.get("gender"))

    if node_type == "Region":
        return build_patients(
            ctx["conceptSystem"],
            ctx["conceptCode"],
            ctx.get("gender"),
            ctx.get("state"),
        )

    if node_type == "Patient":
        return build_patient_clinical_categories(ctx["patientFhirId"])

    if node_type == "ClinicalCategory":
        return build_clinical_category_expand(ctx["patientFhirId"], ctx["category"])

    if node_type in {"Condition", "Observation", "AllergyIntolerance"} and ctx.get("conceptSystem"):
        return build_patient_group_from_concept(ctx["conceptSystem"], ctx["conceptCode"])

    return []


@router.post("/expand")
def expand(req: ExpandRequest):
    with timed_step(logger, "graph/expand", nodeType=req.nodeType) as metrics:
        try:
            nodes = _dispatch_expand(req.nodeType, req.context)
            metrics["summary"] = f"count={len(nodes)}"
            return {"nodes": nodes}
        except KeyError as exc:
            logger.error(
                "[FAIL]  graph/expand | nodeType=%s | missing field %s",
                req.nodeType,
                exc,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Missing required context field for {req.nodeType}: {exc}",
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            handle_db_error(f"graph/expand/{req.nodeType}", exc)
