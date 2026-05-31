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

## Why this architecture — token economics, model efficiency, and the distributed cognition thesis

### The immediate problem: monolithic orchestrators are wasteful

Most agentic systems today use a single large model as the orchestrator. That model receives the full context, reasons about what to do next, calls tools, receives results, and reasons again. Every step — including trivial routing decisions — pays full token cost for a frontier model.

CogTrace's architecture changes this as a direct consequence of structure, not optimization. The MECC is not an LLM. It is a deterministic constraint checker that runs before any LLM call. In the citation integrity scenario:

- **L3 constraints** fire first — does this citation have a parseable identifier at all? If not, retrieval is blocked before any API call is attempted.
- **L4 constraints** fire next — does the DOI resolve? Does the title match? These checks are deterministic. No model call needed.
- **The LLM assessor fires only on genuine ambiguity** — cross-agent inconsistency that no rule can resolve. In most runs, it never fires.

In the sensor escalation scenario, three sensor agents each hold a narrow slice of evidence. The cross-sensor MECC is the only component that sees all three simultaneously — and it is deterministic. For four of the five test cases, constraints resolve the outcome without a model call. The LLM fires only for the structurally ambiguous case: deep-focus earthquake, contradicting sensor readings, null PAGER alert.

This is a structural property of the architecture, not a tuning choice. When constraints are explicit and layered, most decisions are resolved before they become model calls. The token savings are a consequence of knowing what each layer is responsible for and enforcing it before escalating upward.

### The end game: smaller specialized models outperform large generalists

The deeper argument for this architecture is about what happens when each layer is occupied by a model scoped to that layer's representational function.

A large generalist model forced to reason about goal-level objectives, workflow patterns, API contracts, and raw execution simultaneously faces structural disadvantages:

- **Attention dilution** — relevant signals compete with irrelevant context across abstraction levels. The model attends to everything when it should attend to the layer's specific concern.
- **Hallucination leakage** — uncertainty at one level propagates to another because the model holds both simultaneously. A model unsure whether an API exists may hallucinate confidence at the goal level.
- **Context cost** — full-context reasoning at every step is expensive even when most of the context is irrelevant to the decision at hand. A workflow routing decision does not need to see raw execution logs.

A small model scoped to a single layer does not have these problems. It only sees what its layer is responsible for. The parser never sees API state. The verifier never sees goal-level objectives. The MECC never executes anything. Each component can be calibrated within its own representational domain — a much tighter target than calibrating a general-purpose orchestrator across all levels simultaneously.

The research trajectory supports this direction. Smaller, domain-focused models — fine-tuned or distilled for a narrow task — increasingly match or exceed large generalists on those tasks. The open question is what the principled basis for scoping should be. Job title is not it: "researcher" and "reviewer" have no natural boundary in a reasoning system. Abstraction level is: scope by what a component needs to perceive, what invariants it is responsible for enforcing, and what means-ends relations it is allowed to act on.

CogTrace is built so any layer can be occupied by any model — or no model at all:

| Layer | Currently | Could be |
|---|---|---|
| L5 Functional Purpose | Human escalation / goal config | Small goal-evaluation model, fine-tuned on mission objectives |
| L4 Abstract Function | Deterministic MECC + LLM on ambiguity only | Constraint-specialized small model |
| L3 Generalized Function | Deterministic orchestrator | Pattern-routing model, few-shot or fine-tuned |
| L2 Physical Function | Deterministic capability router | Capability-matching model |
| L1 Physical Form | LangGraph | Any execution substrate |

Swapping a fine-tuned small model into any layer requires no architectural change — only a component swap behind the layer interface. The harness is the coordination structure; the models are pluggable.

### Calibration as a first-class property

A less visible but consequential consequence of the layered structure is calibration isolation. In a monolithic orchestrator, overconfidence at one reasoning level propagates freely. In CogTrace, each layer's output is checked by the MECC before it can affect the layer above. A verifier that returns a low-confidence match does not silently advance to a goal-level verdict — the constraint at L4 catches it and either blocks or escalates.

This makes calibration failures visible and locatable. The Weave traces show exactly which layer a constraint fired at, which component produced the output, and what the outcome was. Debugging a calibration failure in a monolithic system means reading through a long trace and inferring where reasoning went wrong. In CogTrace, the layer and constraint are tagged on every span — the failure is observable by construction.

This also enables meaningful longitudinal tracking. Because every MECC evaluation is a named span with a layer attribute, you can ask: across 100 runs, which layer fails most often? Which constraint fires most? Is the L4 assessor being invoked more than expected? These are questions a flat trace cannot answer.

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

The key distinction from a guardrails library or a policy checker: MECC is not a post-hoc filter. It runs before execution, checks upward across all layers, and either permits, blocks, or escalates. It does not just flag — it gates.

---

## Distributed cognition

No single agent has the full picture:

- **Parser** sees raw text — doesn't know if citations are real
- **Retriever** sees API responses — doesn't know the claims
- **Verifier** sees metadata matches — doesn't know semantic support
- **Assessor** sees claim-source pairs — doesn't know API availability
- **MECC** sees all constraints — doesn't execute any action

Only the system together produces the answer. The architecture makes distributed cognition visible rather than hiding it inside a single orchestrator.

This is not just a design pattern — it is the condition that enables smaller specialized models to work. Each component only needs to be good at its own slice. The coordination structure — the MECC and the layer interfaces — handles integration. Competence is distributed across the system rather than concentrated in one large model that must be good at everything.

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

The second thing to verify: how often the LLM assessor fires versus how often constraints resolve the outcome without it. In a well-structured harness, most decisions should be resolved by constraints. LLM invocations should be the exception, not the default. The `assessor_fired` scorer in the seismic evaluation makes this directly measurable.

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

The distinction also matters for the distributed cognition end game. LangGraph, CrewAI, and AutoGen are all designed around the assumption that a large model is doing the reasoning and the framework is managing its flow. If you want to move toward an architecture where each layer is occupied by a smaller, specialized model, you need a coordination structure that does not assume a large central reasoner. The Abstraction Hierarchy provides that structure. The layer interfaces define what each component sees and what it is allowed to act on — independently of what model sits behind them.

The distinction matters most in settings where human-agent collaboration is real and distributed — where multiple people each operate semi-autonomous agent ecosystems and must still coordinate effectively. Without a shared abstraction structure, collaboration collapses into either opaque agent-to-agent interactions or excessive routing back through humans. The Abstraction Hierarchy provides a principled coordination scaffold for those cases.

---

## Roadmap

The current build is a proof of architecture. The path forward:

**v2 — semantic constraints**
- C005: claim support checking — does the cited source actually support the claim made? Requires embedding-based or LLM-based semantic comparison at L4.
- Extend sensor escalation to multi-event batch reconciliation across time windows.

**v3 — model substitution**
- Replace deterministic L3 orchestrator with a small fine-tuned routing model. Measure whether constraint violation rates change.
- Introduce a small L4 constraint model trained on MECC decisions. Compare against deterministic baseline.
- Benchmark: does a specialized small model at L4 match the LLM assessor on the ambiguous cases while costing a fraction of the tokens?

**v4 — multi-agent coordination scaffold**
- Extend the harness to multi-human, multi-agent teams. Each human operator runs their own agent ecosystem; the AH provides the shared coordination layer.
- Human-in-the-loop escalation at L5 becomes a structured handoff, not an interrupt.

The architectural claim this roadmap tests: **distributed cognition with layer-scoped small models outperforms a single large orchestrator on cost, latency, and calibration** — because each component only has to be good at its own slice, and the constraint structure handles integration.
