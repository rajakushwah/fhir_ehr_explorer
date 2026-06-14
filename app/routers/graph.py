import logging

from fastapi import APIRouter, HTTPException

from app.schemas.graph import (
    ComorbidityRequest,
    ConceptPatientsRequest,
    ExpandRequest,
    NodeDetailRequest,
    NodeNeighborsRequest,
    NodeRelationshipsRequest,
    SimilarPatientsRequest,
)
from app.services.node_detail_service import (
    get_node_detail,
    get_node_neighbors,
    get_node_relationships,
)
from app.services.cohort_graph import (
    RESOURCE_REL,
    _cohort_filter_constrains_region,
    _filters_from_context,
    build_cohort_gender_filters,
    build_cohort_city_filters,
    build_cohort_patients,
    build_cohort_region_filters,
    build_metric_resource_expand,
)
from app.services.expand_service import (
    build_clinical_category_expand,
    build_gender_filters,
    build_patient_clinical_categories,
    build_patient_group_from_concept,
    build_patients,
    build_region_filters,
)
from app.services.graph_connectivity import build_place_patients, build_shared_concept_patients
from app.services.graph_analytics import (
    analyze_comorbidity,
    find_similar_patients,
    get_concept_cohort_patients,
)
from app.utils.neo4j_errors import handle_db_error
from app.utils.timing import timed_step

router = APIRouter(prefix="/graph")
logger = logging.getLogger("graph.expand")


def _is_cohort_context(ctx: dict) -> bool:
    return bool(ctx.get("cohortFilters") or ctx.get("cohortKey"))


def _dispatch_expand(node_type: str, ctx: dict) -> list:
    if (
        node_type in RESOURCE_REL
        and _is_cohort_context(ctx)
        and not ctx.get("patientFhirId")
        and not ctx.get("conceptSystem")
    ):
        return build_metric_resource_expand(node_type, ctx)

    if node_type == "Concept":
        if ctx.get("resourceRel") and ctx.get("originPatientFhirId"):
            return build_shared_concept_patients(ctx)
        rel = ctx.get("resourceRel") or "HAS_CONDITION"
        return build_patient_group_from_concept(ctx["conceptSystem"], ctx["conceptCode"], rel)

    if node_type == "Location" and ctx.get("city"):
        expand_ctx = dict(ctx)
        if ctx.get("originPatientFhirId"):
            expand_ctx["excludePatientFhirId"] = ctx["originPatientFhirId"]
        return build_place_patients(expand_ctx)

    if node_type == "PatientGroup":
        if _is_cohort_context(ctx):
            return build_cohort_gender_filters(ctx)
        return build_gender_filters(ctx["conceptSystem"], ctx["conceptCode"])

    if node_type == "Gender":
        if _is_cohort_context(ctx):
            filters = _filters_from_context(ctx)
            if ctx.get("city") or filters.get("city"):
                return build_cohort_patients(ctx)
            if ctx.get("state") or filters.get("state") or _cohort_filter_constrains_region(filters):
                cities = build_cohort_city_filters(ctx)
                if len(cities) > 1:
                    return cities
                return build_cohort_patients(ctx)
            return build_cohort_region_filters(ctx)
        return build_region_filters(ctx["conceptSystem"], ctx["conceptCode"], ctx.get("gender"))

    if node_type == "Region":
        if _is_cohort_context(ctx):
            return build_cohort_patients(ctx)
        return build_patients(
            ctx["conceptSystem"],
            ctx["conceptCode"],
            ctx.get("gender"),
            ctx.get("state"),
            ctx,
        )

    if node_type == "Patient":
        nodes = build_patient_clinical_categories(ctx["patientFhirId"])
        for n in nodes:
            data = n.get("data") or n
            if data.get("type") == "Location":
                data.setdefault("context", {})["originPatientFhirId"] = ctx["patientFhirId"]
        return nodes

    if node_type == "ClinicalCategory":
        return build_clinical_category_expand(ctx["patientFhirId"], ctx["category"], ctx)

    if node_type in {"Condition", "Observation", "AllergyIntolerance"} and ctx.get("conceptSystem"):
        rel_map = {
            "Condition": "HAS_CONDITION",
            "Observation": "HAS_OBSERVATION",
            "AllergyIntolerance": "HAS_ALLERGY",
        }
        rel = ctx.get("resourceRel") or rel_map.get(node_type, "HAS_CONDITION")
        return build_shared_concept_patients({
            **ctx,
            "resourceRel": rel,
        })

    return []


