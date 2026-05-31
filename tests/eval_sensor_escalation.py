"""
AGAH Sensor Escalation — Weave Evaluation Script

Runs five seismic event test cases through the full harness pipeline and publishes
results to the agah-hackathon Weave project as a versioned evaluation.

Each predict() call produces a root Weave span with child spans:
  _lookup_event   (L2) — fixture vs live USGS API resolution
  mecc_evaluate   (L4) — constraint gate result (C-SE001 through C-SE007)
  judge           (L4) — LLM assessor, fired ONLY for C-SE005 cross-agent inconsistency

Key architectural claim under test: the LLM assessor fires for us6000abcd4
(M 6.8 deep-focus) because L4 MECC sees the contradiction between SeismicAgent
(mag >= 6.5) and ImpactAgent (CDI 1.8, null alert) — but NOT for hard-constraint
events (us6000abcd3) where no LLM judgment is appropriate.

Results appear at: wandb.ai → project agah-hackathon → Evaluations tab

Usage:
    python tests/eval_sensor_escalation.py
    python tests/eval_sensor_escalation.py --project my-project
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

import weave
from pydantic import PrivateAttr

ROOT = Path(__file__).resolve().parents[1]


# ── Weave Model ───────────────────────────────────────────────────────────────

class AGAHSeismicModel(weave.Model):
    """Wraps the SE HarnessEngine as a Weave Model.

    Input:  event_ids — one USGS event ID (or newline-separated IDs for multi-event runs)
    Output: verdict dict for the first event, plus pipeline health fields

    Each predict() call is a Weave root span; child spans include _lookup_event (L2),
    mecc_evaluate (L4), and judge (LLM — only for C-SE005 inconsistency events).
    """

    scenario_type: str = "sensorescalation"
    _engine: Any = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        from agah_harness.core.engine import HarnessEngine
        self._engine = HarnessEngine(ROOT, self.scenario_type)

    @weave.op
    def predict(self, event_ids: str) -> dict:
        state = self._engine.run(event_ids)
        if not state.verdicts:
            return {
                "status": "NONE",
                "constraints": [],
                "explanation": "no verdict produced",
                "magnitude": None,
                "depth_km": None,
                "cdi": None,
                "alert": None,
                "tsunami": None,
                "assessor_used": False,
                "data_source": None,
                "layer": state.currentlayer,
                "mecc_fired": False,
                "trace_count": 0,
            }
        v = state.verdicts[0]
        return {
            "status": v.status.value,
            "constraints": v.matched_constraints,
            "explanation": v.explanation,
            "magnitude": v.evidence.get("magnitude"),
            "depth_km": v.evidence.get("depth_km"),
            "cdi": v.evidence.get("cdi"),
            "alert": v.evidence.get("alert"),
            "tsunami": v.evidence.get("tsunami"),
            "assessor_used": v.evidence.get("assessor_used", False),
            "data_source": v.evidence.get("source"),
            "layer": state.currentlayer,
            "mecc_fired": any(r.action == "emit_verdict" for r in state.meccresults),
            "trace_count": len(state.traceevents),
        }


# ── Scorers ────────────────────────────────────────────────────────────────────

@weave.op
def verdict_correct(expected_status: str, output: dict) -> dict:
    """Did the harness return the expected verdict status?"""
    return {"correct": output.get("status") == expected_status}


@weave.op
def constraint_fired(expected_constraint: str, output: dict) -> dict:
    """Did the expected MECC constraint appear in matched_constraints?"""
    if not expected_constraint:
        return {"constraint_check": len(output.get("constraints", [])) == 0}
    return {"constraint_fired": expected_constraint in output.get("constraints", [])}


@weave.op
def pipeline_health(output: dict) -> dict:
    """Did all four AH phases run and did MECC evaluate at L4?"""
    return {
        "all_layers_ran": output.get("layer") == 5,
        "mecc_evaluated": output.get("mecc_fired", False),
        "has_trace_events": output.get("trace_count", 0) >= 3,
    }


@weave.op
def assessor_fired(assessor_expected: bool, output: dict) -> dict:
    """Was the LLM assessor invoked exactly when expected?

    The architectural claim: C-SE005 cross-agent inconsistency triggers the LLM assessor;
    hard constraints (C-SE002 tsunami, C-SE004 orange/red PAGER) must NOT invoke it.
    This scorer makes that claim testable and visible in Weave.
    """
    actual = output.get("assessor_used", False)
    return {"assessor_correct": actual == assessor_expected}


# ── Dataset ────────────────────────────────────────────────────────────────────

ROWS = [
    {
        "event_ids": "us6000abcd1",
        "expected_status": "VALID",
        "expected_constraint": "",
        "assessor_expected": False,
        "description": (
            "Minor M 2.3, depth 8 km, CDI 1.2, no alerts — "
            "no constraints triggered (NOMINAL). Fixture: usgs_nominal.json."
        ),
    },
    {
        "event_ids": "us6000abcd2",
        "expected_status": "MISMATCHED",
        "expected_constraint": "C-SE003",
        "assessor_expected": False,
        "description": (
            "Moderate M 5.8, depth 12 km, yellow PAGER, CDI 4.1 — "
            "C-SE003 fires (mag >= 4.5), seismic monitoring ALERT. No assessor. "
            "Fixture: usgs_alert.json."
        ),
    },
    {
        "event_ids": "us6000abcd3",
        "expected_status": "FABRICATED",
        "expected_constraint": "C-SE002",
        "assessor_expected": False,
        "description": (
            "Major M 7.6, depth 10 km, tsunami flag=1, orange PAGER — "
            "hard constraints C-SE002 + C-SE004 fire; LLM assessor deliberately suppressed. "
            "Fixture: usgs_critical.json."
        ),
    },
    {
        "event_ids": "us6000abcd4",
        "expected_status": "VALID",
        "expected_constraint": "C-SE005",
        "assessor_expected": True,
        "description": (
            "Deep-focus M 6.8, depth 580 km, CDI 1.8, null alert — "
            "C-SE001 fires (mag >= 6.5) but ImpactAgent contradicts (CDI < 2.5, null alert, sig < 400). "
            "C-SE005 cross-agent inconsistency detected at L4; LLM assessor resolves to NOMINAL. "
            "Fixture: usgs_deep_nominal.json. This is the key architectural test case."
        ),
    },
    {
        "event_ids": "us6000xxxxinvalid",
        "expected_status": "UNRESOLVED",
        "expected_constraint": "C-SE006",
        "assessor_expected": False,
        "description": (
            "Non-existent event ID — does not match any fixture and live API returns 404. "
            "C-SE006 fires (event must resolve), verdict is UNRESOLVABLE."
        ),
    },
]


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="AGAH sensor escalation Weave evaluation")
    parser.add_argument(
        "--project",
        default=os.getenv("WEAVE_PROJECT", "agah-hackathon"),
        help="W&B Weave project name (default: agah-hackathon)",
    )
    args = parser.parse_args()

    weave.init(args.project)

    dataset = weave.Dataset(
        name="seismic-escalation-test-v1",
        rows=ROWS,
    )

    model = AGAHSeismicModel()

    evaluation = weave.Evaluation(
        name="agah-seismic-escalation-v1",
        dataset=dataset,
        scorers=[verdict_correct, constraint_fired, pipeline_health, assessor_fired],
    )

    print(f"\nRunning AGAH sensor escalation evaluation → project: {args.project}")
    print(f"  {len(ROWS)} test cases · 4 scorers\n")
    print("  Star case: us6000abcd4 — deep-focus M 6.8, C-SE005 cross-agent inconsistency")
    print("  Weave trace will show 'judge' child span only for this event.\n")

    asyncio.run(evaluation.evaluate(model))

    print(
        f"\nResults published → wandb.ai · project: {args.project} · Evaluations tab\n"
        "  verdict_correct.correct       — fraction with correct status\n"
        "  constraint_fired.*            — fraction where expected constraint fired\n"
        "  pipeline_health.*             — fraction where all 4 AH layers ran\n"
        "  assessor_fired.assessor_correct — LLM invoked iff C-SE005 (key architectural claim)\n"
    )


if __name__ == "__main__":
    main()
