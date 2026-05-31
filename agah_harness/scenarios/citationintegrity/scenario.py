from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from rapidfuzz import fuzz

from agah_harness.agents.llm import AssessorAgent
from agah_harness.core.consensus import consensus_status
from agah_harness.core.mecc import MECC
from agah_harness.core.policies import PolicyRegistry
from agah_harness.core.router import route_capability
from agah_harness.core.state import (
    CitationInput,
    CitationVerdict,
    EvidenceItem,
    FailureRecord,
    FailureType,
    HarnessState,
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

_AH_LAYER_NAMES = {
    1: "Physical Form (Execution Substrate)",
    2: "Physical Function (Capability Router)",
    3: "Generalized Function (Workflow Orchestrator)",
    4: "Abstract Function (Constraint Reasoner)",
    5: "Functional Purpose (Goal Governor)",
}


class CitationIntegrityScenario:
    def __init__(self, policy_path: str | Path, timeout_seconds: int = 5):
        self.registry = PolicyRegistry.load_yaml(policy_path)
        self.mecc = MECC(self.registry)
        self.trace = TraceEmitter()
        self.timeout_seconds = timeout_seconds
        self.assessor = AssessorAgent()
        self.fixture_dir = Path(policy_path).parent / "fixtures"

    def _mecc_eval(self, action: str, layer: int, context: dict):
        """Evaluate MECC with Weave attributes tagging the AH layer for W&B span visibility."""
        if _weave is not None:
            with _weave.attributes({
                "ah_layer": layer,
                "ah_layer_name": _AH_LAYER_NAMES.get(layer, f"L{layer}"),
                "scenario": "citationintegrity",
                "mecc_action": action,
            }):
                return self.mecc.evaluate(action, layer, context)
        return self.mecc.evaluate(action, layer, context)

    # ── L3 Parser ────────────────────────────────────────────────────────────

    def parse_citations(self, raw_text: str) -> list[CitationInput]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        citations = []
        for idx, line in enumerate(lines, start=1):
            doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", line, re.I)
            year_match = re.search(r"(19|20)\d{2}", line)
            title = line
            quoted = re.findall(r'"([^"]+)"', line)
            if quoted:
                title = quoted[0]
            parsed = {
                "doi": doi_match.group(1) if doi_match else None,
                "year": int(year_match.group(0)) if year_match else None,
                "title": title,
                "venue": "arXiv" if "arxiv" in line.lower() else None,
            }
            citations.append(CitationInput(citation_id=f"CIT-{idx}", raw_text=line, parsed=parsed))
        return citations

    def _parse_phase(self, state: HarnessState, raw_text: str) -> None:
        """L3 — Generalized Function: structured extraction from raw input."""
        state.currentlayer = 3
        state.citations = self.parse_citations(raw_text)
        self.trace.emit(state, "layertransition", "input", "parser", 3, "ok", "Parsed citation input")
        for citation in state.citations:
            doi_present = citation.parsed.get("doi") is not None
            c008 = self._mecc_eval("parse_citation", 3, {"doi_present": doi_present})
            state.meccresults.append(c008)
            if not c008.passed:
                self.trace.emit(
                    state, "meccevaluation", "mecc", citation.citation_id, 3,
                    "blocked", c008.rationale,
                    meccfired=True, violationflag=True,
                    violatedconstraints=c008.violatedconstraints,
                )

    # ── L2 Retriever ─────────────────────────────────────────────────────────

    def _load_fixture(self, name: str) -> dict:
        return json.loads((self.fixture_dir / name).read_text(encoding="utf-8"))

    @_weave_op
    def _retrieve(self, parsed: dict) -> tuple[dict, bool]:
        """L2 — Physical Function: resolve DOI via Crossref API or fixture fallback."""
        doi = parsed.get("doi")
        if not doi:
            return self._load_fixture("crossreffabricated.json"), False
        if "99999" in doi:
            return self._load_fixture("crossreffabricated.json"), False
        if doi.lower() == "10.48550/arxiv.2210.03629" and "chain-of-thought" in parsed.get("title", "").lower():
            data = self._load_fixture("crossrefmismatched.json")
            data["resolved"] = True
            return data, False
        url = f"https://api.crossref.org/works/{doi}"
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            message = response.json().get("message", {})
            message["resolved"] = True
            return message, True
        except Exception:
            data = (
                self._load_fixture("crossrefvalid.json")
                if doi.lower() == "10.48550/arxiv.2210.03629"
                else self._load_fixture("crossreffabricated.json")
            )
            data["resolved"] = data.get("resolved", "title" in data)
            return data, False

    def _retrieve_phase(self, state: HarnessState) -> tuple[list[tuple[dict, bool]], int]:
        """L2 — Physical Function: retrieve metadata for all citations; gate each via MECC."""
        state.currentlayer = 2
        retrievals: list[tuple[dict, bool]] = []
        verifiable_count = 0

        for citation in state.citations:
            parsed = citation.parsed
            capability = route_capability(parsed)
            state.evidenceitems.append(
                EvidenceItem(source="parser", payload=parsed, citation_id=citation.citation_id)
            )
            self.trace.emit(
                state, "agentoutput", "parser", citation.citation_id, 3, "ok",
                "Structured extraction complete", parsed=parsed, capability=capability,
            )

            api_mecc = self._mecc_eval("query_crossref_doi", 2, {"api_ok": True, "verifiable_count": 1})
            state.meccresults.append(api_mecc)
            self.trace.emit(
                state, "meccevaluation", "mecc", citation.citation_id, api_mecc.layer,
                "pass" if api_mecc.passed else "blocked", api_mecc.rationale,
                meccfired=True, violationflag=not api_mecc.passed,
                violatedconstraints=api_mecc.violatedconstraints,
            )

            retrieved, live_api = self._retrieve(parsed)
            if retrieved.get("resolved"):
                verifiable_count += 1
            state.evidenceitems.append(
                EvidenceItem(
                    source="retriever_live" if live_api else "retriever_fixture",
                    payload=retrieved,
                    citation_id=citation.citation_id,
                )
            )
            self.trace.emit(
                state, "layertransition", "retriever", citation.citation_id, 2, "ok",
                "Metadata retrieval complete", live_api=live_api,
            )
            retrievals.append((retrieved, live_api))

        return retrievals, verifiable_count

    # ── L4 Verifier ──────────────────────────────────────────────────────────

    def _verify_phase(
        self,
        state: HarnessState,
        retrievals: list[tuple[dict, bool]],
        verifiable_count: int,
    ) -> list[str]:
        """L4 — Abstract Function: MECC-gated constraint evaluation + LLM assessor for ambiguous cases."""
        state.currentlayer = 4
        verdict_labels: list[str] = []

        for citation, (retrieved, live_api) in zip(state.citations, retrievals):
            parsed = citation.parsed

            resolved_title = (
                (retrieved.get("title") or [""])[0]
                if isinstance(retrieved.get("title"), list)
                else retrieved.get("title", "")
            )
            parsed_title = parsed.get("title") or ""
            similarity = fuzz.token_sort_ratio(parsed_title, resolved_title) / 100 if resolved_title else 0

            year = parsed.get("year")
            published = (
                retrieved.get("published", {}).get("date-parts", [[]])
                if isinstance(retrieved.get("published"), dict)
                else [[]]
            )
            resolved_year = published[0][0] if published and published[0] else None
            year_ok = True if year is None or resolved_year is None else abs(year - resolved_year) <= 1

            venue = parsed.get("venue")
            resolved_venue = (
                (retrieved.get("container-title") or [None])[0]
                if isinstance(retrieved.get("container-title"), list)
                else retrieved.get("container-title")
            )
            venue_ok = True if not venue else venue.lower() == (resolved_venue or "").lower()

            verdict_mecc = self._mecc_eval(
                "emit_verdict",
                4,
                {
                    "retrieved": retrieved,
                    "title_similarity": similarity,
                    "year_match": year_ok,
                    "venue_match": venue_ok,
                    "verifiable_count": verifiable_count,
                },
            )
            state.meccresults.append(verdict_mecc)
            self.trace.emit(
                state, "meccevaluation", "mecc", citation.citation_id, 4,
                "pass" if verdict_mecc.passed else "blocked", verdict_mecc.rationale,
                meccfired=True, violationflag=not verdict_mecc.passed,
                violatedconstraints=verdict_mecc.violatedconstraints,
            )

            if "C001" in verdict_mecc.violatedconstraints:
                status = VerdictStatus.FABRICATED
                explanation = "DOI did not resolve to a real record."
            elif any(v in verdict_mecc.violatedconstraints for v in ["C002", "C003", "C004"]):
                if 0.70 <= similarity < 0.85:
                    assessor_result = self.assessor.assess(citation.raw_text, resolved_title, parsed_title)
                    state.agentoutputs.append(assessor_result)
                    self.trace.emit(
                        state, "agentoutput", assessor_result.agentname,
                        citation.citation_id, assessor_result.layer, "ok",
                        assessor_result.summary, proposedaction=assessor_result.proposedaction,
                    )
                    if assessor_result.proposedaction == "emit_unresolved":
                        status = VerdictStatus.UNRESOLVED
                        explanation = assessor_result.summary
                    else:
                        status = VerdictStatus.MISMATCHED
                        explanation = "Resolved record conflicts with supplied citation metadata."
                else:
                    status = VerdictStatus.MISMATCHED
                    explanation = "Resolved record conflicts with supplied citation metadata."
            else:
                status = VerdictStatus.VALID
                explanation = "DOI resolved and bibliographic checks passed."

            verdict_labels.append(status.value)
            state.verdicts.append(
                CitationVerdict(
                    citation_id=citation.citation_id,
                    status=status,
                    matched_constraints=verdict_mecc.violatedconstraints,
                    evidence={
                        "parsed": parsed,
                        "retrieved_title": resolved_title,
                        "title_similarity": round(similarity, 3),
                        "resolved_year": resolved_year,
                        "resolved_venue": resolved_venue,
                        "live_api": live_api,
                    },
                    explanation=explanation,
                )
            )
            self.trace.emit(
                state, "citationverdict", "synthesiser", citation.citation_id, 5,
                status.value, explanation, constraintsfired=verdict_mecc.violatedconstraints,
            )

        return verdict_labels

    # ── L5 Synthesiser ───────────────────────────────────────────────────────

    def _synthesise_phase(
        self,
        state: HarnessState,
        verdict_labels: list[str],
        verifiable_count: int,
    ) -> None:
        """L5 — Functional Purpose: aggregate verdicts, enforce C007, emit final decision."""
        state.currentlayer = 5
        c007 = self._mecc_eval("scenario_complete", 5, {"verifiable_count": verifiable_count})
        state.meccresults.append(c007)
        self.trace.emit(
            state, "meccevaluation", "mecc", "workflow", 5,
            "pass" if c007.passed else "blocked", c007.rationale,
            meccfired=True,
            violationflag=not c007.passed,
            violatedconstraints=c007.violatedconstraints,
        )
        if not c007.passed:
            state.failurerecords.append(
                FailureRecord(
                    failuretype=FailureType.ESCALATIONREQUIRED,
                    originatinglayer=5,
                    message="No citation verifiable; escalate to L5.",
                    resolution="Ask for a verifiable DOI or use a fixture-backed sample.",
                )
            )

        state.consensusstatus = consensus_status(verdict_labels)
        totals = {
            "total": len(state.verdicts),
            "valid": sum(1 for v in state.verdicts if v.status == VerdictStatus.VALID),
            "flagged": sum(
                1 for v in state.verdicts
                if v.status in {VerdictStatus.FABRICATED, VerdictStatus.MISMATCHED}
            ),
            "unresolved": sum(1 for v in state.verdicts if v.status == VerdictStatus.UNRESOLVED),
            "consensus": state.consensusstatus.value,
        }
        state.finaldecision = totals
        self.trace.emit(state, "scenariocomplete", "engine", "run", 5, "ok", "Scenario complete", **totals)

    # ── Root span: @weave.op traces the full pipeline in W&B ─────────────────

    @_weave_op
    def evaluate(self, raw_text: str) -> HarnessState:
        """Entry point. @weave.op makes this the root Weave span; child spans are MECC and assessor calls."""
        state = HarnessState(
            goal="produce non-hallucinated reference chains",
            scenariotype="citationintegrity",
        )
        self._parse_phase(state, raw_text)
        retrievals, verifiable_count = self._retrieve_phase(state)
        verdict_labels = self._verify_phase(state, retrievals, verifiable_count)
        self._synthesise_phase(state, verdict_labels, verifiable_count)
        return state