@router.post("/expand")
def expand(req: ExpandRequest):
    with timed_step(logger, "graph/expand", nodeType=req.nodeType) as metrics:
        try:
            ctx = dict(req.context)
            if req.limit is not None:
                ctx["limit"] = req.limit
            nodes = _dispatch_expand(req.nodeType, ctx)
            metrics["summary"] = f"count={len(nodes)} limit={ctx.get('limit')}"
            message = None
            if not nodes and req.nodeType == "Patient":
                message = (
                    "No clinical data linked to this patient. "
                    "Re-run ingestion: python -m ingestion.cli load-csv-rels"
                )
            return {"nodes": nodes, "message": message}
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


@router.post("/node/detail")
def node_detail(req: NodeDetailRequest):
    with timed_step(logger, "graph/node/detail", nodeType=req.nodeType):
        try:
            return get_node_detail(req.nodeType, dict(req.context), req.meta)
        except Exception as exc:
            handle_db_error(f"graph/node/detail/{req.nodeType}", exc)


@router.post("/node/neighbors")
def node_neighbors(req: NodeNeighborsRequest):
    with timed_step(logger, "graph/node/neighbors", nodeType=req.nodeType):
        try:
            items = get_node_neighbors(
                req.nodeType,
                dict(req.context),
                req.filterType,
                req.limit or 50,
            )
            return {"neighbors": items, "total": len(items)}
        except Exception as exc:
            handle_db_error(f"graph/node/neighbors/{req.nodeType}", exc)


@router.post("/node/relationships")
def node_relationships(req: NodeRelationshipsRequest):
    with timed_step(logger, "graph/node/relationships", nodeType=req.nodeType):
        try:
            items = get_node_relationships(
                req.nodeType,
                dict(req.context),
                req.filterRel,
                req.limit or 50,
            )
            return {"relationships": items, "total": len(items)}
        except Exception as exc:
            handle_db_error(f"graph/node/relationships/{req.nodeType}", exc)


@router.post("/analytics/comorbidity")
def comorbidity_analysis(req: ComorbidityRequest):
    with timed_step(logger, "graph/analytics/comorbidity"):
        try:
            return analyze_comorbidity(
                dict(req.filters),
                min_co_occurrence=req.minCoOccurrence,
                max_concepts=req.maxConcepts,
            )
        except Exception as exc:
            handle_db_error("graph/analytics/comorbidity", exc)


@router.post("/analytics/similar-patients")
def similar_patients(req: SimilarPatientsRequest):
    with timed_step(logger, "graph/analytics/similar-patients", patient=req.patientFhirId):
        try:
            return find_similar_patients(
                req.patientFhirId,
                dict(req.filters),
                limit=req.limit,
            )
        except Exception as exc:
            handle_db_error("graph/analytics/similar-patients", exc)


@router.post("/analytics/concept-patients")
def concept_cohort_patients(req: ConceptPatientsRequest):
    with timed_step(
        logger,
        "graph/analytics/concept-patients",
        code=req.conceptCode,
    ):
        try:
            return get_concept_cohort_patients(
                dict(req.filters),
                req.conceptSystem,
                req.conceptCode,
                concept_label=req.conceptLabel,
            )
        except Exception as exc:
            handle_db_error("graph/analytics/concept-patients", exc)
