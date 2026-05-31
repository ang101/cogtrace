from __future__ import annotations

import json
import re
from pathlib import Path

from agah_harness.core.consensus import consensus_status
from agah_harness.core.policies import PolicyRegistry
from agah_harness.core.state import (
    CitationInput,
    CitationVerdict,
    EvidenceItem,
    FailureRecord,
    FailureType,
    HarnessState,
    MECCResult,
    VerdictStatus,
)
from agah_harness.core.trace import TraceEmitter

try:
    import weave as _weave
    _weave_op = _weave.op
except Exception:
    _weave = None  # type: ignore[assignment]
    def _weave_op(fn):  # type: ignore[misc]
        return fn

_WILDCARD_PATTERN = re.compile(r"\b(all|everything|\*|%)\b", re.I)
_OPERATION_PATTERN = re.compile(
    r"^(DELETE|DROP|RESTART|STOP|KILL|TRUNCATE|REMOVE|UPDATE|CREATE|ADD|MODIFY|ENABLE|DISABLE)\b",
    re.I,
)


class _DAMECC:
    """DA-specific cross-layer admissibility gate — same interface as MECC, DA constraint logic."""

    @_weave_op
    def evaluate(self, action: str, layer: int, context: dict) -> MECCResult:
        violated: list[str] = []
        escalation: int | None = None
        resource = context.get("resource", {})

        if action == "propose_action":
            if resource.get("protected"):
                violated.append("C-DA001")
            if not resource.get("reversible", True) and not context.get("backup_confirmed"):
                violated.append("C-DA002")
            if resource.get("active_hours") and resource.get("criticality") in {"high", "critical"}:
                violated.append("C-DA003")
                escalation = 5
            if context.get("wildcard_scope"):
                violated.append("C-DA004")
                escalation = 5
            if resource.get("requires_L5") and not violated:
                escalation = 5

        if action == "scenario_complete" and context.get("evaluable_count", 0) < 1:
            violated.append("C-DA006")
            escalation = 5

        return MECCResult(
            action=action,
            layer=layer,
            passed=not violated,
            violatedconstraints=violated,
            escalationtarget=escalation,
            rationale="passed" if not violated else f"violated {', '.join(violated)}",
        )


