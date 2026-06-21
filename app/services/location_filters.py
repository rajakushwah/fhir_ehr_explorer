"""Shared patient location filter helpers (city, state, country)."""

from __future__ import annotations

from typing import Any, Optional


def patient_location_where(p_alias: str = "p") -> str:
    """AND clauses for gender + city + state + country + patient ID (all optional)."""
    return f"""
    WHERE ($gender IS NULL OR {p_alias}.gender = $gender)
      AND ($state IS NULL OR toLower(coalesce({p_alias}.state,'')) CONTAINS toLower($state)
           OR toLower(coalesce({p_alias}.state,'')) = toLower($state))
      AND ($city IS NULL OR toLower(coalesce({p_alias}.city,'')) CONTAINS toLower($city)
           OR toLower(coalesce({p_alias}.city,'')) = toLower($city))
      AND ($country IS NULL OR toLower(coalesce({p_alias}.country,'')) CONTAINS toLower($country)
           OR toLower(coalesce({p_alias}.country,'')) = toLower($country))
      AND ($patientId IS NULL OR
           (toInteger($patientId) IS NOT NULL AND {p_alias}.patientId = toInteger($patientId)) OR
           toLower({p_alias}.fhirId) CONTAINS toLower($patientId))
    """


def patient_location_drill_where(p_alias: str = "p") -> str:
    """Extra drill-down predicates for gender/region/city nodes."""
    return f"""
    AND ($nodeGender IS NULL OR {p_alias}.gender = $nodeGender)
    AND ($nodeState IS NULL OR toLower(coalesce({p_alias}.state,'')) CONTAINS toLower($nodeState)
         OR toLower(coalesce({p_alias}.state,'')) = toLower($nodeState))
    AND ($nodeCity IS NULL OR toLower(coalesce({p_alias}.city,'')) CONTAINS toLower($nodeCity)
         OR toLower(coalesce({p_alias}.city,'')) = toLower($nodeCity))
    AND ($nodeCountry IS NULL OR toLower(coalesce({p_alias}.country,'')) CONTAINS toLower($nodeCountry)
         OR toLower(coalesce({p_alias}.country,'')) = toLower($nodeCountry))
    """


def location_params(
    *,
    gender: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    patient_id: Optional[str] = None,
    concept_system: Optional[str] = None,
    concept_code: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "gender": gender,
        "state": state,
        "city": city,
        "country": country,
        "patientId": patient_id.strip() if patient_id else None,
        "conceptSystem": concept_system,
        "conceptCode": concept_code,
    }
    if extra:
        params.update(extra)
    return params


def filters_from_parsed(parsed) -> dict[str, Any]:
    return {
        "gender": parsed.gender,
        "state": parsed.state,
        "city": parsed.city,
        "country": getattr(parsed, "country", None),
        "patientId": getattr(parsed, "patient_id", None),
    }
