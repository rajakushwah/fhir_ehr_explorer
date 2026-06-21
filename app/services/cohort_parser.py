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

COUNTRY_ALIASES = {
    "us": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "united states": "US",
    "united states of america": "US",
    "america": "US",
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
    country: Optional[str] = None
    gender: Optional[str] = None
    patient_id: Optional[str] = None
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
    return text.strip().title()


def _normalize_country(text: str) -> Optional[str]:
    t = text.strip().lower().rstrip(".")
    if not t:
        return None
    if t in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[t]
    if len(t) == 2:
        return t.upper()
    return text.strip().title()


def _clean_phrase(phrase: str) -> str:
    phrase = re.sub(r"\b(patients?|people|all|show\s+me|find|list)\b", "", phrase, flags=re.I)
    phrase = re.sub(r"\s+", " ", phrase).strip(" .,")
    return phrase


def _is_state_token(token: str) -> bool:
    t = token.strip().lower()
    return (
        t in US_STATE_ALIASES
        or token.strip().upper() in US_STATE_ALIASES.values()
        or len(token.strip()) <= 3
    )


def _is_country_token(token: str) -> bool:
    t = token.strip().lower().rstrip(".")
    return t in COUNTRY_ALIASES or len(t) == 2


def _keyword_location_value(text: str, keyword: str) -> Optional[str]:
    pattern = (
        rf"\b{keyword}\s+(?:is|=|:)?\s*"
        r"([A-Za-z][A-Za-z.\s\-']+?)"
        r"(?=\s+\b(?:city|state|region|country|with|and|who|gender)\b|$|\?)"
    )
    match = re.search(pattern, text, re.I)
    return _clean_phrase(match.group(1)) if match else None


def _parse_location_filters(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    city = state = country = None

    city_val = _keyword_location_value(text, "city")
    if city_val:
        city = city_val

    state_val = _keyword_location_value(text, "state") or _keyword_location_value(text, "region")
    if state_val:
        state = _normalize_state(state_val)

    country_val = _keyword_location_value(text, "country")
    if country_val:
        country = _normalize_country(country_val)

    combined = re.search(
        r"(?:in|from|located\s+in|living\s+in)\s+"
        r"([A-Za-z][A-Za-z\s\-']+?)"
        r"(?:,\s*([A-Za-z][A-Za-z\s\-']+?))?"
        r"(?:,\s*([A-Za-z]{2,10}))?"
        r"(?=\s+(?:with|who|and|that|suffering|having)|$|\?)",
        text,
        re.I,
    )
    if combined:
        parts = [_clean_phrase(g) for g in combined.groups() if g and _clean_phrase(g)]
        parts = [p for p in parts if p.lower() not in {"a", "the", "who"}]

        if len(parts) >= 3:
            if not city:
                city = parts[0]
            if not state:
                state = _normalize_state(parts[1])
            if not country:
                country = _normalize_country(parts[2])
        elif len(parts) == 2:
            if _is_country_token(parts[1]):
                if not state:
                    state = _normalize_state(parts[0])
                if not country:
                    country = _normalize_country(parts[1])
            elif _is_state_token(parts[1]):
                if not city:
                    city = parts[0]
                if not state:
                    state = _normalize_state(parts[1])
            else:
                if not city:
                    city = parts[0]
                if not state:
                    state = _normalize_state(parts[1])
        elif len(parts) == 1:
            token = parts[0]
            if _is_country_token(token):
                if not country:
                    country = _normalize_country(token)
            elif _is_state_token(token):
                if not state:
                    state = _normalize_state(token)
            else:
                if not city:
                    city = token

    return city, state, country


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

    city, state, country = _parse_location_filters(raw)
    result.city = city
    result.state = state
    result.country = country

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


def _format_location(parsed: ParsedCohort) -> Optional[str]:
    parts = [p for p in (parsed.city, parsed.state, parsed.country) if p]
    if not parts:
        return None
    return ", ".join(parts)


def build_interpretation(parsed: ParsedCohort) -> str:
    parts = ["Patients"]
    if parsed.patient_id:
        parts.append(f"with ID matching '{parsed.patient_id}'")
    if parsed.gender:
        parts.append(f"({parsed.gender})")
    location = _format_location(parsed)
    if location:
        parts.append(f"in {location}")
    if parsed.condition:
        parts.append(f"with {parsed.condition}")
    if parsed.min_age is not None or parsed.max_age is not None:
        lo = parsed.min_age or 0
        hi = parsed.max_age or "∞"
        parts.append(f"age {lo}–{hi}")
    if len(parts) == 1:
        return "All patients in the database"
    return " ".join(parts)