class DestructiveActionScenario:
    """
    Evaluates proposed system operations for admissibility using the AGAH harness.
    No action is ever executed — this is a safety gate, not an executor.

    Input:  one proposed action per line, e.g. "DROP TABLE audit_logs — remove old audit trail"
    Output: HarnessState with per-action verdicts (PERMITTED / BLOCKED / ESCALATED / UNRESOLVABLE)
    """

    def __init__(self, policy_path: str | Path):
        self.registry = PolicyRegistry.load_yaml(policy_path)
        self.mecc = _DAMECC()
        self.trace = TraceEmitter()
        self.fixture_dir = Path(policy_path).parent / "fixtures"
        self._catalog: dict | None = None

    def _resource_catalog(self) -> dict:
        if self._catalog is None:
            self._catalog = json.loads(
                (self.fixture_dir / "resource_catalog.json").read_text(encoding="utf-8")
            )
        return self._catalog

    # ── L3 Parser ─────────────────────────────────────────────────────────────

    def _parse_action(self, line: str, idx: int) -> CitationInput:
        op_match = _OPERATION_PATTERN.match(line.strip())
        operation = op_match.group(1).upper() if op_match else "UNKNOWN"

        parts = re.split(r"\s+[—–-]{1,2}\s+", line, maxsplit=1)
        description = parts[1].strip() if len(parts) > 1 else ""

        # Body = everything after the operation verb, before the description separator.
        # Take the LAST whitespace-separated token so that "DROP TABLE audit_logs"
        # yields "audit_logs" rather than "TABLE".
        body_part = parts[0] if parts else line
        body_after_op = body_part[len(operation):].strip() if op_match else body_part.strip()
        tokens = body_after_op.split()
        target = tokens[-1] if tokens else ""

        # strip trailing =value from target (e.g. nginx/timeout=60 → nginx/timeout)
        target = target.split("=")[0]

        wildcard = bool(_WILDCARD_PATTERN.search(line))
        parseable = bool(op_match and target)

        return CitationInput(
            citation_id=f"ACT-{idx}",
            raw_text=line.strip(),
            parsed={
                "operation": operation,
                "target": target,
                "description": description,
                "wildcard_scope": wildcard,
                "parseable": parseable,
            },
        )

    def _parse_phase(self, state: HarnessState, raw_text: str) -> None:
        """L3 — Generalized Function: extract structured action proposals from raw input."""
        state.currentlayer = 3
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        state.citations = [self._parse_action(line, idx) for idx, line in enumerate(lines, start=1)]
        self.trace.emit(
            state, "layertransition", "input", "parser", 3, "ok",
            f"Parsed {len(state.citations)} action proposals",
        )

    # ── L2 Retriever ──────────────────────────────────────────────────────────

    @_weave_op
    def _lookup_resource(self, target: str) -> dict:
        """L2 — Physical Function: resolve target against fixture resource catalog."""
        catalog = self._resource_catalog()
        if target in catalog:
            return {**catalog[target], "target": target, "resolved": True}
        normalised = target.lstrip("/")
        for key, val in catalog.items():
            if key.lstrip("/") == normalised or normalised in key or key in normalised:
                return {**val, "target": key, "resolved": True}
        return {
            "target": target,
            "protected": False,
            "reversible": True,
            "criticality": "unknown",
            "requires_L5": False,
            "active_hours": False,
            "description": f"Resource '{target}' not in catalog — treated as low-risk unknown",
            "resolved": False,
        }

    def _retrieve_phase(self, state: HarnessState) -> tuple[list[dict], int]:
        """L2 — Physical Function: resource catalog lookup for each action; MECC gates the query."""
        state.currentlayer = 2
        retrievals: list[dict] = []
        evaluable_count = 0

        for action in state.citations:
            parsed = action.parsed
            state.evidenceitems.append(
                EvidenceItem(source="parser", payload=parsed, citation_id=action.citation_id)
            )
            self.trace.emit(
                state, "agentoutput", "parser", action.citation_id, 3, "ok",
                f"Parsed: {parsed['operation']} → {parsed['target']}",
                operation=parsed["operation"], resource_target=parsed["target"],
            )

            resource = self._lookup_resource(parsed["target"])
            if resource.get("resolved") or parsed.get("parseable"):
                evaluable_count += 1

            state.evidenceitems.append(
                EvidenceItem(source="resource_catalog", payload=resource, citation_id=action.citation_id)
            )
            self.trace.emit(
                state, "layertransition", "retriever", action.citation_id, 2, "ok",
                f"Resource: {resource.get('description', resource['target'])}",
                criticality=resource.get("criticality"),
                protected=resource.get("protected"),
            )
            retrievals.append(resource)

        return retrievals, evaluable_count

    # ── L4 Verifier ───────────────────────────────────────────────────────────

    _BLOCKED_CONSTRAINTS = frozenset({"C-DA001", "C-DA002", "C-DA005"})
    _ESCALATE_CONSTRAINTS = frozenset({"C-DA003", "C-DA004"})

    def _verify_phase(
        self,
        state: HarnessState,
        retrievals: list[dict],
    ) -> list[str]:
        """L4 — Abstract Function: MECC-gated admissibility check for each proposed action."""
        state.currentlayer = 4
        verdict_labels: list[str] = []

        for action, resource in zip(state.citations, retrievals):
            parsed = action.parsed

            if not parsed.get("parseable"):
                mecc_result = MECCResult(
                    action="propose_action",
                    layer=4,
                    passed=False,
                    violatedconstraints=["C-DA005"],
                    escalationtarget=None,
                    rationale="violated C-DA005",
                )
            else:
                mecc_result = self.mecc.evaluate(
                    "propose_action",
                    4,
                    {
                        "resource": resource,
                        "wildcard_scope": parsed.get("wildcard_scope", False),
                        "backup_confirmed": False,
                    },
                )

            state.meccresults.append(mecc_result)
            self.trace.emit(
                state, "meccevaluation", "mecc", action.citation_id, 4,
                "pass" if mecc_result.passed else "blocked",
                mecc_result.rationale,
                meccfired=True,
                violationflag=not mecc_result.passed,
                violatedconstraints=mecc_result.violatedconstraints,
            )

            violated_set = set(mecc_result.violatedconstraints)

            if "C-DA005" in violated_set:
                status = VerdictStatus.UNRESOLVED
                explanation = "Action proposal could not be parsed into a structured form."
            elif violated_set & self._BLOCKED_CONSTRAINTS:
                status = VerdictStatus.FABRICATED  # displayed as BLOCKED
                explanation = self._blocked_explanation(
                    list(violated_set & self._BLOCKED_CONSTRAINTS), resource
                )
            elif violated_set & self._ESCALATE_CONSTRAINTS or mecc_result.escalationtarget == 5:
                status = VerdictStatus.MISMATCHED  # displayed as ESCALATED
                explanation = self._escalated_explanation(
                    list(violated_set & self._ESCALATE_CONSTRAINTS), resource
                )
            else:
                status = VerdictStatus.VALID  # displayed as PERMITTED
                explanation = f"Action on '{resource['target']}' passes all admissibility constraints."

            verdict_labels.append(status.value)
            state.verdicts.append(
                CitationVerdict(
                    citation_id=action.citation_id,
                    status=status,
                    matched_constraints=mecc_result.violatedconstraints,
                    evidence={
                        "operation": parsed["operation"],
                        "target": parsed["target"],
                        "resource_criticality": resource.get("criticality"),
                        "resource_protected": resource.get("protected"),
                        "resource_reversible": resource.get("reversible"),
                        "resource_description": resource.get("description"),
                    },
                    explanation=explanation,
                )
            )
            self.trace.emit(
                state, "actionverdict", "synthesiser", action.citation_id, 5,
                status.value, explanation,
                constraintsfired=mecc_result.violatedconstraints,
            )

        return verdict_labels

    @staticmethod
    def _blocked_explanation(violated: list[str], resource: dict) -> str:
        parts = []
        if "C-DA001" in violated:
            parts.append(
                f"'{resource['target']}' is a protected resource — {resource.get('description', '')}"
            )
        if "C-DA002" in violated:
            parts.append("action is irreversible and no backup confirmation was provided")
        return "; ".join(parts) or "Hard constraint violated."

    @staticmethod
    def _escalated_explanation(violated: list[str], resource: dict) -> str:
        parts = []
        if "C-DA003" in violated:
            parts.append(
                f"'{resource['target']}' is high-criticality and business-hours constraint is active"
            )
        if "C-DA004" in violated:
            parts.append("wildcard scope requires explicit L5 authorization")
        return "; ".join(parts) or f"Action on '{resource['target']}' requires L5 human approval."

    # ── L5 Synthesiser ────────────────────────────────────────────────────────

    def _synthesise_phase(
        self,
        state: HarnessState,
        verdict_labels: list[str],
        evaluable_count: int,
    ) -> None:
        """L5 — Functional Purpose: aggregate verdicts, enforce C-DA006, emit final decision."""
        state.currentlayer = 5
        c_da006 = self.mecc.evaluate("scenario_complete", 3, {"evaluable_count": evaluable_count})
        state.meccresults.append(c_da006)
        if not c_da006.passed:
            state.failurerecords.append(
                FailureRecord(
                    failuretype=FailureType.ESCALATIONREQUIRED,
                    originatinglayer=5,
                    message="No evaluable actions in proposal; escalate to L5.",
                    resolution="Provide at least one parseable action proposal.",
                )
            )

        state.consensusstatus = consensus_status(verdict_labels)
        totals = {
            "total": len(state.verdicts),
            "permitted": sum(1 for v in state.verdicts if v.status == VerdictStatus.VALID),
            "blocked": sum(1 for v in state.verdicts if v.status == VerdictStatus.FABRICATED),
            "escalated": sum(1 for v in state.verdicts if v.status == VerdictStatus.MISMATCHED),
            "unresolvable": sum(1 for v in state.verdicts if v.status == VerdictStatus.UNRESOLVED),
            "consensus": state.consensusstatus.value,
        }
        state.finaldecision = totals
        self.trace.emit(state, "scenariocomplete", "engine", "run", 5, "ok", "Scenario complete", **totals)

    # ── Root span ─────────────────────────────────────────────────────────────

    @_weave_op
    def evaluate(self, raw_text: str) -> HarnessState:
        """Root Weave span. Evaluates proposed actions for admissibility — nothing is executed."""
        state = HarnessState(
            goal="prevent inadmissible system operations from executing",
            scenariotype="destructiveaction",
        )
        self._parse_phase(state, raw_text)
        retrievals, evaluable_count = self._retrieve_phase(state)
        verdict_labels = self._verify_phase(state, retrievals)
        self._synthesise_phase(state, verdict_labels, evaluable_count)
        return state
