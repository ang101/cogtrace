# CogTrace

**Trace decisions. See why.**

CogTrace is a multi-agent harness that checks decisions against structured constraints across all abstraction layers — grounded in Rasmussen's Abstraction Hierarchy from cognitive engineering.

> Built for the AGI Hackathon 2026. Two prize tracks: Most Sophisticated Harness and Best Use of W&B Weave.

---

## The argument

Most multi-agent systems are just org charts in disguise — one agent writes code, one reviews it, one deploys it. They know their role. But when something goes wrong, nobody knows at which level of reasoning it failed: was it a bad tool call at the execution layer? A constraint that wasn't checked? A goal that was never specified? The role-based model has no answer because it was never designed to ask that question.

CogTrace is designed around that question. Every action is checked against constraints at a specific level of abstraction before it executes. When something fails, you know exactly where — not just which agent, but at which layer of the system's reasoning it broke down.

Instead of assigning agents by job title, the harness allocates components by **representational function** — what each component perceives, what invariants it enforces, and at what level of abstraction it operates. The theoretical grounding is Rasmussen's Abstraction Hierarchy (AH), a framework from cognitive work analysis that structures system behaviour around domain constraints and abstraction levels rather than inherited workplace metaphors.

The result is a harness that is less like an org chart and more like a constraint-and-affordance structure. Agents are not defined primarily by "who does the task" but by "what kind of representation they hold" and "what means-ends relations they are allowed to act on."

---

## Architecture: five AH layers

| Layer | Name | CogTrace Component | Role |
|---|---|---|---|
| L5 | Functional Purpose | Goal Governor | Mission objectives, ethical bounds, success criteria |
| L4 | Abstract Function | Constraint Reasoner + MECC | Invariants, conservation constraints, safety predicates |
| L3 | Generalized Function | Workflow Orchestrator | Standard operational patterns, fallback chains |
| L2 | Physical Function | Capability Router | Tool specs, API contracts, model capabilities |
| L1 | Physical Form | Execution Substrate (LangGraph) | HTTP calls, file I/O, LLM invocations |

**LangGraph operates only at L1.** This is architecturally deliberate — execution substrate concerns (graph nodes, edges, conditional routing) do not bleed into L2–L5.

---

## The MECC

The **Means-Ends Consistency Checker** is the harness's core primitive — a cross-layer admissibility gate:

```
MECC(A, L) = permitted(A, L)  ∧  (∀k ≥ L: ¬violates(A, C_k))  ∧  (∃g ∈ G: advances(A, g))
```

Before any action executes — external API call, verdict emission, escalation — MECC checks it against constraints at **all layers at or above** the action's origin layer. A policy evaluator checks rules at one layer. MECC enforces the full hierarchy at runtime.

MECC fires:
- Before any external API call
- Before any verdict is emitted
- Before any escalation is triggered
- After any agent proposes an action

---

## Scenarios

### Citation Integrity (primary demo)

Verifies whether citations in a document actually exist and match what they claim to be. Motivated by a May 2026 Lancet audit finding fabricated or mismatched citations in 2.5 million biomedical papers.

**What it checks (v1 — bibliographic integrity):**

| Constraint | Layer | Rule |
|---|---|---|
| C008 | L3 | Citation must have a parseable DOI or arXiv identifier |
| C006 | L3 | API must respond within 5 seconds or fall back to fixture |
| C007 | L3 | At least one citation must be verifiable to proceed |
| C001 | L4 | DOI must resolve to a real Crossref or PubMed record |
| C002 | L4 | Resolved title fuzzy-match ≥ 0.85 |
| C003 | L4 | Year must match ±1 |
| C004 | L4 | Venue must match if provided |
| C005 | L4 | Claim support (semantic) — **v2 only, not evaluated in this build** |

The demo sample exercises all three failure modes: a valid citation that passes all checks, a fabricated DOI that triggers C001 (FABRICATED), a real DOI with a misattributed title that triggers C002 (MISMATCHED), and a citation with no identifier that triggers C008 at L3.

**Failure examples by layer:**

