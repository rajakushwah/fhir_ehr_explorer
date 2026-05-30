"""Parse natural-language cohort queries into structured filters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

US_STATE_ALIASES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

CONDITION_HINTS = [
    "diabetes", "prediabetes", "asthma", "hypertension", "lupus", "covid",
    "arthritis", "cancer", "obesity", "heart", "pain", "allergy", "glucose",
    "depression", "anxiety", "pneumonia", "bronchitis", "sinusitis",
    "pregnant", "pregnancy", "diabetic", "hypertensive",
]

CONDITION_ALIASES = {
    "pregnant": "pregnancy",
    "preg": "pregnancy",
    "diabetic": "diabetes",
}

GENDER_PATTERNS = [
    (re.compile(r"\b(female|women|woman|girls?)\b", re.I), "female"),
    (re.compile(r"\b(male|men|man|boys?)\b", re.I), "male"),
]

LOCATION_PATTERNS = [
    re.compile(r"\b(?:who\s+(?:is|are)\s+)?from\s+([A-Za-z]{2,30})(?:\s|$|\?)", re.I),
    re.compile(r"(?:location\s+is|located\s+in|living\s+in|from|in)\s+([a-z][a-z\s]{1,30}?)(?:\s+(?:and|with|who|that|suffering|having)|$)", re.I),
    re.compile(r"(?:state|region|city)\s+(?:is|=|:)\s*([a-z][a-z\s]{1,30})", re.I),
]

CONDITION_PATTERNS = [
    re.compile(r"(?:suffering\s+from|diagnosed\s+with|having|with|who\s+have)\s+([a-z][a-z0-9\s\-]{2,40}?)(?:\s+(?:and|in|who|from)|$)", re.I),
    re.compile(r"who\s+(?:is|are|was|were)\s+(?!from\b)([a-z][a-z0-9\-]{2,30})(?:\s|$|\?)", re.I),
    re.compile(r"(?:patients?\s+)?(?:that\s+are|that\s+is|who\s+is|who\s+are)\s+(?!from\b)([a-z][a-z0-9\-]{2,30})(?:\s|$|\?)", re.I),
    re.compile(r"(?:condition|disease|disorder)\s+(?:is|=|:)\s*([a-z][a-z0-9\s\-]{2,40})", re.I),
]


@dataclass
class ParsedCohort:
    condition: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None


def _normalize_state(text: str) -> Optional[str]:
    t = text.strip().lower()
    if not t:
        return None
    if t.upper() in US_STATE_ALIASES.values():
        return t.upper()
    if t in US_STATE_ALIASES:
        return US_STATE_ALIASES[t]
    return text.strip().title() if len(text.strip()) <= 3 else text.strip().title()


def _clean_phrase(phrase: str) -> str:
    phrase = re.sub(r"\b(patients?|people|all|show\s+me|find|list)\b", "", phrase, flags=re.I)
    phrase = re.sub(r"\s+", " ", phrase).strip(" .,")
    return phrase


def parse_natural_query(text: str) -> ParsedCohort:
    raw = text.strip()
    lower = raw.lower()
    result = ParsedCohort()

    for pattern, gender in GENDER_PATTERNS:
        if pattern.search(lower):
            result.gender = gender
            break

    age_range = re.search(r"(?:age|aged)\s+(?:between\s+)?(\d{1,3})\s*(?:-|to|and)\s*(\d{1,3})", lower)
    if age_range:
        result.min_age = int(age_range.group(1))
        result.max_age = int(age_range.group(2))
    else:
        over = re.search(r"(?:over|above|older\s+than)\s+(\d{1,3})", lower)
        under = re.search(r"(?:under|below|younger\s+than)\s+(\d{1,3})", lower)
        if over:
            result.min_age = int(over.group(1))
        if under:
            result.max_age = int(under.group(1))

    for pattern in LOCATION_PATTERNS:
        m = pattern.search(raw)
        if m:
            loc = _clean_phrase(m.group(1))
            if loc and loc.lower() not in {"a", "the", "who"}:
                normalized = _normalize_state(loc)
                if len(loc) <= 3 or loc.upper() in US_STATE_ALIASES.values() or loc.lower() in US_STATE_ALIASES:
                    result.state = normalized
                else:
                    result.city = loc
                break

    for pattern in CONDITION_PATTERNS:
        m = pattern.search(raw)
        if m:
            cond = _clean_phrase(m.group(1))
            if cond:
                result.condition = cond
                break

    if not result.condition:
        for hint in CONDITION_HINTS:
            if re.search(rf"\b{re.escape(hint)}\b", lower):
                result.condition = CONDITION_ALIASES.get(hint, hint)
                break

    return result


def build_interpretation(parsed: ParsedCohort) -> str:
    parts = ["Patients"]
    if parsed.gender:
        parts.append(f"({parsed.gender})")
    if parsed.state:
        parts.append(f"in {parsed.state}")
    elif parsed.city:
        parts.append(f"in {parsed.city}")
    if parsed.condition:
        parts.append(f"with {parsed.condition}")
    if parsed.min_age is not None or parsed.max_age is not None:
        lo = parsed.min_age or 0
        hi = parsed.max_age or "∞"
        parts.append(f"age {lo}–{hi}")
    if len(parts) == 1:
        return "All patients in the database"
    return " ".join(parts)
