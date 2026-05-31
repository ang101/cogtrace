# AGAH — Claude Code Session Context

> Read this fully before writing any code. This file is the authoritative spec for the build.
> Updated after AI critique review — v1.1

---

## What We Are Building

**AGAH (Abstraction-Grounded Agentic Harness)** — a multi-agent harness for scientific citation integrity verification, grounded in Rasmussen's Abstraction Hierarchy (AH) from cognitive engineering.

This is a **hackathon build** (one day, solo). The primary goal is to demonstrate a novel harness architecture, not just an application. The harness IS the contribution.

**Two prize targets:**
1. Most Sophisticated Harness — judges must see AGAH as a named architecture, not a LangGraph wrapper
2. Best Use of Weave ($1,000) — every MECC evaluation and layer transition traced in W&B Weave

---

## Core Theoretical Frame (READ THIS)

### The Argument
Most practical multi-agent systems built on frameworks such as LangGraph, CrewAI, and AutoGen are organized around human-like job roles—for example, researcher, reviewer, critic, or planner—even when the underlying frameworks themselves are more general orchestration substrates. This pattern is useful for rapid prototyping, but it risks importing human organizational assumptions into systems whose components do not share human cognitive limits, role identities, or social coordination needs. Rasmussen’s Abstraction Hierarchy offers a different basis for design: instead of assigning agents by job title, the harness can allocate components by representational function—what each component perceives, what invariants it enforces, and at what level of abstraction it operates.

AGAH adopts this alternative. It treats the harness as a constraint-and-affordance structure grounded in the five levels of the Abstraction Hierarchy, rather than as a digital org chart. In this design, agents are not defined primarily as “who does the task,” but as “what kind of representation they hold” and “what means-ends relations they are allowed to act on.” That makes the architecture more closely aligned with cognitive work analysis, where system behavior is structured by domain constraints and abstraction levels rather than by inherited workplace metaphors

AGAH's alternative: design the harness as a **constraint-and-affordance structure** using Rasmussen's five-level Abstraction Hierarchy. Agents are allocated by **representational function**, not job title.

### Why job roles are the wrong model (stronger claim)

Job roles are useful organizational constructs, but they are only a coarse and historically contingent proxy for cognition. They emerged largely from industrial labor organization and task coordination, not from a principled account of how cognitive work is decomposed. A role such as “researcher” or “reviewer” bundles together many distinct functions—retrieval, comparison, anomaly detection, judgment under uncertainty, policy checking—that need not remain coupled in an artificial system.

For agentic systems, this matters because role-based decomposition can hide the actual structure of the work domain. It encourages designers to replicate familiar staffing patterns rather than identify the stable properties that govern performance: perceptual access, control constraints, invariants, escalation rules, and abstraction level. AGAH therefore replaces role labels with representational functions. Its units are defined by what information they are permitted to see, what constraints they enforce, and which layer of the work domain they inhabit. These properties are more stable and analytically defensible than job titles, which are often organizational artifacts rather than cognitive primitives

### Human-agent-agent teaming and distributed collaboration

The deeper motivation for AGAH is not only single-user orchestration, but human-agent-agent teaming: situations in which multiple humans each operate semi-autonomous agent ecosystems and must still collaborate effectively. In such settings, failures often arise not because any single agent is unintelligent, but because no shared abstraction structure governs how local decisions, constraints, and goals should be coordinated. Without that structure, collaboration tends to collapse either into opaque agent-to-agent interactions or into excessive routing back through humans.

The Abstraction Hierarchy provides a principled coordination scaffold for these cases. Agents operating at the same level—for example, workflow-pattern agents at a generalized-function layer—can coordinate directly on local structure without escalating every interaction to human principals. By contrast, genuine conflicts over goals, admissibility, or risk can be surfaced at higher layers where human judgment is actually appropriate. This also supports the use of smaller, narrower agents that hold only the context relevant to their layer, rather than large context-heavy agents that attempt to maintain the full system state at once. In that sense, the abstraction-layer design is not only a cognitive structuring mechanism but also an engineering strategy for managing context, cost, and escalation under distributed collaboration.



### The Five AH Layers (NEVER collapse or rename these)

