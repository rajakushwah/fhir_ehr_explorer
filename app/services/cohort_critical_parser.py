"""Detect critical / abnormal patient cohort queries from natural language."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from app.data.observation_thresholds import THRESHOLD_RULES
from app.services.cohort_parser import ParsedCohort

Severity = Literal["critical", "abnormal"]

CRITICAL_TRIGGERS = re.compile(
    r"\b("
    r"critical(?:ly)?(?:\s+ill|\s+patients?)?|"
    r"unstable\s+patients?|"
    r"patients?\s+(?:with\s+)?(?:critical|abnormal|out\s+of\s+range|elevated|high\s+risk)|"
    r"(?:give\s+me|show|find|list|get)\s+(?:all\s+)?(?:the\s+)?critical|"
    r"abnormal\s+(?:lab|labs|value|values|result|results|vital|vitals|reading|readings)"
    r")\b",
    re.I,
)

ABNORMAL_ONLY = re.compile(
    r"\b(abnormal|out\s+of\s+range|elevated|high\s+(?:glucose|bp|blood pressure|cholesterol))\b",
    re.I,
)


@dataclass
class ParsedCriticalSearch:
    is_critical_search: bool = False
    severity: Severity = "critical"
    lab_codes: list[str] = field(default_factory=list)


def _match_lab_codes(text: str) -> list[str]:
    lower = text.lower()
    codes: list[str] = []
    for rule in THRESHOLD_RULES:
        if any(kw in lower for kw in rule.keywords):
            codes.append(rule.code)
    return list(dict.fromkeys(codes))


def parse_critical_query(text: str, parsed: ParsedCohort) -> ParsedCriticalSearch:
    result = ParsedCriticalSearch()
    if not text or not text.strip():
        return result

    if not CRITICAL_TRIGGERS.search(text):
        return result

    result.is_critical_search = True
    result.severity = "abnormal" if ABNORMAL_ONLY.search(text) and not re.search(
        r"\bcritical\b", text, re.I
    ) else "critical"

    lab_codes = _match_lab_codes(text)
    if lab_codes:
        result.lab_codes = lab_codes

    return result


def build_critical_interpretation(critical: ParsedCriticalSearch, parsed: ParsedCohort) -> str:
    severity_label = "Critical" if critical.severity == "critical" else "Abnormal"
    parts = [f"{severity_label} patients"]

    if critical.lab_codes:
        labels = []
        seen: set[str] = set()
        for rule in THRESHOLD_RULES:
            if rule.code in critical.lab_codes and rule.label not in seen:
                labels.append(rule.label)
                seen.add(rule.label)
        if labels:
            parts.append(f"({', '.join(labels[:3])}{'…' if len(labels) > 3 else ''})")

    if parsed.gender:
        parts.append(f"· {parsed.gender}")
    location_parts = [p for p in (parsed.city, parsed.state, parsed.country) if p]
    if location_parts:
        parts.append(f"· {', '.join(location_parts)}")
    if parsed.condition:
        parts.append(f"· with {parsed.condition}")

    parts.append("· values exceeding clinical thresholds")
    return " ".join(parts)
