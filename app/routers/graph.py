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

router = APIRouter(prefix="/graph")


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
    try:
        nodes = _dispatch_expand(req.nodeType, req.context)
        return {"nodes": nodes}
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required context field for {req.nodeType}: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Expand failed for {req.nodeType}: {exc}",
        ) from exc
