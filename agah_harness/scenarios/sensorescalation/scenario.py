from __future__ import annotations

import json
from pathlib import Path

import requests

from agah_harness.agents.llm import AssessorAgent
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

_AH_LAYER_NAMES = {
    1: "Physical Form (Execution Substrate)",
    2: "Physical Function (Capability Router)",
    3: "Generalized Function (Workflow Orchestrator)",
    4: "Abstract Function (Constraint Reasoner)",
    5: "Functional Purpose (Goal Governor)",
}

_USGS_DETAIL_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/{}.geojson"

_FIXTURE_MAP = {
    "us6000abcd1": "usgs_nominal.json",
    "us6000abcd2": "usgs_alert.json",
    "us6000abcd3": "usgs_critical.json",
    "us6000abcd4": "usgs_deep_nominal.json",
}


def _flatten(feature: dict) -> dict:
    """Flatten USGS GeoJSON Feature into a working dict; extract depth from geometry."""
    props = dict(feature.get("properties") or {})
    coords = (feature.get("geometry") or {}).get("coordinates") or [None, None, None]
    props["depth"] = float(coords[2]) if len(coords) > 2 and coords[2] is not None else None
    props["event_id"] = feature.get("id", "")
    props["resolved"] = True
    return props


class _SEMECC:
    """SE-specific cross-layer admissibility gate.

    Three virtual L2 agents feed this gate:
      SeismicAgent  — mag, depth, nst, magType
      TsunamiAgent  — tsunami flag, depth, coastal proximity
      ImpactAgent   — PAGER alert, CDI, significance score

    C-SE005 is the cross-agent constraint: inconsistency between seismic signal
    and impact evidence is only visible here at L4, not to any individual L2 agent.
    """

    @_weave_op
    def evaluate(self, action: str, layer: int, context: dict) -> MECCResult:
        violated: list[str] = []
        escalation: int | None = None
        props = context.get("props", {})

        if action == "emit_verdict":
            mag = float(props.get("mag") or 0)
            tsunami = int(props.get("tsunami") or 0)
            alert = props.get("alert")
            cdi = float(props.get("cdi") or 0)
            sig = int(props.get("sig") or 0)

            # C-SE002 (hard): tsunami flag
            if tsunami == 1:
                violated.append("C-SE002")
                escalation = 5

            # C-SE004 (hard): PAGER orange or red
            if alert in ("orange", "red"):
                violated.append("C-SE004")
                escalation = 5

            # C-SE001: magnitude >= 6.5
            if mag >= 6.5:
                violated.append("C-SE001")
                if escalation is None:
                    escalation = 5

            # C-SE003: moderate magnitude (only if C-SE001 not already firing)
            elif 4.5 <= mag < 6.5:
                violated.append("C-SE003")

            # C-SE005: cross-agent inconsistency
            # C-SE001 fired but impact evidence is contradictorily low
            if "C-SE001" in violated and cdi < 2.5 and alert is None and sig < 400:
                violated.append("C-SE005")

        if action == "scenario_complete":
            if context.get("evaluable_count", 0) < 1:
                violated.append("C-SE007")
                escalation = 5

        return MECCResult(
            action=action,
            layer=layer,
            passed=not bool(violated),
            violatedconstraints=violated,
            escalationtarget=escalation,
            rationale="passed" if not violated else f"violated {', '.join(violated)}",
        )


