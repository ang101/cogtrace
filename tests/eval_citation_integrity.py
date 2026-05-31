"""
AGAH Citation Integrity — Weave Evaluation Script

Runs five citation test cases through the full harness pipeline and publishes
results to the agah-hackathon Weave project as a versioned evaluation.

Each predict() call produces a root Weave span with child spans:
  _retrieve  (L2) — fixture vs live API resolution
  mecc_evaluate (L4) — constraint gate result
  assess/judge  (L4/L5) — LLM assessor, if fired

Results appear at: wandb.ai → project agah-hackathon → Evaluations tab

Usage:
    python tests/eval_citation_integrity.py
    python tests/eval_citation_integrity.py --project my-project
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

class AGAHCitationModel(weave.Model):
    """Wraps HarnessEngine as a Weave Model.

    Each predict() call produces a root Weave trace spanning all four AH phases.
    The engine is instantiated once per model object (not per call).
    """

    scenario_type: str = "citationintegrity"
    _engine: Any = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        from agah_harness.core.engine import HarnessEngine
        self._engine = HarnessEngine(ROOT, self.scenario_type)

    @weave.op
    def predict(self, citation_text: str) -> dict:
        state = self._engine.run(citation_text)
        if not state.verdicts:
            return {
                "status": "NONE",
                "constraints": [],
                "layer": state.currentlayer,
                "mecc_fired": False,
                "trace_count": 0,
                "title_similarity": None,
                "explanation": "no verdict produced",
            }
        v = state.verdicts[0]
        return {
            "status": v.status.value,
            "constraints": v.matched_constraints,
            "explanation": v.explanation,
            "title_similarity": v.evidence.get("title_similarity"),
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
        # Expect no constraints fired
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


# ── Dataset ────────────────────────────────────────────────────────────────────

ROWS = [
    {
        "citation_text": (
            'Yao et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." '
            "arXiv. DOI: 10.48550/arXiv.2210.03629"
        ),
        "expected_status": "VALID",
        "expected_constraint": "",
        "description": "Real paper, correct DOI, matching title and year — should pass all constraints",
    },
    {
        "citation_text": (
            'Smith et al. (2024). "A Revolutionary Biomedical Agent Pipeline." '
            "Nature. DOI: 10.1038/s41586-2024-99999-x"
        ),
        "expected_status": "FABRICATED",
        "expected_constraint": "C001",
        "description": "Invented DOI (99999) — C001 fires, resolved=False",
    },
    {
        "citation_text": (
            'Jones et al. (2019). "A Survey of Machine Learning Methods." '
            "ICML. DOI: 10.48550/arXiv.2210.03629"
        ),
        "expected_status": "MISMATCHED",
        "expected_constraint": "C002",
        "description": "Real DOI with completely wrong title — similarity far below 0.85, C002 fires",
    },
    {
        "citation_text": (
            'Brown et al. (2021). "Language Models are Few-Shot Learners." NeurIPS.'
        ),
        "expected_status": "FABRICATED",
        "expected_constraint": "C001",
        "description": "No DOI present — parser produces None, fabricated fixture returned",
    },
    {
        "citation_text": (
            'Yao et al. (2023). "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." '
            "arXiv. DOI: 10.48550/arXiv.2210.03629"
        ),
        "expected_status": "MISMATCHED",
        "expected_constraint": "C002",
        "description": "Real DOI with misattributed title — crossrefmismatched.json, C002/C003",
    },
]


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="AGAH citation integrity Weave evaluation")
    parser.add_argument(
        "--project",
        default=os.getenv("WEAVE_PROJECT", "agah-hackathon"),
        help="W&B Weave project name (default: agah-hackathon)",
    )
    args = parser.parse_args()

    weave.init(args.project)

    dataset = weave.Dataset(
        name="citation-integrity-test-v1",
        rows=ROWS,
    )

    model = AGAHCitationModel()

    evaluation = weave.Evaluation(
        name="agah-citation-integrity-v1",
        dataset=dataset,
        scorers=[verdict_correct, constraint_fired, pipeline_health],
    )

    print(f"\nRunning AGAH citation integrity evaluation → project: {args.project}")
    print(f"  {len(ROWS)} test cases · 3 scorers\n")

    asyncio.run(evaluation.evaluate(model))

    print(
        f"\nResults published → wandb.ai · project: {args.project} · "
        "Evaluations tab\n"
        "  verdict_correct.correct  — fraction with correct status\n"
        "  constraint_fired.*       — fraction where expected constraint fired\n"
        "  pipeline_health.*        — fraction where all 4 AH layers ran\n"
    )


if __name__ == "__main__":
    main()
