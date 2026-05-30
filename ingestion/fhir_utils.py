"""Shared FHIR R4 extraction helpers for Synthea bundles."""

from __future__ import annotations

from typing import Any, Optional


def first_coding(codeable: Optional[dict]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not codeable:
        return None, None, None
    text = codeable.get("text")
    coding = codeable.get("coding") or []
    if coding:
        c = coding[0]
        return c.get("system"), c.get("code"), c.get("display") or text
    return None, None, text


def ref_id(reference: Optional[dict | str]) -> Optional[str]:
    if not reference:
        return None
    if isinstance(reference, str):
        ref = reference
    else:
        ref = reference.get("reference") or ""
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return ref.split("urn:uuid:", 1)[1]
    if "/" in ref:
        return ref.rsplit("/", 1)[-1]
    return ref


def extension_value(extensions: list, url_suffix: str) -> Optional[str]:
    for ext in extensions or []:
        if url_suffix in ext.get("url", ""):
            for inner in ext.get("extension") or []:
                if inner.get("url") == "text":
                    return inner.get("valueString")
                coding = inner.get("valueCoding") or {}
                if coding.get("display"):
                    return coding.get("display")
            if "valueString" in ext:
                return ext.get("valueString")
            if "valueCode" in ext:
                return ext.get("valueCode")
    return None


def status_text(status_obj: Any) -> Optional[str]:
    if status_obj is None:
        return None
    if isinstance(status_obj, str):
        return status_obj
    if isinstance(status_obj, dict):
        for c in status_obj.get("coding") or []:
            if c.get("code"):
                return c.get("code")
        return status_obj.get("text")
    return str(status_obj)


def observation_value(resource: dict) -> tuple[Optional[float], Optional[str], Optional[str]]:
    vq = resource.get("valueQuantity") or {}
    if vq.get("value") is not None:
        try:
            return float(vq["value"]), vq.get("unit"), None
        except (TypeError, ValueError):
            pass
    if resource.get("valueString"):
        return None, None, resource["valueString"]
    if resource.get("valueBoolean") is not None:
        return None, None, str(resource["valueBoolean"])
    if resource.get("valueInteger") is not None:
        return float(resource["valueInteger"]), None, None
    components = resource.get("component") or []
    if components:
        parts = []
        for comp in components[:3]:
            _, _, display = first_coding(comp.get("code"))
            cv = comp.get("valueQuantity") or {}
            if cv.get("value") is not None:
                parts.append(f"{display or 'value'}={cv['value']}{cv.get('unit') or ''}")
        if parts:
            return None, None, "; ".join(parts)
    return None, None, None


def period_bounds(period: Optional[dict]) -> tuple[Optional[str], Optional[str]]:
    if not period:
        return None, None
    return period.get("start"), period.get("end")
