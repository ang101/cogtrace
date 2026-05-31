from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import weave
    _WEAVE_PROJECT = os.getenv("WEAVE_PROJECT", "agah-hackathon")
    weave.init(_WEAVE_PROJECT)
    _weave_active = True
except Exception:
    weave = None  # type: ignore[assignment]
    _weave_active = False
    _WEAVE_PROJECT = "agah-hackathon"

import io

import pandas as pd
import plotly.io as pio
import streamlit as st

if _weave_active:
    import wandb

from agah_harness.core.engine import HarnessEngine
from app.ah_viz import LAYER_LABELS, build_ah_figure

PROJECT_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="CogTrace", layout="wide")
st.image(str(PROJECT_ROOT / "images" / "cogtracelogo.png"), width=180)
st.caption("Trace decisions. See why. A multi-agent harness that checks decisions against structured constraints, across all abstraction layers")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Scenario")
    scenario_type = st.selectbox(
        "Scenario selector",
        ["citationintegrity", "destructiveaction", "sensorescalation"],
        index=0,
    )

    if scenario_type == "citationintegrity":
        st.markdown(
            "Checks whether citations in a document actually exist and match what they claim "
            "to be. Each DOI is verified against Crossref and arXiv; title, year, and venue "
            "are compared against the resolved record. Anything invented or misattributed is "
            "flagged immediately."
        )
        st.markdown("**C005** — Claim support (semantic) — v2 only, not evaluated in this build.")
    elif scenario_type == "destructiveaction":
        st.markdown(
            "Before any system operation runs, the harness decides whether it's safe to "
            "proceed. Irreversible or high-risk operations (deleting data, dropping tables) "
            "are **blocked** outright. Borderline cases are **escalated** for human review "
            "rather than executed silently. Nothing is actually executed — this is a "
            "decision gate, not an execution engine."
        )
    elif scenario_type == "sensorescalation":
        st.markdown(
            "Three independent sensor agents — seismic, tsunami, and impact — each report "
            "on incoming earthquake events. The harness reconciles their findings across all "
            "five abstraction layers. Low-risk events are cleared automatically; high-risk "
            "events escalate to the top layer."
        )
        st.markdown(
            "_Key case: `us6000abcd4` — a large magnitude but negligible observed impact. "
            "Sensors contradict each other, so the LLM assessor steps in to resolve the "
            "ambiguity rather than escalating blindly._"
        )

    if _weave_active:
        st.success(f"Weave tracing active → `{_WEAVE_PROJECT}`")
    else:
        st.warning("Weave not initialised — set WANDB_API_KEY in .env")

# ── Samples ────────────────────────────────────────────────────────────────────
_CITATION_SAMPLE = '''\
Yao et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." arXiv. DOI: 10.48550/arXiv.2210.03629
Smith et al. (2024). "A Revolutionary Biomedical Agent Pipeline." Nature. DOI: 10.1038/s41586-2024-99999-x
Yao et al. (2023). "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." arXiv. DOI: 10.48550/arXiv.2210.03629
Anonymous (2024). "Undocumented Findings in Biomedical Research." Journal of Undocumented Research.'''

_DA_SAMPLE = '''\
DELETE /tmp/cache — clear temporary application cache
DROP TABLE audit_logs — remove old audit trail to free disk space
RESTART payment-service — restart service after config update
UPDATE nginx/timeout=60 — increase request timeout from 30s to 60s'''

_SE_SAMPLE = '''\
us6000abcd1
us6000abcd2
us6000abcd3
us6000abcd4
us6000t04s'''

_SAMPLE_MAP = {
    "citationintegrity": _CITATION_SAMPLE,
    "destructiveaction": _DA_SAMPLE,
    "sensorescalation": _SE_SAMPLE,
}
default_text = _SAMPLE_MAP.get(scenario_type, _CITATION_SAMPLE)

# ── Input ──────────────────────────────────────────────────────────────────────
_INPUT_LABEL = {
    "citationintegrity": "Paste citations",
    "destructiveaction": "Paste proposed actions",
    "sensorescalation": "Paste USGS event IDs (one per line — fixture IDs or live event IDs)",
}
raw_input = st.text_area(
    _INPUT_LABEL.get(scenario_type, "Input"),
    value=default_text,
    height=220,
)
run = st.button("Run CogTrace pipeline", type="primary")


# ── Label helpers (defined before if run: block) ───────────────────────────────

def _da_label(status: str) -> str:
    return {
        "VALID": "PERMITTED",
        "FABRICATED": "BLOCKED",
        "MISMATCHED": "ESCALATED",
        "UNRESOLVED": "UNRESOLVABLE",
    }.get(status, status)