| Layer | Name | AGAH Component | Role |
|---|---|---|---|
| L5 | Functional Purpose | Goal Governor | Mission objectives, ethical bounds, success criteria |
| L4 | Abstract Function | Constraint Reasoner + MECC | Invariants, conservation constraints, safety predicates |
| L3 | Generalized Function | Workflow Orchestrator | Standard operational patterns, fallback chains |
| L2 | Physical Function | Capability Router | Tool specs, API contracts, model capabilities |
| L1 | Physical Form | Execution Substrate (LangGraph) | HTTP calls, file I/O, LLM calls |

**LangGraph is ONLY at L1.** This is architecturally deliberate and defensible. Do not let LangGraph concepts bleed into L2–L5.

### Distributed Cognition (why citation scenario)
No single agent has the full picture:
- Parser sees raw text — doesn't know if citations are real
- Retriever sees API responses — doesn't know the claims
- Verifier sees metadata matches — doesn't know semantic support
- Assessor sees claim-source pairs — doesn't know API availability
- MECC sees all constraints — doesn't execute any action

Only the system together produces the answer. This is distributed cognition made visible.

---

## The MECC (Most Important Primitive)

### Definition
The Means-Ends Consistency Checker is a **cross-layer admissibility function**, not a policy list.

```
MECC(A, L) = permitted(A, L)  ∧  (∀k ≥ L: ¬violates(A, C_k))  ∧  (∃g ∈ G: advances(A, g))
```

### Operational Precision (resolved from critique)

**What counts as an action A in the citation scenario:**
- `accept_citation_as_valid` — final trust verdict
- `query_crossref(doi)` — external API call
- `query_arxiv(title)` — external API call
- `fallback_to_fixture(citation_id)` — use canned response
- `emit_verdict(citation_id, status)` — write result to state

**What `advances(A, g)` means operationally:**
- Boolean rule in v1: action must contribute to at least one of {resolve_citation, flag_fabrication, flag_mismatch, surface_conflict}
- Not a scoring function in v1 — that is v2

**How MECC differs from ordinary policy evaluation:**
MECC is the cross-layer admissibility gate. It checks an action against constraints at ALL layers above its origin level before execution. A policy evaluator checks rules at ONE layer. MECC is what makes the hierarchy enforced at runtime, not just described.

### MECC is invoked:
1. Before any external API call
2. Before any citation verdict is emitted
3. Before any escalation is triggered
4. After any agent proposes an action

---

## Scenario: Citation Integrity Verification (v1 ONLY)

### Real-World Motivation
A May 2026 Lancet paper (DOI: 10.1016/S0140-6736(26)00603-3) audited 2.5 million biomedical papers and found fabricated/mismatched citations at scale. Use this in pitch. Do not use the author's own paper as demo input.

### Precise Scope (resolved from critique)

**v1 = citation integrity** (bibliographic verification):
- DOI exists and resolves
- Title fuzzy-matches (threshold 0.85)
- Year matches ±1
- Venue matches if provided

**v2 = claim-support verification** (semantic):
- Does the source abstract actually support the claim attributed to it?
- C005 is explicitly a v2 constraint — mark it as such in UI

Do NOT conflate these. Do not say v1 catches "unsupported claims" — it catches fabricated/mismatched citations.

### Agent Roles (resolved from critique)
These are **agent roles**. In v1, several are implemented deterministically. Be explicit about this — it is not a weakness, it is the `deterministic_by_default` design principle.

| Agent | Layer | v1 Implementation |
|---|---|---|
| Parser | L3 | Deterministic (regex + structured extraction) |
| Retriever | L2 | Deterministic (Crossref/arXiv HTTP calls) |
| Verifier | L4 | Deterministic (fuzzy match + MECC evaluation) |
| Assessor | L4/L5 | LLM in v1 for ambiguous cases only |
| Synthesiser | L5 | Deterministic (aggregate verdict) |

The LLM (claude-sonnet-4-20250514) is invoked by Assessor for genuinely ambiguous partial matches. This keeps cost low and makes the demo reliable.

### MECC Constraints (YAML-defined in scenarios/citation_integrity/policies.yaml)

| ID | Layer | Rule | On Violation |
|---|---|---|---|
| C001 | L4 | DOI must resolve to real Crossref/PubMed record | FABRICATED |
| C002 | L4 | Resolved title fuzzy-match ≥ 0.85 | MISMATCHED |
| C003 | L4 | Year must match ±1 | MISMATCHED |
| C004 | L4 | Venue must match if provided | MISMATCHED |
| C005 | L4 | Source supports claim (STUB — v2) | N/A in v1 |
| C006 | L3 | API responds within 5s | Retry → fixture fallback |
| C007 | L3 | ≥1 citation verifiable to proceed | Escalate to L5 |

