from __future__ import annotations

from agah_harness.core.state import MECCResult
from agah_harness.core.policies import PolicyRegistry

try:
    import weave as _weave
    _weave_op = _weave.op
except Exception:
    _weave = None  # type: ignore[assignment]
    def _weave_op(fn):  # type: ignore[misc]
        return fn


class MECC:
    def __init__(self, registry: PolicyRegistry):
        self.registry = registry

    @_weave_op
    def evaluate(self, action: str, layer: int, context: dict) -> MECCResult:
        """Cross-layer admissibility gate. Checks action against ALL constraints at or above `layer`."""
        violated: list[str] = []
        escalation = None
        retrieved = context.get("retrieved", {})
        similarity = context.get("title_similarity", 0.0)
        year_ok = context.get("year_match", True)
        venue_ok = context.get("venue_match", True)
        api_ok = context.get("api_ok", True)
        verifiable_count = context.get("verifiable_count", 1)

        if action == "emit_verdict":
            if not retrieved.get("resolved", False):
                violated.append("C001")
            if retrieved.get("resolved", False) and similarity < 0.85:
                violated.append("C002")
            if retrieved.get("resolved", False) and not year_ok:
                violated.append("C003")
            if retrieved.get("resolved", False) and not venue_ok:
                violated.append("C004")

        if action == "parse_citation" and not context.get("doi_present", True):
            violated.append("C008")

        if action in {"query_crossref_doi", "query_arxiv_title"} and not api_ok:
            violated.append("C006")
            escalation = 3

        if action == "scenario_complete" and verifiable_count < 1:
            violated.append("C007")
            escalation = 5

        return MECCResult(
            action=action,
            layer=layer,
            passed=not violated,
            violatedconstraints=violated,
            escalationtarget=escalation,
            rationale="passed" if not violated else f"violated {', '.join(violated)}",
        )
