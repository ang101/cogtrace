from __future__ import annotations

from typing import Any

from agah_harness.core.state import HarnessState
from agah_harness.substrates.base import SubstrateAdapter


class LangGraphSubstrateAdapter(SubstrateAdapter):
    """L1 adapter for LangGraph.

    Wraps the existing LangGraph execution in agah_harness/integrations/langgraphapp.py
    behind the SubstrateAdapter interface so the harness can reference it as a
    named, swappable substrate rather than importing langgraphapp directly.

    Alternative substrates (CrewAdapter, AutogenAdapter, DirectRunnerAdapter)
    would implement SubstrateAdapter and be selected by WorkSystemConfig.substrate.
    """

    def build_graph(self, scenario: Any) -> Any:
        from agah_harness.integrations.langgraphapp import build_citation_graph
        return build_citation_graph(scenario)

    def run(self, graph: Any, raw_text: str) -> HarnessState:
        from agah_harness.integrations.langgraphapp import run_graph
        return run_graph(graph, raw_text)