---

## Architecture Decisions (LOCKED)

### File Structure
```
agah/
  harness/
    core/
      state.py          # HarnessState + FailureRecord (typed dataclasses)
      mecc.py           # MECC — standalone module, first-class primitive
      policies.py       # ConstraintPolicy loader + evaluator
      consensus.py      # Cross-agent agreement checker
      trace.py          # TraceEvent emitter + Weave hooks (from day one)
      engine.py         # Orchestration loop
      router.py         # Deterministic/agentic routing via operation_metadata
    agents/
      base.py           # AgentResult dataclass + base interface
      llm.py            # Anthropic claude-sonnet-4 wrapper
      registry.py       # Agent registry
    scenarios/
      citation_integrity/
        scenario.py
        policies.yaml   # C001–C007
        fixtures/       # Canned API responses — BUILD THESE FIRST
          crossref_valid.json
          crossref_fabricated.json
          crossref_mismatched.json
          arxiv_valid.json
      destructive_action/
        scenario.py     # STUB ONLY — empty ScenarioAdapter
      sensor_escalation/
        scenario.py     # STUB ONLY — empty ScenarioAdapter
    integrations/
      langgraph_app.py  # L1 substrate only
      weave_tracing.py  # Weave emit functions
  app/
    streamlit_app.py
  config/
    defaults.yaml
  tests/
    test_mecc.py        # Smoke + unit tests — run before demo
  requirements.txt
  README.md
  CLAUDE.md             # This file
```

### Key Data Structures

```python
# state.py
@dataclass
class HarnessState:
    goal: str
    scenario_type: str
    current_layer: int          # 1–5
    evidence_items: list[EvidenceItem]
    agent_outputs: list[AgentResult]
    mecc_results: list[MECCResult]
    consensus_status: ConsensusStatus
    escalation_target: str | None
    final_decision: FinalDecision | None
    trace_events: list[TraceEvent]
    failure_records: list[FailureRecord]

@dataclass
class FailureRecord:
    failure_type: FailureType    # Enum — NEVER a bare exception
    originating_layer: int
    message: str
    timestamp: datetime
    resolution: str | None

class FailureType(Enum):
    NO_EVIDENCE = "no_evidence"
    TIMEOUT = "timeout"
    CONSENSUS_FAILURE = "consensus_failure"
    CONSTRAINT_VIOLATION = "constraint_violation"
    ESCALATION_REQUIRED = "escalation_required"
    EVIDENCE_CONFLICT = "evidence_conflict"

# mecc.py
@dataclass
class MECCResult:
    action: str
    layer: int
    passed: bool
    violated_constraints: list[str]   # policy_ids
    escalation_target: int | None     # layer to escalate to
```

---

## Build Priority Order (ONE DAY)

**DO NOT skip ahead. Build in this order.**