| Layer | What happened | Constraint | Outcome |
|---|---|---|---|
| L3 | `"Undocumented Findings…"` — no DOI or arXiv ID in the text | C008 | Blocked at parse time; retrieval never attempted |
| L4 | `"A Revolutionary Biomedical Agent Pipeline"` with invented DOI `10.1038/…99999-x` | C001 | DOI resolves to nothing — FABRICATED |
| L4 | Correct ReAct DOI but title swapped to "Chain-of-Thought Prompting…" | C002 | Title similarity 0.11, far below 0.85 — MISMATCHED |
| L5 | All citations in a batch are unverifiable | C007 | Escalates to Functional Purpose layer — workflow blocked |

### Sensor Escalation

Three independent sensor agents — seismic, tsunami, and impact — report on incoming USGS earthquake events. The harness reconciles their findings across all five AH layers using a dedicated cross-sensor MECC that can see all three agents simultaneously (no individual agent can). The key architectural case: a large-magnitude deep-focus earthquake where sensors contradict each other triggers the LLM assessor at L4 to resolve the ambiguity rather than escalating blindly.

**Failure examples by layer:**

| Layer | What happened | Constraint | Outcome |
|---|---|---|---|
| L2 | Event ID not found in fixture or live USGS API | C-SE006 | Unresolvable — nothing to evaluate |
| L4 | M 7.6, tsunami flag=1, orange PAGER alert | C-SE002 + C-SE004 | Hard escalation to CRITICAL — LLM assessor deliberately suppressed |
| L4 | M 5.8, yellow PAGER, CDI 4.1 | C-SE003 | Seismic monitoring ALERT |
| L4 | M 6.8 deep-focus, CDI 1.8, null alert (`us6000abcd4`) | C-SE005 | Cross-agent inconsistency — SeismicAgent says escalate, ImpactAgent says nominal. LLM assessor resolves to NOMINAL. This is the key architectural case. |
| L5 | No events in batch could be evaluated | C-SE007 | Escalates to Functional Purpose layer |

### Destructive Action

A decision gate for proposed system operations. Irreversible or high-risk operations (dropping tables, deleting data) are blocked outright by hard L4 constraints. Borderline cases are escalated to L5 for human approval. Nothing is executed — this is an admissibility check, not an execution engine.

---

## Distributed cognition

No single agent has the full picture:

- **Parser** sees raw text — doesn't know if citations are real
- **Retriever** sees API responses — doesn't know the claims
- **Verifier** sees metadata matches — doesn't know semantic support
- **Assessor** sees claim-source pairs — doesn't know API availability
- **MECC** sees all constraints — doesn't execute any action

Only the system together produces the answer. The architecture makes distributed cognition visible rather than hiding it inside a single orchestrator.

---

## W&B Weave integration

Every significant event emits a Weave trace span:

- `layer_transition` — source and target layer, trigger
- `mecc_evaluation` — action, layer, constraints checked, pass/fail
- `agent_output` — agent name, layer, confidence, proposed action
- `constraint_violation` — policy ID, severity, escalation target
- `citation_verdict` — item ID, status, constraints fired
- `scenario_complete` — totals, latency, cost

The Streamlit dashboard pulls real latency data back from Weave spans and displays it inline. Human feedback (👍/👎) is logged to the W&B classic dashboard per run. Verdict tables accumulate across runs as `wandb.Table` entries for longitudinal comparison.

---

## For W&B Weave judges

### What to look for in the Weave UI

**Traces tab** (project → Weave → Traces):
- Each pipeline run is a root span: `CitationIntegrityScenario.evaluate` or `SeismicEscalationScenario.evaluate`
- Expand any root span to see the full child span tree: `_retrieve`/`_lookup_event` (L2), `MECC.evaluate` × N (L2–L5), `assess`/`judge` (L4, LLM only when ambiguous)
- Every `MECC.evaluate` span carries custom attributes set via `weave.attributes()`:
  - `ah_layer` — integer (2, 3, 4, or 5)
  - `ah_layer_name` — e.g. `"Abstract Function (Constraint Reasoner)"`
  - `mecc_action` — e.g. `"emit_verdict"`, `"parse_citation"`, `"scenario_complete"`
  - `scenario` — `"citationintegrity"` or `"sensorescalation"`
- Use the Weave filter bar to slice the trace tree by `ah_layer_name` — this shows all MECC checks at a given abstraction level across all runs
- Spans with non-empty `violated_constraints` in their output are the failure events

**Evaluations tab** (project → Weave → Evaluations):

