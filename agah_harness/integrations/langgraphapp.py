from __future__ import annotations

from pathlib import Path

from agah_harness.core.engine import HarnessEngine
from agah_harness.core.state import HarnessState

try:
    from langgraph.graph import END, START, StateGraph
except Exception:
    StateGraph = None
    START = END = None


def build_graph(project_root: str | Path):
    """
    L1 substrate: LangGraph graph with one node per AH layer.

    Nodes map directly to Abstraction Hierarchy layers:
      L3 parser → L2 retriever → L4 verifier → L5 synthesiser

    State dict carries HarnessState and intermediate retrieval results
    between nodes so each layer has only the context it needs.
    """
    engine = HarnessEngine(project_root)
    scenario = engine.scenario

    if StateGraph is None:
        return None

    class GraphState(dict):
        pass

    # ── L3: Generalized Function — Parser ─────────────────────────────────
    def l3_parser(state: GraphState) -> GraphState:
        harness = HarnessState(
            goal="produce non-hallucinated reference chains",
            scenariotype="citationintegrity",
        )
        scenario._parse_phase(harness, state["citation_text"])
        state["harness"] = harness
        return state

    # ── L2: Physical Function — Retriever ──────────────────────────────────
    def l2_retriever(state: GraphState) -> GraphState:
        harness: HarnessState = state["harness"]
        retrievals, verifiable_count = scenario._retrieve_phase(harness)
        state["retrievals"] = retrievals
        state["verifiable_count"] = verifiable_count
        return state

    # ── L4: Abstract Function — Verifier + MECC ────────────────────────────
    def l4_verifier(state: GraphState) -> GraphState:
        harness: HarnessState = state["harness"]
        verdict_labels = scenario._verify_phase(
            harness,
            state["retrievals"],
            state["verifiable_count"],
        )
        state["verdict_labels"] = verdict_labels
        return state

    # ── L5: Functional Purpose — Synthesiser ───────────────────────────────
    def l5_synthesiser(state: GraphState) -> GraphState:
        harness: HarnessState = state["harness"]
        scenario._synthesise_phase(
            harness,
            state["verdict_labels"],
            state["verifiable_count"],
        )
        state["result"] = harness
        return state

    graph = StateGraph(GraphState)
    graph.add_node("L3_parser", l3_parser)
    graph.add_node("L2_retriever", l2_retriever)
    graph.add_node("L4_verifier", l4_verifier)
    graph.add_node("L5_synthesiser", l5_synthesiser)

    graph.add_edge(START, "L3_parser")
    graph.add_edge("L3_parser", "L2_retriever")
    graph.add_edge("L2_retriever", "L4_verifier")
    graph.add_edge("L4_verifier", "L5_synthesiser")
    graph.add_edge("L5_synthesiser", END)

    return graph.compile()