def _se_label(status: str) -> str:
    return {
        "VALID": "NOMINAL",
        "FABRICATED": "CRITICAL",
        "MISMATCHED": "ALERT",
        "UNRESOLVED": "UNRESOLVABLE",
    }.get(status, status)


# ── Constraint label lookup ───────────────────────────────────────────────────

_CONSTRAINT_LABELS: dict[str, str] = {
    "C001": "DOI unresolvable — invented or broken link",
    "C002": "Title mismatch — similarity below 0.85 threshold",
    "C003": "Year mismatch — off by more than 1 year",
    "C004": "Venue mismatch — journal or conference doesn't match",
    "C005": "Claim support (semantic) — v2 only, not evaluated",
    "C006": "API timeout — fallback fixture used",
    "C007": "No verifiable citations — none could be looked up",
    "C008": "No identifier — citation has no DOI or arXiv ID",
    "C-SE001": "Magnitude threshold exceeded (≥6.5)",
    "C-SE002": "Tsunami risk flag triggered",
    "C-SE003": "Seismic alert threshold exceeded (mag ≥4.5)",
    "C-SE004": "PAGER alert level orange or red",
    "C-SE005": "Cross-agent inconsistency — sensors contradict each other",
    "C-SE006": "Event unresolvable — ID not found in any source",
    "C-SE007": "Insufficient sensor data to make a determination",
    "C-DA001": "Protected resource — operation is off-limits",
    "C-DA002": "Irreversible operation — cannot be undone",
    "C-DA003": "Cascading impact risk — affects dependent systems",
    "C-DA004": "Requires L5 human approval before proceeding",
    "C-DA005": "Rate limit or quota exceeded",
    "C-DA006": "No rollback plan — cannot recover if this fails",
}


def _label_constraints(ids: list[str]) -> str:
    return ", ".join(f"{c} ({_CONSTRAINT_LABELS.get(c, c)})" for c in ids) or "none"


# ── AH caption helpers ────────────────────────────────────────────────────────

def _build_run_summary(state, scenario_type: str) -> dict:
    return {
        "scenario": scenario_type,
        "layers_visited": sorted({e.layer for e in state.traceevents}),
        "mecc_total": len(state.meccresults),
        "mecc_violations": sum(1 for r in state.meccresults if not r.passed),
        "verdict_counts": {
            v.status.value: sum(1 for x in state.verdicts if x.status == v.status)
            for v in state.verdicts
        },
        "assessor_fired": any(e.metadata.get("assessor_used") for e in state.traceevents),
        "total_events": len(state.verdicts),
        "fail_details": [
            {
                "id": v.citation_id,
                "status": v.status.value,
                "constraints": v.matched_constraints,
                "why": v.explanation,
            }
            for v in state.verdicts
            if v.status.value not in {"VALID", "NOMINAL", "PERMITTED"}
        ],
    }


def _generate_chart_caption(summary: dict) -> tuple[str, float]:
    """Returns (caption_text, estimated_cost_usd)."""
    import anthropic
    _fallback = (
        "The system walked each item up the abstraction ladder: low-level "
        "retrieval at L1–L2, constraint checks via MECC at L4, and escalation "
        "to the purpose layer (L5) for hard violations.",
        0.0,
    )
    prompt = (
        "Write 2–3 plain-English sentences as a caption for a chart showing a multi-agent "
        "harness traversing Rasmussen's Abstraction Hierarchy (L1=physical to L5=purpose).\n\n"
        f"Scenario: {summary['scenario']}\n"
        f"Layers visited: {summary['layers_visited']}\n"
        f"Items: {summary['total_events']} processed, verdicts: {summary['verdict_counts']}\n"
        f"MECC: {summary['mecc_total']} checks, {summary['mecc_violations']} violations\n"
        f"LLM assessor invoked: {summary['assessor_fired']}\n"
        f"Failures: {summary['fail_details']}\n\n"
        "For each failure, say in plain English what went wrong (e.g. 'citation 2 had an "
        "invented DOI that didn't resolve', 'citation 4 had no identifier at all'). "
        "Describe which layers those failures surfaced at and why. No jargon. "
        "Do not start with 'The chart'."
    )
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=220,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        cost = msg.usage.input_tokens * 3e-6 + msg.usage.output_tokens * 15e-6
        return text, cost
    except Exception:
        return _fallback


