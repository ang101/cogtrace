from __future__ import annotations

from agah_harness.agents.llm import AssessorAgent


def build_registry() -> dict[str, object]:
    return {
        "assessor": AssessorAgent(),
    }
