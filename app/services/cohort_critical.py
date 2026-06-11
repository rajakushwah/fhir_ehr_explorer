"""Find patients with critical or abnormal observation values."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.data.observation_thresholds import (
    ObservationThreshold,
    Severity,
    rule_to_cypher_param,
    rules_for_codes,
)
from app.schemas.cohort import CriticalFinding, PatientSummary
from app.services.cohort_critical_parser import ParsedCriticalSearch
from app.services.cohort_parser import ParsedCohort
from app.services.location_filters import location_params, patient_location_where


def _age_from_birth(birth_date: Optional[str]) -> Optional[int]:
    if not birth_date:
        return None
    try:
        born = date.fromisoformat(birth_date[:10])
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return None


def _active_rules(critical: ParsedCriticalSearch) -> list[ObservationThreshold]:
    code_set = set(critical.lab_codes) if critical.lab_codes else None
    return rules_for_codes(code_set)


def _cypher_rules(critical: ParsedCriticalSearch) -> list[dict[str, Any]]:
    rules = _active_rules(critical)
    params: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rule in rules:
        key = (rule.code, rule.direction, critical.severity)
        if key in seen:
            continue
        seen.add(key)
        params.append(rule_to_cypher_param(rule, critical.severity))
    return params


def count_critical_patients(
    session,
    parsed: ParsedCohort,
    critical: ParsedCriticalSearch,
    concept: Optional[dict[str, Any]] = None,
) -> int:
    rules = _cypher_rules(critical)
    if not rules:
        return 0

    row = session.run(
        _count_cypher(concept),
        rules=rules,
        **location_params(
            gender=parsed.gender,
            state=parsed.state,
            city=parsed.city,
            country=parsed.country,
            concept_system=concept["system"] if concept else None,
            concept_code=concept["code"] if concept else None,
        ),
    ).single()
    return int(row["total"]) if row else 0


def search_critical_patients(
    session,
    parsed: ParsedCohort,
    critical: ParsedCriticalSearch,
    limit: int,
    offset: int = 0,
    concept: Optional[dict[str, Any]] = None,
) -> tuple[list[PatientSummary], int]:
    rules = _cypher_rules(critical)
    if not rules:
        return [], 0

    rows = session.run(
        _search_cypher(concept),
        rules=rules,
        **location_params(
            gender=parsed.gender,
            state=parsed.state,
            city=parsed.city,
            country=parsed.country,
            concept_system=concept["system"] if concept else None,
            concept_code=concept["code"] if concept else None,
            extra={"limit": limit, "offset": offset},
        ),
    )

    patients: list[PatientSummary] = []
    for r in rows:
        age = _age_from_birth(r.get("birthDate"))
        if parsed.min_age is not None and (age is None or age < parsed.min_age):
            continue
        if parsed.max_age is not None and (age is None or age > parsed.max_age):
            continue

        raw_findings = r.get("findings") or []
        findings: list[CriticalFinding] = []
        for f in raw_findings:
            if f.get("value") is None:
                continue
            findings.append(CriticalFinding(
                label=f.get("label") or "Observation",
                value=float(f["value"]),
                unit=f.get("unit"),
                severity=f.get("severity") or critical.severity,
                direction=f.get("direction") or "high",
                date=f.get("date"),
                code=f.get("code"),
            ))

        patients.append(PatientSummary(
            fhirId=r["fhirId"],
            gender=r.get("gender"),
            state=r.get("state"),
            city=r.get("city"),
            country=r.get("country"),
            birthDate=r.get("birthDate"),
            age=age,
            conditions=r.get("conditions") or [],
            isCritical=True,
            criticalFindings=findings,
        ))

    total = count_critical_patients(session, parsed, critical, concept)
    if parsed.min_age is not None or parsed.max_age is not None:
        total = len(patients)

    return patients, total


def _patient_prefix(concept: Optional[dict[str, Any]]) -> str:
    if concept:
        return """
        MATCH (concept:Concept {system: $conceptSystem, code: $conceptCode})
        MATCH (concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
        """
    return "MATCH (p:Patient)"


def _patient_where() -> str:
    return patient_location_where()


def _threshold_match() -> str:
    return """
    AND (
      (rule.direction = 'high' AND latest.valueNum >= rule.threshold) OR
      (rule.direction = 'low' AND latest.valueNum <= rule.threshold)
    )
    """


def _search_cypher(concept: Optional[dict[str, Any]]) -> str:
    return (
        _patient_prefix(concept)
        + _patient_where()
        + """
    UNWIND $rules AS rule
    MATCH (p)-[:HAS_OBSERVATION]->(o:Observation)-[:CODED_AS]->(c:Concept)
    WHERE c.system = rule.system AND c.code = rule.code
      AND o.valueNum IS NOT NULL
    WITH p, rule, o
    ORDER BY o.effectiveDateTime DESC
    WITH p, rule, collect(o)[0] AS latest
    WHERE latest IS NOT NULL
    """
        + _threshold_match()
        + """
    WITH p, collect(DISTINCT {
      label: rule.label,
      value: latest.valueNum,
      unit: coalesce(latest.valueUnit, rule.unit),
      date: latest.effectiveDateTime,
      severity: rule.severity,
      direction: rule.direction,
      code: rule.code
    }) AS findings
    OPTIONAL MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(cx:Concept)
    WITH p, findings, collect(DISTINCT coalesce(cx.display, cx.text))[..5] AS conditions
    RETURN p.fhirId AS fhirId, p.gender AS gender, p.state AS state,
           p.city AS city, p.country AS country, p.birthDate AS birthDate, conditions, findings
    ORDER BY size(findings) DESC, p.fhirId
    SKIP $offset LIMIT $limit
    """
    )


def _count_cypher(concept: Optional[dict[str, Any]]) -> str:
    return (
        _patient_prefix(concept)
        + _patient_where()
        + """
    UNWIND $rules AS rule
    MATCH (p)-[:HAS_OBSERVATION]->(o:Observation)-[:CODED_AS]->(c:Concept)
    WHERE c.system = rule.system AND c.code = rule.code
      AND o.valueNum IS NOT NULL
    WITH p, rule, o
    ORDER BY o.effectiveDateTime DESC
    WITH p, rule, collect(o)[0] AS latest
    WHERE latest IS NOT NULL
    """
        + _threshold_match()
        + """
    RETURN count(DISTINCT p) AS total
    """
    )