Run these to populate the Evaluations tab:
```bash
python tests/eval_citation_integrity.py
python tests/eval_sensor_escalation.py
```

- `agah-citation-integrity-v1` — 5 test cases, 3 scorers: `verdict_correct`, `constraint_fired`, `pipeline_health`
- `agah-seismic-escalation-v1` — 5 test cases, 4 scorers including `assessor_fired` — the architectural claim: the LLM assessor fires for `us6000abcd4` (C-SE005 cross-agent inconsistency) but NOT for hard-constraint events like `us6000abcd3` (C-SE002 tsunami). This is verifiable in the evaluation results.

**Tables / workspace** (project → workspace):
- `citationintegrity/verdict_log` — per-item verdict table accumulating across all demo runs
- `citationintegrity/mecc_violations`, `total_items` — scalar metrics per run, charted over time
- `*/human_feedback` — 👍/👎 ratings submitted from the Streamlit UI

### The architectural claim the traces demonstrate

The Weave span tree shows constraint checking is not flat. Violations surface at different AH layers depending on what kind of constraint fired:

- **L2 spans**: capability routing checks (API gate before any retrieval)
- **L3 spans**: workflow-level checks (C008 no identifier, C007 nothing verifiable) — fire before any L4 evaluation
- **L4 spans**: bibliographic and sensor constraint checks (the main verification logic)
- **L5 spans**: synthesis checks (C007/C-SE007 scenario-complete gate)

This layering is enforced at runtime by the MECC, not just described in documentation. The `ah_layer` attribute on each span makes the hierarchy directly observable in the Weave UI.

---

## Setup

```bash
git clone <repo>
cd AGIhack
pip install -r requirements.txt
```

Create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
WANDB_API_KEY=...
WEAVE_PROJECT=agah-hackathon   # optional, defaults to agah-hackathon
```

Run the Streamlit app:

```bash
streamlit run app/streamlitapp.py
```

Run the unit test:

```bash
pytest tests/testmecc.py
```

Run the Weave evaluations (publishes to W&B):

```bash
python tests/eval_citation_integrity.py
python tests/eval_sensor_escalation.py
```

---

## Tech stack

| Component | Choice | Notes |
|---|---|---|
| LLM | claude-sonnet-4-20250514 | Assessor agent for ambiguous cases only |
| Execution substrate | LangGraph | L1 only — not the architecture |
| Constraint config | YAML | Swappable per scenario |
| Citation APIs | Crossref REST + arXiv | Free, no auth; fixtures as fallback |
| Observability | W&B Weave | Traces every MECC evaluation and layer transition |
| UI | Streamlit | Logo-driven header, live Weave span latency table |
| Language | Python 3.11+ | |

---

## Project layout

```
agah_harness/
  core/
    mecc.py          # MECC — cross-layer admissibility gate
    state.py         # HarnessState, MECCResult, FailureRecord
    policies.py      # YAML constraint loader
    engine.py        # Orchestration loop
    trace.py         # TraceEvent emitter + Weave hooks
  agents/
    llm.py           # Anthropic wrapper (AssessorAgent)
  scenarios/
    citationintegrity/   # Full pipeline + fixtures
    sensorescalation/    # Full pipeline + fixtures
    destructiveaction/   # Admissibility gate
app/
  streamlitapp.py    # UI
  ah_viz.py          # Plotly AH trace chart
tests/
  testmecc.py                  # Unit test
  eval_citation_integrity.py   # Weave evaluation
  eval_sensor_escalation.py    # Weave evaluation
```

---

## Why not LangGraph / CrewAI / AutoGen for the harness?

Those frameworks are excellent execution substrates. CogTrace uses LangGraph at L1 for exactly that purpose. What they don't provide is an explicit mechanism for cross-layer constraint enforcement — a way to ask, before any action executes, whether it is admissible with respect to constraints at all levels of abstraction above it. That is what the MECC provides, and it is what makes the harness more than a workflow runner.

The distinction matters most in settings where human-agent collaboration is real and distributed — where multiple people each operate semi-autonomous agent ecosystems and must still coordinate effectively. Without a shared abstraction structure, collaboration collapses into either opaque agent-to-agent interactions or excessive routing back through humans. The Abstraction Hierarchy provides a principled coordination scaffold for those cases.
