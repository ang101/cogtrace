from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


WORK_SYSTEM_PROPERTIES: dict[str, str] = {
    "admissibility": (
        "Cross-layer MECC gate — every proposed action is checked against all "
        "higher-layer constraints before execution"
    ),
    "escalation": (
        "Typed escalation targets — L4 routes to L5 on constraint violation; "
        "FailureType.ESCALATIONREQUIRED is first-class state, not an exception"
    ),
    "accountability": (
        "FailureRecord with originating_layer and resolution — failures are "
        "typed, timestamped, and resolvable by the harness, not silently swallowed"
    ),
    "observability": (
        "@weave.op traces on MECC, assessor, and scenario root + "
        "TraceEvent audit trail in HarnessState — architecture diagram made live"
    ),
    "policy_surface": (
        "YAML-defined constraints, versioned per scenario, swappable without "
        "code changes — the policy boundary is explicit and auditable"
    ),
    "evidence_provenance": (
        "EvidenceItem tracks source and citation_id separately from verdicts — "
        "no single agent collapses evidence and judgment into one object"
    ),
    "extension_contracts": (
        "ScenarioContract, SubstrateContract, AssessorContract (extension_contracts.py) "
        "— the three extension points are formal Protocol interfaces, not implicit conventions"
    ),
    "distributed_cognition": (
        "No single component holds the full picture — the harness composes the "
        "answer from layer-bounded representations; this is visible in Weave traces"
    ),
}


@dataclass
class WorkSystemConfig:
    """Configuration for a single AGAH work-system execution.

    Passed to HarnessEngine (or a future WorkSystem entry point) to select
    scenario, substrate, and observability settings. Keeps the configuration
    surface explicit rather than scattered across environment variables.
    """

    scenario_type: str
    substrate: str = "langgraph"
    policy_path: str | Path | None = None
    weave_project: str = "agah-hackathon"
    trace_enabled: bool = True

    @property
    def properties(self) -> dict[str, str]:
        """Return the canonical work-system property descriptions."""
        return WORK_SYSTEM_PROPERTIES

    def describe(self) -> str:
        """One-line identity string for logs and Weave run names."""
        return f"AGAH work-system [{self.scenario_type}] via {self.substrate}"
