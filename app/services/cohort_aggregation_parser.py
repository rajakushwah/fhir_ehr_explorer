"""Detect aggregation intent in natural-language cohort queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.services.cohort_parser import ParsedCohort

COUNT_TRIGGERS = re.compile(
    r"\b("
    r"count|how many|total number|number of|what(?:'s| is) the (?:total )?count|"
    r"give me (?:a |the )?count|show (?:me )?(?:the )?count"
    r")\b",
    re.I,
)

AVG_TRIGGERS = re.compile(
    r"\b(average|avg|mean)\b",
    re.I,
)

TARGET_PATTERNS = [
    (re.compile(r"\ballerg(?:y|ies)\b", re.I), "AllergyIntolerance", "allergies"),
    (re.compile(r"\bobservations?\b", re.I), "Observation", "observations"),
    (re.compile(r"\bencounters?\b", re.I), "Encounter", "encounters"),
    (re.compile(r"\bconditions?\b", re.I), "Condition", "conditions"),
    (re.compile(r"\bconcepts?\b", re.I), "Concept", "concepts"),
    (re.compile(r"\bpatients?\b", re.I), "Patient", "patients"),
]

GROUP_PATTERNS = [
    (re.compile(r"\bby gender\b", re.I), "gender"),
    (re.compile(r"\bby state\b", re.I), "state"),
    (re.compile(r"\bby city\b", re.I), "city"),
    (re.compile(r"\bper patient\b", re.I), "patient"),
]


@dataclass
class ParsedAggregation:
    is_aggregation: bool = False
    metric: str = "count"
    target: str = "Patient"
    target_label: str = "patients"
    group_by: Optional[str] = None


def parse_aggregation_query(text: str, parsed: ParsedCohort) -> ParsedAggregation:
    lower = text.strip().lower()
    result = ParsedAggregation()

    is_count = bool(COUNT_TRIGGERS.search(lower))
    is_avg = bool(AVG_TRIGGERS.search(lower))
    if not is_count and not is_avg:
        return result

    result.is_aggregation = True
    result.metric = "avg" if is_avg and not is_count else "count"

    for pattern, label, name in TARGET_PATTERNS:
        if pattern.search(lower):
            result.target = label
            result.target_label = name
            break
    else:
        result.target = "Patient"
        result.target_label = "patients"

    for pattern, field in GROUP_PATTERNS:
        if pattern.search(lower):
            result.group_by = field
            break

    if not result.group_by:
        m = re.search(r"\bby\s+(gender|state|city|patient)\b", lower)
        if m:
            result.group_by = m.group(1)

    return result


def build_aggregation_interpretation(
    agg: ParsedAggregation,
    parsed: ParsedCohort,
) -> str:
    metric = "Average" if agg.metric == "avg" else "Count"
    parts = [f"{metric} of {agg.target_label}"]

    if parsed.gender:
        parts.append(f"({parsed.gender})")
    if parsed.state:
        parts.append(f"in {parsed.state}")
    elif parsed.city:
        parts.append(f"in {parsed.city}")
    if parsed.condition:
        parts.append(f"with {parsed.condition}")
    if agg.group_by and agg.group_by != "patient":
        parts.append(f"by {agg.group_by}")
    elif agg.group_by == "patient":
        parts.append("per patient")

    return " ".join(parts)