1. **fixtures/** — Create canned API responses first. Demo resilience depends on this.
2. **state.py** — HarnessState + FailureRecord + all enums
3. **mecc.py** — MECC evaluate() function + MECCResult
4. **policies.py** — YAML loader + ConstraintPolicy + evaluator
5. **trace.py** — TraceEvent + Weave emit (call weave.init early)
6. **agents/base.py + agents/llm.py** — AgentResult + Anthropic wrapper
7. **scenarios/citation_integrity/** — Full pipeline: parse → retrieve → verify → MECC → verdict
8. **engine.py** — Orchestration loop connecting all of the above
9. **integrations/langgraph_app.py** — L1 substrate (keep minimal)
10. **app/streamlit_app.py** — UI last
11. **tests/test_mecc.py** — Run before demo

**Hard cut line:** If behind at step 8, cut semantic similarity (C005), stub scenarios, JSON export. NEVER cut MECC, Weave tracing, or the FABRICATED badge moment in the UI.

---

## Latency Target
**Under 10 seconds** end-to-end for a 3-citation input on stage. Use fixtures as fallback if live API is slow.

---

## Weave Integration (P0 — $1,000 prize)

Thread Weave from step 5 onward. Every significant event emits a trace:

```python
# trace.py — emit on every one of these
TRACE_EVENTS = [
    "layer_transition",       # source_layer, target_layer, trigger
    "mecc_evaluation",        # action, layer, constraints_checked, result
    "agent_output",           # agent_name, layer, confidence, proposed_action
    "constraint_violation",   # policy_id, severity, escalation_target
    "escalation_event",       # layer, reason, question_posed
    "citation_verdict",       # citation_id, status, constraints_fired
    "scenario_complete",      # total, valid, flagged, latency_ms, cost_usd
]
```

Weave traces = the architecture diagram made live. This is the Best Use of Weave story.

---

## Tech Stack

| Component | Choice | Notes |
|---|---|---|
| LLM | claude-sonnet-4-20250514 | Assessor agent for ambiguous cases only |
| L1 Substrate | LangGraph | Execution only — not the architecture |
| Constraint Config | YAML | Swappable per scenario |
| Citation APIs | Crossref REST + arXiv | Free, no auth; fixtures as fallback |
| Semantic Similarity | sentence-transformers (local) | Deterministic, no API call |
| Observability | W&B Weave | From day one, not bolted on |
| UI | Streamlit | Community Cloud deploy |
| Persistence | In-memory only (v1) | No DB |
| Language | Python 3.11+ | |

---

## Critique Resolutions (AI Reviewer — Applied to v1.1)

These were flagged by an AI reviewer and are now resolved in this spec:

| Issue | Resolution |
|---|---|
| "No existing framework provides..." overclaims | Narrowed: existing frameworks do not explicitly organise citation verification through AH-based cross-layer constraints and means-ends consistency |
| "Citation wins over destructive action" too absolute | Reframed: citation is better for research legitimacy; destructive action is better for raw demo viscerality. Citation chosen for this build. |
| All layers marked Deterministic vs multi-agent claim | Resolved: agents are roles; several implemented deterministically in v1 by design. Assessor uses LLM. This is the `deterministic_by_default` principle. |
| MECC vs ordinary policy evaluation ambiguity | Resolved: MECC is cross-layer admissibility function; policy evaluator is single-layer. See MECC section above. |
| C005 absent but problem framed as unsupported claims | Resolved: v1 = citation integrity only. v2 = claim-support. UI labels this explicitly. |
| Fixture creation not prioritised | Resolved: fixtures are step 1 in build order |
| Latency target inconsistency (10s vs 15s) | Resolved: 10 seconds |
| YAML portability overclaim | Resolved: pitch says "same harness can be reconfigured — stubs show portability" not "fully working" |
| Pitch line "every framework" too sweeping | Resolved: "most current multi-agent demos" |

---

## Demo Fixtures (Build First)

Three citations for the live demo:

1. **VALID** — Real paper, real DOI, title/year/venue all match
2. **FABRICATED** — DOI that does not resolve (invented)
3. **MISMATCHED** — Real DOI but title attribution is wrong

Suggested real papers to use for fixtures:
- Yao et al. 2023 ReAct (arXiv:2210.03629) — use as VALID
- Invent a plausible-looking but nonexistent DOI — use as FABRICATED
- Use a real DOI but swap the title with another paper — use as MISMATCHED

The FABRICATED badge moment is the demo's centrepiece. Make sure the fixture triggers it reliably.

---

## Pitch (3 Minutes)

1. **[0:00–0:20]** Hook: A May 2026 Lancet study found fabricated citations in 2.5 million biomedical papers. Most current multi-agent demos can't reliably catch this. Not a model problem — a harness problem.
2. **[0:20–0:50]** Problem: Most current multi-agent demos organise agents like employees. That imports human cognitive limits into systems that don't need them.
3. **[0:50–1:20]** Solution: AGAH maps Rasmussen's Abstraction Hierarchy onto a harness. Five layers. LangGraph only at L1.
4. **[1:20–3:00]** Live demo: Paste citations → layer trace → MECC fires at L4 → red FABRICATED badge → Weave dashboard live.
5. **[3:00]** Close: Same harness reconfigured for other domains — stubs show portability. That is the point.

---

## What NOT to Do

- Do not give agents job-title names (researcher, reviewer, critic) — name them by representational function
- Do not let LangGraph concepts (nodes, edges, conditional routing) appear above L1
- Do not collapse MECC into policies.py — it stays in mecc.py as a first-class module
- Do not add persistence, auth, or multi-user support in v1
- Do not use the author's own paper as demo input
- Do not claim v1 catches unsupported claims — it catches fabricated/mismatched citations
- Do not start Streamlit before the pipeline runs end-to-end in CLI

---

*AGAH SRS v1.1 — Approved for build. All critique resolutions applied.*