# ── Run — execution only (W&B logging + session state storage) ────────────────
if run:
    engine = HarnessEngine(PROJECT_ROOT, scenario_type=scenario_type)
    _new_state = engine.run(raw_input)
    st.session_state["_last_state"] = _new_state
    st.session_state["_last_scenario"] = scenario_type

    if _weave_active and "_wb_run_url" not in st.session_state:
        # Build W&B project URL from API entity (wandb.run may be None with weave.init)
        try:
            _api = wandb.Api()
            _entity = _api.default_entity or ""
            if _entity:
                st.session_state["_wb_run_url"] = (
                    f"https://wandb.ai/{_entity}/{_WEAVE_PROJECT}/weave"
                )
        except Exception:
            pass

        # W&B Table — log verdict rows to classic dashboard
        try:
            _tbl = wandb.Table(
                columns=["scenario", "item_id", "status", "constraints", "explanation"]
            )
            for v in _new_state.verdicts:
                _tbl.add_data(
                    scenario_type,
                    v.citation_id,
                    v.status.value,
                    ", ".join(v.matched_constraints) or "none",
                    (v.explanation or "")[:120],
                )
            wandb.log({
                f"{scenario_type}/verdict_log": _tbl,
                f"{scenario_type}/mecc_violations": sum(
                    1 for r in _new_state.meccresults if not r.passed
                ),
                f"{scenario_type}/total_items": len(_new_state.verdicts),
            })
        except Exception:
            pass

        # Fetch Weave span latencies for display
        try:
            _wc = weave.get_client()
            _recent = list(_wc.calls(limit=20))
            _span_rows = []
            for c in _recent:
                if getattr(c, "started_at", None) and getattr(c, "ended_at", None):
                    _span_rows.append({
                        "operation": (c.op_name or "").split(".")[-1],
                        "latency_ms": round(
                            (c.ended_at - c.started_at).total_seconds() * 1000, 1
                        ),
                        "tokens": ((c.summary or {}).get("usage") or {}).get("total_tokens"),
                    })
            st.session_state["_weave_spans"] = _span_rows
        except Exception:
            st.session_state["_weave_spans"] = []


# ── Render — persists across Streamlit reruns ──────────────────────────────────
_state = st.session_state.get("_last_state")
_scenario = st.session_state.get("_last_scenario", scenario_type)
_wb_url = st.session_state.get("_wb_run_url")

