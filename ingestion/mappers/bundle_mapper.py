"""Map a Synthea FHIR bundle to graph write payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ingestion.config import MapOptions, get_map_options
from ingestion.fhir_utils import (
    extension_value,
    first_coding,
    observation_value,
    period_bounds,
    ref_id,
    status_text,
)
from ingestion.parsers.bundle_parser import BundleIndex

SKIP_TYPES = {
    "Bundle",
    "Provenance",
    "Claim",
    "ExplanationOfBenefit",
    "DocumentReference",
    "SupplyDelivery",
    "Medication",
    "MedicationAdministration",
    "CareTeam",
    "CarePlan",
    "Device",
    "ImagingStudy",
    "PractitionerRole",
}

HAS_REL = {
    "Condition": "HAS_CONDITION",
    "Observation": "HAS_OBSERVATION",
    "Encounter": "HAS_ENCOUNTER",
    "Procedure": "HAS_PROCEDURE",
    "MedicationRequest": "HAS_MEDICATION",
    "AllergyIntolerance": "HAS_ALLERGY",
    "Immunization": "HAS_IMMUNIZATION",
    "DiagnosticReport": "HAS_DIAGNOSTIC_REPORT",
}


@dataclass
class GraphPayload:
    nodes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    patient_links: list[dict[str, str]] = field(default_factory=list)
    concept_links: list[dict[str, str]] = field(default_factory=list)
    encounter_links: list[dict[str, str]] = field(default_factory=list)
    org_links: list[dict[str, str]] = field(default_factory=list)
    location_links: list[dict[str, str]] = field(default_factory=list)


def _add_node(payload: GraphPayload, label: str, fhir_id: str, props: dict) -> None:
    payload.nodes.setdefault(label, []).append({"fhirId": fhir_id, **props})


def _observation_category(resource: dict) -> str:
    category = status_text((resource.get("category") or [{}])[0] if resource.get("category") else None)
    return (category or "").lower().replace(" ", "-")


def _keep_observation(resource: dict, options: MapOptions) -> bool:
    category = _observation_category(resource)
    if category in options.skip_observation_categories:
        return False
    if options.keep_observation_categories and category not in options.keep_observation_categories:
        return False

    sys, code, _ = first_coding(resource.get("code"))
    value_num, _, value_string = observation_value(resource)
    if not code and value_num is None and not value_string:
        return False
    return True


def _filter_observations(resources: list[dict], options: MapOptions) -> list[dict]:
    kept = [res for res in resources if _keep_observation(res, options)]
    if options.max_observations_per_patient and len(kept) > options.max_observations_per_patient:
        kept.sort(
            key=lambda res: res.get("effectiveDateTime")
            or (res.get("effectivePeriod") or {}).get("start")
            or "",
            reverse=True,
        )
        kept = kept[: options.max_observations_per_patient]
    return kept


def map_bundle(bundle: dict, options: MapOptions | None = None) -> GraphPayload:
    options = options or get_map_options()
    index = BundleIndex(bundle)
    payload = GraphPayload()

    for org in index.by_type.get("Organization", []):
        _add_node(payload, "Organization", org["id"], {"name": (org.get("name") or "")[:200]})

    for loc in index.by_type.get("Location", []):
        addr = loc.get("address") or {}
        _add_node(
            payload,
            "Location",
            loc["id"],
            {
                "name": (loc.get("name") or "")[:200],
                "city": addr.get("city"),
                "state": addr.get("state"),
            },
        )

    for pract in index.by_type.get("Practitioner", []):
        names = pract.get("name") or []
        display = names[0].get("text") if names else None
        _add_node(payload, "Practitioner", pract["id"], {"name": (display or "")[:200]})

    for patient in index.by_type.get("Patient", []):
        pid = patient["id"]
        addr = (patient.get("address") or [{}])[0]
        _add_node(
            payload,
            "Patient",
            pid,
            {
                "gender": patient.get("gender"),
                "birthDate": patient.get("birthDate"),
                "city": addr.get("city"),
                "state": addr.get("state"),
                "postalCode": addr.get("postalCode"),
                "race": extension_value(patient.get("extension") or [], "us-core-race"),
                "ethnicity": extension_value(patient.get("extension") or [], "us-core-ethnicity"),
            },
        )

    for enc in index.by_type.get("Encounter", []):
        eid = enc["id"]
        start, end = period_bounds(enc.get("period"))
        enc_types = enc.get("type") or []
        type_sys, type_code, type_display = first_coding(enc_types[0] if enc_types else None)
        _add_node(
            payload,
            "Encounter",
            eid,
            {
                "status": enc.get("status"),
                "class": (enc.get("class") or {}).get("code"),
                "periodStart": start,
                "periodEnd": end,
                "typeDisplay": type_display,
                "typeSystem": type_sys,
                "typeCode": type_code,
            },
        )
        patient_fhir_id = ref_id(enc.get("subject"))
        if patient_fhir_id:
            payload.patient_links.append(
                {"rel": "HAS_ENCOUNTER", "patientFhirId": patient_fhir_id, "resourceFhirId": eid}
            )
        org_id = ref_id(enc.get("serviceProvider"))
        if org_id:
            payload.org_links.append({"encounterFhirId": eid, "orgFhirId": org_id})
        for loc_ref in enc.get("location") or []:
            loc_id = ref_id(loc_ref.get("location"))
            if loc_id:
                payload.location_links.append({"encounterFhirId": eid, "locationFhirId": loc_id})

    def _map_clinical(resource_type: str, resources: list[dict], code_field: str = "code") -> None:
        rel = HAS_REL[resource_type]
        for res in resources:
            rid = res["id"]
            props: dict[str, Any] = {"status": res.get("status")}

            if resource_type == "Condition":
                props.update(
                    {
                        "clinicalStatus": status_text(res.get("clinicalStatus")),
                        "verificationStatus": status_text(res.get("verificationStatus")),
                        "onsetDateTime": res.get("onsetDateTime") or (res.get("onsetPeriod") or {}).get("start"),
                        "abatementDateTime": res.get("abatementDateTime"),
                    }
                )
            elif resource_type == "Observation":
                value_num, value_unit, value_string = observation_value(res)
                props.update(
                    {
                        "status": res.get("status"),
                        "effectiveDateTime": res.get("effectiveDateTime")
                        or (res.get("effectivePeriod") or {}).get("start"),
                        "valueNum": value_num,
                        "valueUnit": value_unit,
                        "valueString": value_string,
                        "category": _observation_category(res),
                    }
                )
            elif resource_type == "Procedure":
                props["performedDateTime"] = res.get("performedDateTime") or (
                    (res.get("performedPeriod") or {}).get("start")
                )
            elif resource_type == "MedicationRequest":
                props["authoredOn"] = res.get("authoredOn")
                props["intent"] = res.get("intent")
                codeable = res.get("medicationCodeableConcept")
                if codeable:
                    sys, code, display = first_coding(codeable)
                    props["medSystem"] = sys
                    props["medCode"] = code
                    props["medDisplay"] = display
            elif resource_type == "AllergyIntolerance":
                props.update(
                    {
                        "clinicalStatus": status_text(res.get("clinicalStatus")),
                        "verificationStatus": status_text(res.get("verificationStatus")),
                        "type": res.get("type"),
                        "category": ",".join(res.get("category") or []) or None,
                    }
                )
            elif resource_type == "Immunization":
                props["occurrenceDateTime"] = res.get("occurrenceDateTime")
            elif resource_type == "DiagnosticReport":
                props["effectiveDateTime"] = res.get("effectiveDateTime") or (
                    (res.get("effectivePeriod") or {}).get("start")
                )
                props["category"] = status_text((res.get("category") or [{}])[0] if res.get("category") else None)

            _add_node(payload, resource_type, rid, props)

            patient_fhir_id = ref_id(res.get("subject") or res.get("patient"))
            if patient_fhir_id:
                payload.patient_links.append(
                    {"rel": rel, "patientFhirId": patient_fhir_id, "resourceFhirId": rid}
                )

            codeable = res.get(code_field)
            if resource_type == "MedicationRequest" and not codeable:
                codeable = res.get("medicationCodeableConcept")
            sys, code, display = first_coding(codeable)
            if sys and code:
                payload.concept_links.append(
                    {
                        "resourceType": resource_type,
                        "resourceFhirId": rid,
                        "system": sys,
                        "code": code,
                        "display": display or code,
                    }
                )

            enc_id = ref_id(res.get("encounter") or (res.get("context") or {}).get("encounter"))
            if enc_id:
                payload.encounter_links.append(
                    {"resourceType": resource_type, "resourceFhirId": rid, "encounterFhirId": enc_id}
                )

    clinical_types = (
        "Condition",
        "Observation",
        "Procedure",
        "MedicationRequest",
        "AllergyIntolerance",
        "Immunization",
        "DiagnosticReport",
    )
    for rtype in clinical_types:
        resources = index.by_type.get(rtype, [])
        if rtype == "Observation":
            resources = _filter_observations(resources, options)
        _map_clinical(rtype, resources)

    return payload