class SeismicEscalationScenario:
    """
    Evaluates USGS seismic events for escalation using multi-sensor MECC.

    Three L2 agents per event — SeismicAgent, TsunamiAgent, ImpactAgent — each sees only
    its own evidence. C-SE005 cross-agent inconsistency fires when their signals contradict;
    only L4 MECC can see all three simultaneously. LLM assessor resolves the inconsistency.

    Input:  one USGS event ID per line (fixture IDs us6000abcd1-4 or any live USGS event ID)
    Output: HarnessState with per-event verdicts (NOMINAL / ALERT / CRITICAL / UNRESOLVABLE)

    Verdict mapping:
      VerdictStatus.VALID       -> NOMINAL
      VerdictStatus.MISMATCHED  -> ALERT
      VerdictStatus.FABRICATED  -> CRITICAL (escalate to L5)
      VerdictStatus.UNRESOLVED  -> UNRESOLVABLE
    """

    _HARD_CONSTRAINTS = frozenset({"C-SE002", "C-SE004"})

    def __init__(self, policy_path: str | Path):
        self.registry = PolicyRegistry.load_yaml(policy_path)
        self.mecc = _SEMECC()
        self.trace = TraceEmitter()
        self.assessor = AssessorAgent()
        self.fixture_dir = Path(policy_path).parent / "fixtures"
        self._fixture_cache: dict[str, dict] | None = None

    def _mecc_eval(self, action: str, layer: int, context: dict) -> MECCResult:
        """Evaluate MECC with Weave attributes tagging the AH layer for W&B span visibility."""
        if _weave is not None:
            with _weave.attributes({
                "ah_layer": layer,
                "ah_layer_name": _AH_LAYER_NAMES.get(layer, f"L{layer}"),
                "scenario": "sensorescalation",
                "mecc_action": action,
            }):
                return self.mecc.evaluate(action, layer, context)
        return self.mecc.evaluate(action, layer, context)

    def _fixtures(self) -> dict[str, dict]:
        if self._fixture_cache is None:
            self._fixture_cache = {}
            for eid, fname in _FIXTURE_MAP.items():
                fpath = self.fixture_dir / fname
                if fpath.exists():
                    self._fixture_cache[eid] = json.loads(fpath.read_text(encoding="utf-8"))
        return self._fixture_cache

    # -- L3 Parser -------------------------------------------------------------

    def _parse_phase(self, state: HarnessState, raw_text: str) -> None:
        """L3 -- Generalized Function: extract event IDs from raw input."""
        state.currentlayer = 3
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        for idx, line in enumerate(lines, start=1):
            event_id = line.split()[0].strip()
            state.citations.append(CitationInput(
                citation_id=f"EVT-{idx}",
                raw_text=line,
                parsed={"event_id": event_id, "description": line},
            ))
        self.trace.emit(
            state, "layertransition", "input", "parser", 3, "ok",
            f"Parsed {len(state.citations)} event IDs",
        )

    # -- L2 Retriever ----------------------------------------------------------

    @_weave_op
    def _lookup_event(self, event_id: str) -> dict:
        """L2 -- Physical Function: fixture routing then live USGS API with 5s timeout."""
        fixtures = self._fixtures()
        if event_id in fixtures:
            result = _flatten(fixtures[event_id])
            result["source"] = "fixture"
            return result

        try:
            resp = requests.get(
                _USGS_DETAIL_URL.format(event_id),
                timeout=5,
                headers={"User-Agent": "AGAH-Harness/1.0"},
            )
            if resp.status_code == 200:
                result = _flatten(resp.json())
                result["source"] = "live_api"
                return result
        except Exception:
            pass

        unknown = json.loads((self.fixture_dir / "usgs_unknown.json").read_text(encoding="utf-8"))
        result = _flatten(unknown)
        result["event_id"] = event_id
        result["resolved"] = False
        result["source"] = "fallback"
        return result

    def _retrieve_phase(self, state: HarnessState) -> tuple[list[dict], int]:
        """L2 -- Physical Function: three sensor-agent evidence items per event."""
        state.currentlayer = 2
        retrievals: list[dict] = []
        evaluable_count = 0

        for event in state.citations:
            event_id = event.parsed["event_id"]

            gate = self._mecc_eval("query_usgs_api", 2, {"event_id": event_id})
            state.meccresults.append(gate)
            self.trace.emit(
                state, "meccevaluation", "mecc", event.citation_id, gate.layer,
                "pass" if gate.passed else "blocked", gate.rationale,
                meccfired=True, violationflag=not gate.passed,
                violatedconstraints=gate.violatedconstraints,
            )

            props = self._lookup_event(event_id)
            if props.get("resolved"):
                evaluable_count += 1

            # SeismicAgent -- only sees mag/depth/station data
            state.evidenceitems.append(EvidenceItem(
                source="seismic_agent",
                payload={
                    "mag": props.get("mag"),
                    "depth": props.get("depth"),
                    "nst": props.get("nst"),
                    "magType": props.get("magType"),
                    "rms": props.get("rms"),
                },
                citation_id=event.citation_id,
            ))

            # TsunamiAgent -- only sees tsunami flag and depth
            state.evidenceitems.append(EvidenceItem(
                source="tsunami_agent",
                payload={
                    "tsunami": props.get("tsunami"),
                    "depth": props.get("depth"),
                    "coastal": self._coastal(props),
                },
                citation_id=event.citation_id,
            ))

            # ImpactAgent -- only sees PAGER/CDI/significance
            state.evidenceitems.append(EvidenceItem(
                source="impact_agent",
                payload={
                    "alert": props.get("alert"),
                    "cdi": props.get("cdi"),
                    "sig": props.get("sig"),
                    "felt": props.get("felt"),
                    "mmi": props.get("mmi"),
                },
                citation_id=event.citation_id,
            ))

            data_source = props.get("source", "fallback")
            self.trace.emit(
                state, "layertransition", f"retriever_{data_source}", event.citation_id, 2,
                "ok" if props.get("resolved") else "fallback",
                f"{event_id}: M {props.get('mag', '?')}, "
                f"depth {props.get('depth', '?')} km, "
                f"alert={props.get('alert')}, CDI={props.get('cdi')}",
                mag=props.get("mag"),
                depth=props.get("depth"),
                alert=props.get("alert"),
                tsunami=props.get("tsunami"),
                data_source=data_source,
            )
            source = data_source
            retrievals.append(props)

        return retrievals, evaluable_count

    @staticmethod
    def _coastal(props: dict) -> str:
        place = (props.get("place") or "").lower()
        coastal_words = ("coast", "sea", "ocean", "island", "bay", "gulf", "strait", "pacific", "atlantic")
        return "coastal" if any(w in place for w in coastal_words) else "inland"

    # -- L4 Verifier -----------------------------------------------------------

    def _inconsistency_prompt(self, props: dict) -> str:
        return (
            "You are the AGAH L4 assessor resolving a cross-sensor inconsistency for a seismic event.\n\n"
            f"SeismicAgent reports: M {props.get('mag')}, depth {props.get('depth')} km, "
            f"{props.get('nst', 'unknown')} reporting stations, magType={props.get('magType')}.\n"
            f"TsunamiAgent reports: tsunami={props.get('tsunami')}, depth={props.get('depth')} km.\n"
            f"ImpactAgent reports: CDI={props.get('cdi')}, PAGER alert={props.get('alert')}, "
            f"significance={props.get('sig')}, felt reports={props.get('felt', 0)}.\n"
            f"Place: {props.get('place', 'unknown')}.\n\n"
            f"These signals conflict. A shallow M {props.get('mag')} event typically produces CDI > 3.0, "
            f"but CDI is only {props.get('cdi')}. The most likely explanation is a deep-focus event "
            f"(seismic energy absorbed before reaching the surface) or a magnitude overestimate.\n\n"
            "Based on the full sensor picture -- depth, magnitude, CDI, and felt reports -- "
            "decide the appropriate escalation level.\n"
            "Return one line only: NOMINAL, ALERT, or CRITICAL -- then a one-sentence reason."
        )

    def _verify_phase(self, state: HarnessState, retrievals: list[dict]) -> list[str]:
        """L4 -- Abstract Function: MECC-gated multi-sensor constraint evaluation."""
        state.currentlayer = 4
        verdict_labels: list[str] = []

        for event, props in zip(state.citations, retrievals):
            if not props.get("resolved"):
                state.meccresults.append(MECCResult(
                    action="emit_verdict",
                    layer=4,
                    passed=False,
                    violatedconstraints=["C-SE006"],
                    escalationtarget=None,
                    rationale="violated C-SE006",
                ))
                status = VerdictStatus.UNRESOLVED
                explanation = f"Event ID '{event.parsed['event_id']}' did not resolve to a USGS record."
                verdict_labels.append(status.value)
                state.verdicts.append(CitationVerdict(
                    citation_id=event.citation_id,
                    status=status,
                    matched_constraints=["C-SE006"],
                    evidence={"event_id": event.parsed["event_id"]},
                    explanation=explanation,
                ))
                self.trace.emit(
                    state, "actionverdict", "mecc", event.citation_id, 4,
                    status.value, explanation,
                    violationflag=True,
                    constraintsfired=["C-SE006"],
                )
                continue

            mecc_result = self._mecc_eval("emit_verdict", 4, {"props": props})
            state.meccresults.append(mecc_result)
            violated = set(mecc_result.violatedconstraints)

            self.trace.emit(
                state, "meccevaluation", "mecc", event.citation_id, 4,
                "pass" if mecc_result.passed else "blocked",
                mecc_result.rationale,
                meccfired=True,
                violationflag=not mecc_result.passed,
                violatedconstraints=mecc_result.violatedconstraints,
                cross_agent_inconsistency="C-SE005" in violated,
            )

            assessor_used = False

            # Hard constraints -- no LLM override
            if violated & self._HARD_CONSTRAINTS:
                status = VerdictStatus.FABRICATED
                hard_fired = list(violated & self._HARD_CONSTRAINTS)
                explanation = self._hard_explanation(hard_fired, props)

            # Cross-agent inconsistency -> LLM assessor resolves
            elif "C-SE005" in violated:
                assessor_used = True
                prompt = self._inconsistency_prompt(props)
                llm_result = self.assessor.judge(prompt)
                state.agentoutputs.append(llm_result)
                verdict_word = (llm_result.proposedaction or "NOMINAL").upper()
                self.trace.emit(
                    state, "agentoutput", "assessor", event.citation_id, 4, "ok",
                    f"LLM assessor (C-SE005 inconsistency): {verdict_word} -- "
                    f"{llm_result.summary[:100]}",
                    confidence=llm_result.confidence,
                    proposedaction=verdict_word,
                    cross_agent_inconsistency=True,
                )
                if verdict_word == "CRITICAL":
                    status = VerdictStatus.FABRICATED
                elif verdict_word == "ALERT":
                    status = VerdictStatus.MISMATCHED
                else:
                    status = VerdictStatus.VALID
                explanation = f"[LLM assessor resolved C-SE005] {llm_result.summary}"

            # C-SE001 without inconsistency -> CRITICAL (confirmed by seismic + impact)
            elif "C-SE001" in violated:
                status = VerdictStatus.FABRICATED
                explanation = (
                    f"M {props.get('mag')} >= 6.5 with corroborating impact evidence "
                    f"-- immediate L5 escalation (C-SE001)"
                )

            # C-SE003 -> ALERT
            elif "C-SE003" in violated:
                status = VerdictStatus.MISMATCHED
                explanation = (
                    f"M {props.get('mag')} >= 4.5 -- seismic monitoring alert (C-SE003)"
                )

            # NOMINAL
            else:
                status = VerdictStatus.VALID
                explanation = (
                    f"M {props.get('mag')} -- all sensor signals nominal, no constraints triggered"
                )

            verdict_labels.append(status.value)
            state.verdicts.append(CitationVerdict(
                citation_id=event.citation_id,
                status=status,
                matched_constraints=mecc_result.violatedconstraints,
                evidence={
                    "event_id": props.get("event_id"),
                    "place": props.get("place"),
                    "magnitude": props.get("mag"),
                    "depth_km": props.get("depth"),
                    "cdi": props.get("cdi"),
                    "alert": props.get("alert"),
                    "tsunami": props.get("tsunami"),
                    "sig": props.get("sig"),
                    "source": props.get("source"),
                    "assessor_used": assessor_used,
                },
                explanation=explanation,
            ))
            self.trace.emit(
                state, "actionverdict", "synthesiser", event.citation_id, 5,
                status.value, explanation,
                constraintsfired=mecc_result.violatedconstraints,
                assessor_used=assessor_used,
            )

        return verdict_labels

    @staticmethod
    def _hard_explanation(hard_fired: list[str], props: dict) -> str:
        parts = []
        if "C-SE002" in hard_fired:
            parts.append("tsunami flag active (hard constraint C-SE002 -- no assessor override)")
        if "C-SE004" in hard_fired:
            parts.append(
                f"PAGER alert level '{props.get('alert')}' (hard constraint C-SE004 -- no assessor override)"
            )
        return "; ".join(parts) or "Hard constraint -- immediate CRITICAL escalation."

    # -- L5 Synthesiser --------------------------------------------------------

    def _synthesise_phase(
        self,
        state: HarnessState,
        verdict_labels: list[str],
        evaluable_count: int,
    ) -> None:
        """L5 -- Functional Purpose: aggregate verdicts, enforce C-SE007, emit final decision."""
        state.currentlayer = 5
        c_se007 = self._mecc_eval("scenario_complete", 5, {"evaluable_count": evaluable_count})
        state.meccresults.append(c_se007)
        if not c_se007.passed:
            state.failurerecords.append(FailureRecord(
                failuretype=FailureType.ESCALATIONREQUIRED,
                originatinglayer=5,
                message="No evaluable seismic events; escalate to L5.",
                resolution="Provide at least one valid USGS event ID.",
            ))

        state.consensusstatus = consensus_status(verdict_labels)
        totals = {
            "total": len(state.verdicts),
            "critical": sum(1 for v in state.verdicts if v.status == VerdictStatus.FABRICATED),
            "alert": sum(1 for v in state.verdicts if v.status == VerdictStatus.MISMATCHED),
            "nominal": sum(1 for v in state.verdicts if v.status == VerdictStatus.VALID),
            "unresolvable": sum(1 for v in state.verdicts if v.status == VerdictStatus.UNRESOLVED),
            "consensus": state.consensusstatus.value,
        }
        state.finaldecision = totals
        self.trace.emit(state, "scenariocomplete", "engine", "run", 5, "ok", "Scenario complete", **totals)

    # -- Root span -------------------------------------------------------------

    @_weave_op
    def evaluate(self, raw_text: str) -> HarnessState:
        """Root Weave span. Evaluates USGS seismic events via multi-sensor MECC."""
        state = HarnessState(
            goal="detect and escalate significant seismic events before irreversible decisions are made",
            scenariotype="sensorescalation",
        )
        self._parse_phase(state, raw_text)
        retrievals, evaluable_count = self._retrieve_phase(state)
        verdict_labels = self._verify_phase(state, retrievals)
        self._synthesise_phase(state, verdict_labels, evaluable_count)
        return state
