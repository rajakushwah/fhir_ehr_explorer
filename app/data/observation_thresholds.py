"""Clinical observation thresholds for critical / abnormal patient detection.

Uses LOINC codes commonly present in Synthea FHIR bundles. Thresholds are
reference ranges for demo purposes — tune per deployment or ingest FHIR
referenceRange when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["critical", "abnormal"]
Direction = Literal["high", "low"]


@dataclass(frozen=True)
class ObservationThreshold:
    code: str
    label: str
    direction: Direction
    critical: float
    abnormal: float
    unit: str = ""
    system: str = "http://loinc.org"
    keywords: tuple[str, ...] = ()


# Latest observation per code is compared against these thresholds.
THRESHOLD_RULES: tuple[ObservationThreshold, ...] = (
    ObservationThreshold(
        "2339-0", "Glucose", "high", critical=400, abnormal=200, unit="mg/dL",
        keywords=("glucose", "blood sugar"),
    ),
    ObservationThreshold(
        "4548-4", "HbA1c", "high", critical=9.0, abnormal=7.0, unit="%",
        keywords=("hba1c", "a1c", "hemoglobin a1c"),
    ),
    ObservationThreshold(
        "8480-6", "Systolic BP", "high", critical=180, abnormal=140, unit="mmHg",
        keywords=("systolic", "blood pressure"),
    ),
    ObservationThreshold(
        "8462-4", "Diastolic BP", "high", critical=120, abnormal=90, unit="mmHg",
        keywords=("diastolic",),
    ),
    ObservationThreshold(
        "8867-4", "Heart rate", "high", critical=120, abnormal=100, unit="/min",
        keywords=("heart rate", "pulse"),
    ),
    ObservationThreshold(
        "8867-4", "Heart rate", "low", critical=40, abnormal=50, unit="/min",
        keywords=("bradycardia", "low heart rate"),
    ),
    ObservationThreshold(
        "2160-0", "Creatinine", "high", critical=3.0, abnormal=1.5, unit="mg/dL",
        keywords=("creatinine", "kidney"),
    ),
    ObservationThreshold(
        "2093-3", "Total cholesterol", "high", critical=300, abnormal=240, unit="mg/dL",
        keywords=("cholesterol", "lipid"),
    ),
    ObservationThreshold(
        "2089-1", "LDL cholesterol", "high", critical=190, abnormal=160, unit="mg/dL",
        keywords=("ldl",),
    ),
    ObservationThreshold(
        "2571-8", "Triglycerides", "high", critical=500, abnormal=200, unit="mg/dL",
        keywords=("triglyceride",),
    ),
    ObservationThreshold(
        "39156-5", "BMI", "high", critical=40, abnormal=30, unit="kg/m2",
        keywords=("bmi", "body mass index"),
    ),
    ObservationThreshold(
        "2708-6", "Oxygen saturation", "low", critical=88, abnormal=92, unit="%",
        keywords=("oxygen", "spo2", "o2 sat"),
    ),
    ObservationThreshold(
        "8310-5", "Body temperature", "high", critical=103.0, abnormal=100.4, unit="F",
        keywords=("fever", "temperature"),
    ),
    ObservationThreshold(
        "8310-5", "Body temperature", "low", critical=95.0, abnormal=96.5, unit="F",
        keywords=("hypothermia",),
    ),
    ObservationThreshold(
        "29463-7", "Body weight", "high", critical=350, abnormal=300, unit="lbs",
        keywords=("weight", "obesity"),
    ),
)


def rules_for_codes(codes: set[str] | None = None) -> list[ObservationThreshold]:
    if not codes:
        return list(THRESHOLD_RULES)
    return [r for r in THRESHOLD_RULES if r.code in codes]


def rule_to_cypher_param(rule: ObservationThreshold, severity: Severity) -> dict:
    threshold = rule.critical if severity == "critical" else rule.abnormal
    return {
        "system": rule.system,
        "code": rule.code,
        "label": rule.label,
        "direction": rule.direction,
        "threshold": threshold,
        "unit": rule.unit,
        "severity": severity,
    }
