from __future__ import annotations


def route_capability(parsed: dict) -> str:
    doi = (parsed.get("doi") or "").lower()
    title = (parsed.get("title") or "").lower()
    if "arxiv" in doi or "arxiv" in title:
        return "crossref_or_arxiv"
    if doi:
        return "crossref"
    return "fixture_only"
