"""Parse Synthea patient Bundle JSON files."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator


class BundleIndex:
    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.by_url: dict[str, dict] = {}
        self.by_id: dict[str, dict] = {}
        self.by_type: dict[str, list[dict]] = defaultdict(list)

        for entry in bundle.get("entry") or []:
            resource = entry.get("resource")
            if not resource or "resourceType" not in resource:
                continue
            rid = resource.get("id")
            full_url = entry.get("fullUrl") or (f"urn:uuid:{rid}" if rid else None)
            if full_url:
                self.by_url[full_url] = resource
            if rid:
                self.by_id[rid] = resource
            self.by_type[resource["resourceType"]].append(resource)

    def resolve(self, reference: dict | str | None) -> dict | None:
        rid = self.resolve_id(reference)
        return self.by_id.get(rid) if rid else None

    def resolve_id(self, reference: dict | str | None) -> str | None:
        from ingestion.fhir_utils import ref_id

        if not reference:
            return None
        ref = reference if isinstance(reference, str) else reference.get("reference")
        if not ref:
            return None
        if ref in self.by_url:
            res = self.by_url[ref]
            return res.get("id")
        rid = ref_id(reference if isinstance(reference, dict) else {"reference": reference})
        return rid


def load_bundle(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_bundle_files(input_dir: Path) -> Iterator[Path]:
    yield from sorted(input_dir.glob("*.json"))
