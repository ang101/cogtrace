from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agah_harness.core.state import AgentResult, HarnessState


@runtime_checkable
class ScenarioContract(Protocol):
    """Interface for scenario adapters.

    Each scenario (citation integrity, destructive action, sensor escalation,
    and future domains) implements this contract. HarnessEngine routes raw
    input to the correct scenario implementation; the substrate executes the
    resulting pipeline.

    The four AH phase methods are the internal contract; evaluate() is the
    external entry point decorated with @weave.op.
    """

    def evaluate(self, raw_text: str) -> HarnessState:
        """Root Weave span — parse, retrieve, verify, synthesise."""
        ...


@runtime_checkable
class SubstrateContract(Protocol):
    """Interface for L1 execution substrates.

    LangGraph is the default substrate at L1. This contract allows the harness
    to target alternative execution backends (CrewAI, AutoGen, a plain async
    runner, or a test harness) without touching L2–L5 logic.
    """

    def build_graph(self, scenario: Any) -> Any:
        """Construct the execution graph/pipeline from a scenario."""
        ...

    def run(self, graph: Any, raw_text: str) -> HarnessState:
        """Execute the graph and return a fully populated HarnessState."""
        ...


@runtime_checkable
class AssessorContract(Protocol):
    """Interface for LLM assessor agents.

    Assessors are invoked sparingly — only for genuinely ambiguous cases
    (citation similarity 0.70–0.85) and cross-agent inconsistency (C-SE005).
    The contract is the same regardless of the backend (Anthropic, W&B
    Inference, or deterministic fallback).
    """

    def assess(
        self,
        citation_text: str,
        retrieved_title: str,
        parsed_title: str,
    ) -> AgentResult:
        """Resolve an ambiguous citation match. Returns UNRESOLVED or MISMATCHED."""
        ...

    def judge(self, context: str) -> AgentResult:
        """Resolve cross-agent inconsistency. Returns NOMINAL, ALERT, or CRITICAL."""
        ...
