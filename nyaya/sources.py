"""Only bundled, individually verified claims can be presented as legal guidance."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE_PATH = Path(__file__).resolve().parent.parent / "data" / "sources.json"


def load_sources() -> dict[str, dict]:
    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    return {source["id"]: source for source in payload["sources"]}


def verified_guidance(items: list[dict]) -> list[dict]:
    """Use the stored claim's actual text, never a model's citation-shaped prose.

    Unsourced practical suggestions may pass through, but cannot masquerade as a
    sourced legal claim. Invalid source/claim pairs raise rather than appear in UI.
    """
    sources = load_sources()
    result = []
    for item in items:
        source_id, claim_id = item.get("source_id"), item.get("claim_id")
        if not source_id and not claim_id:
            result.append({"text": item["text"], "type": "practical"})
            continue
        source = sources.get(source_id)
        claims = {claim["id"]: claim for claim in source["claims"]} if source else {}
        if claim_id not in claims:
            raise ValueError("Unverified source and claim combination")
        result.append({"text": claims[claim_id]["text"], "type": "verified",
                       "source": source, "claim_id": claim_id})
    return result
