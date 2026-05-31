from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agah_harness.core.state import HarnessState


class SubstrateAdapter(ABC):
    """Abstract base for L1 execution substrates.

    The Abstraction Hierarchy keeps LangGraph at L1. This interface makes
    that boundary explicit and swappable: a different L1 substrate (CrewAI,
    AutoGen, OpenAI Responses, a plain async runner) implements this contract
    without touching L2–L5 harness logic.

    Implementing a new substrate requires only two methods:
      build_graph  — construct the execution graph/pipeline from scenario phases
      run          — execute it and return a populated HarnessState
    """

    @abstractmethod
    def build_graph(self, scenario: Any) -> Any:
        """Construct the substrate's execution structure from a scenario.

        Args:
            scenario: Any object exposing _parse_phase, _retrieve_phase,
                      _verify_phase, _synthesise_phase (the four AH phases).

        Returns:
            An opaque graph/pipeline object understood by this substrate's run().
        """

    @abstractmethod
    def run(self, graph: Any, raw_text: str) -> HarnessState:
        """Execute the graph and return a fully populated HarnessState.

        Args:
            graph:    The object returned by build_graph().
            raw_text: Raw input (citations, action proposals, event IDs, etc.)

        Returns:
            HarnessState with all evidence items, verdicts, MECC results,
            trace events, and finaldecision populated.
        """