if _state is not None:
    left, center, right = st.columns([1.05, 1.15, 1.2])

    with left:
        st.subheader("What steps we took")
        for event in _state.traceevents:
            is_bad = (
                event.violationflag
                or event.status in {"FABRICATED", "blocked", "CRITICAL"}
            )
            color = "🟥" if is_bad else "🟩"
            st.markdown(f"{color} **L{event.layer}** `{event.event_type}` — {event.message}")

    with center:
        st.subheader("What we decided per event")

        if _scenario == "citationintegrity":
            rows = [
                {
                    "id": v.citation_id,
                    "status": v.status.value,
                    "constraints": _label_constraints(v.matched_constraints),
                    "title_similarity": v.evidence.get("title_similarity"),
                    "explanation": v.explanation,
                }
                for v in _state.verdicts
            ]

        elif _scenario == "destructiveaction":
            rows = [
                {
                    "id": v.citation_id,
                    "operation": v.evidence.get("operation"),
                    "target": v.evidence.get("target"),
                    "status": _da_label(v.status.value),
                    "constraints": _label_constraints(v.matched_constraints),
                    "explanation": v.explanation,
                }
                for v in _state.verdicts
            ]

        else:  # sensorescalation
            rows = [
                {
                    "id": v.citation_id,
                    "event_id": v.evidence.get("event_id"),
                    "place": (v.evidence.get("place") or "")[:40],
                    "mag": v.evidence.get("magnitude"),
                    "depth_km": v.evidence.get("depth_km"),
                    "cdi": v.evidence.get("cdi"),
                    "alert": v.evidence.get("alert") or "—",
                    "status": _se_label(v.status.value),
                    "constraints": _label_constraints(v.matched_constraints),
                    "assessor": "LLM" if v.evidence.get("assessor_used") else "—",
                    "explanation": v.explanation[:80],
                }
                for v in _state.verdicts
            ]

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        for verdict in _state.verdicts:
            if verdict.status.value == "FABRICATED":
                if _scenario == "destructiveaction":
                    st.error(
                        f"🚨 BLOCKED — {verdict.citation_id} "
                        f"({verdict.evidence.get('target')}): {verdict.explanation}"
                    )
                elif _scenario == "sensorescalation":
                    place = verdict.evidence.get("place") or verdict.evidence.get("event_id", "")
                    st.error(
                        f"🚨 CRITICAL ESCALATION — {verdict.citation_id} "
                        f"({place}): {verdict.explanation}"
                    )
                else:
                    st.error(
                        f"🚨 FABRICATED — {verdict.citation_id}: {verdict.explanation}"
                    )

    with right:
        st.subheader("What we blocked and why")
        st.caption("Flagged by the Means–Ends Consistency Checker (MECC)")
        for result in _state.meccresults:
            if not result.passed:
                _labels = [
                    f"**{c}** — {_CONSTRAINT_LABELS.get(c, c)}"
                    for c in result.violatedconstraints
                ]
                st.warning(
                    f"L{result.layer} blocked `{result.action}`:\n\n"
                    + "\n\n".join(f"- {l}" for l in _labels)
                )

        st.subheader("Run totals")
        fd = _state.finaldecision or {}
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            st.metric("Items checked", fd.get("total", 0))
            st.metric("Passed ✓", fd.get("valid", 0))
        with _mc2:
            st.metric("Flagged ✗", fd.get("flagged", 0))
            st.metric("MECC violations", sum(1 for r in _state.meccresults if not r.passed))
        st.caption(f"Consensus: {fd.get('consensus', '—')}")

        if _weave_active:
            st.info(f"Traces published → wandb.ai · project: `{_WEAVE_PROJECT}`")
        if _wb_url:
            st.link_button("Open W&B run →", _wb_url)

        # ── Weave span latencies ───────────────────────────────────────────────
        _spans = st.session_state.get("_weave_spans", [])
        if _spans:
            st.markdown("**Weave span latencies**")
            st.dataframe(pd.DataFrame(_spans), use_container_width=True, hide_index=True)

        # ── Human feedback (L5 approval story) ────────────────────────────────
        if _weave_active:
            st.markdown("**Was this verdict correct?**")
            _fb_col1, _fb_col2 = st.columns(2)
            with _fb_col1:
                if st.button("👍 Correct", key="fb_up"):
                    try:
                        wandb.log({f"{_scenario}/human_feedback": 1})
                        st.success("Feedback recorded → W&B")
                    except Exception:
                        pass
            with _fb_col2:
                if st.button("👎 Incorrect", key="fb_down"):
                    try:
                        wandb.log({f"{_scenario}/human_feedback": -1})
                        st.success("Feedback recorded → W&B")
                    except Exception:
                        pass

    # ── AH Trace Visualization ────────────────────────────────────────────────
    st.divider()

    fig = build_ah_figure(_state.traceevents, _state.verdicts, _scenario)

    # CSV export
    _csv_df = pd.DataFrame([
        {
            "timestamp": e.timestamp.isoformat(),
            "layer": e.layer,
            "layer_name": LAYER_LABELS.get(e.layer, f"L{e.layer}"),
            "event_type": e.event_type,
            "source": e.source,
            "target": e.target,
            "status": e.status,
            "message": e.message,
            "mecc_fired": e.meccfired,
            "violation": e.violationflag,
            "constraints": str(
                e.metadata.get("violatedconstraints")
                or e.metadata.get("constraintsfired")
                or []
            ),
        }
        for e in _state.traceevents
    ])

    # PNG export
    try:
        _png = pio.to_image(fig, format="png", width=1400, height=500, scale=2)
        _png_ok = True
    except Exception:
        _png_ok = False

    _btn_space, _btn_csv, _btn_png = st.columns([7.2, 1.1, 1.1])
    with _btn_csv:
        st.download_button(
            "↓ CSV", _csv_df.to_csv(index=False),
            file_name="ah_trace.csv", mime="text/csv",
            use_container_width=True,
        )
    with _btn_png:
        if _png_ok:
            st.download_button(
                "↓ PNG", _png,
                file_name="ah_trace.png", mime="image/png",
                use_container_width=True,
            )
        else:
            st.button(
                "↓ PNG", disabled=True, use_container_width=True,
                help="kaleido not installed — run: pip install kaleido",
            )

    st.subheader("Abstraction Hierarchy trace")
    _caption_key = f"ah_caption_{id(_state)}"
    if _caption_key not in st.session_state:
        _cap_text, _cap_cost = _generate_chart_caption(_build_run_summary(_state, _scenario))
        st.session_state[_caption_key] = _cap_text
        st.session_state[f"{_caption_key}_cost"] = _cap_cost
    _assessor_calls = sum(1 for e in _state.traceevents if e.metadata.get("assessor_used"))
    _total_cost = st.session_state.get(f"{_caption_key}_cost", 0.0) + _assessor_calls * 0.0003
    with right:
        st.metric("Est. LLM cost", f"~${_total_cost:.4f}")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(st.session_state[_caption_key])
