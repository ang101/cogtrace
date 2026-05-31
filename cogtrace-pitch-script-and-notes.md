# CogTrace Pitch Script and Speaker Notes

## Title
**CogTrace**

**Tagline:** Constraint-guided harnesses for trustworthy AI work systems

**Sub-brand / architecture name:** AGAH — Abstraction-Grounded Agentic Harness

---

## 3–4 Minute Judge Pitch

A May 2026 *Lancet* study audited 2.5 million biomedical papers and 125 million references, and found fabricated and mismatched citations at scale.[cite:1][cite:2]

Most agent demos still struggle with this because they are built like org charts — researcher, reviewer, critic — instead of being built like work systems.[cite:2]

CogTrace is our answer. CogTrace is the product brand, and AGAH is the architecture inside it.[cite:1][cite:2]

The simple idea is that real work does not happen as a straight line of prompts. Real work moves across levels: why the system exists, what counts as acceptable, what functions must happen, what capabilities are available, and what actually gets executed.[cite:1][cite:2]

So instead of assigning AI components fake job titles, we organize them around the structure of the work itself.[cite:2]

In AGAH, that becomes five layers. L5 is mission and success criteria. L4 is constraints and admissibility. L3 is the workflow pattern. L2 is capability routing. L1 is execution substrate — and that is the only place LangGraph lives.[cite:1][cite:2]

That separation matters because we are not presenting a LangGraph wrapper with extra narrative. The architecture is above the graph. The graph is just the runtime substrate.[cite:1][cite:2]

The key primitive is MECC, the Means-Ends Consistency Checker. In plain English, it asks: before this action happens, is it allowed by higher-level constraints, and does it actually advance the system goal?[cite:1][cite:2]

That means before an API call, before a verdict, before an escalation, the system checks cross-layer admissibility.[cite:1][cite:2]

For the hackathon, we use one proof case: citation integrity verification. In v1, that means DOI resolution, title match, year match, and venue match. We are intentionally not overclaiming semantic claim support — that is marked as v2.[cite:1][cite:2]

The demo is simple: paste three citations. One is valid, one is fabricated, and one is mismatched.[cite:1][cite:2]

When the fabricated citation is processed, the DOI does not resolve, constraint C001 fires at L4, MECC blocks trust, and the UI shows a red FABRICATED badge. At the same time, Weave shows the exact same event live in the trace.[cite:1][cite:2]

That is why CogTrace is not just another agent app. It makes the work structure visible. Judges can see why the system blocked an action, at what layer, and based on which constraint.[cite:1][cite:2]

And this is also why the system is multi-agent in a meaningful sense. No single component has the full picture. The parser sees raw text, the retriever sees APIs, the verifier sees metadata consistency, the assessor handles ambiguity, and MECC sees admissibility across the hierarchy.[cite:1][cite:2]

So the contribution is not “we built a citation checker.” The contribution is that we built a harness architecture for trustworthy AI work systems — one that replaces the AI org chart with explicit goals, guardrails, capabilities, and actions.[cite:1][cite:2]

Today the demo case is citation integrity. Tomorrow the same harness can support other work domains. That is the point of CogTrace: architecture first, scenario second.[cite:1][cite:2]

---

## Slide-by-slide speaker notes

### Slide 1 — CogTrace
- Say: “CogTrace is the brand. AGAH is the architecture inside it.”
- Say: “We build constraint-guided harnesses for trustworthy AI work systems.”
- Goal: establish brand shift immediately.[cite:1][cite:2]

### Slide 2 — The problem
- Say: “Most agent systems still look like org charts.”
- Say: “That is useful for demos, but it is not how complex work is structured.”[cite:2]

### Slide 3 — Better mental model
- Say: “Instead of copying employee roles, we model how work actually gets done: goals, constraints, patterns, capabilities, and substrate.”[cite:1][cite:2]
- Say: “This is the shift from workflow theater to work-system design.”

### Slide 4 — Five layers
- Walk top to bottom.
- Emphasize: “LangGraph is only at L1.”[cite:1][cite:2]
- Emphasize: “The architecture lives above the runtime graph.”

### Slide 5 — MECC
- Say: “MECC is our enforcement primitive.”[cite:1][cite:2]
- Say: “It does not just ask whether one rule passes. It asks whether an action is still admissible in light of the larger system goals.”[cite:1][cite:2]

### Slide 6 — Why better for AI systems
- Say: “Smaller agents, lower context load, more explainable failures, less black-box behavior.”[cite:2]
- Say: “This is about trustworthy coordination, not more agent chatter.”

### Slide 7 — Citation proof case
- Say: “Citation integrity is the demo vehicle, not the final product.”[cite:1][cite:2]
- Say: “It gives us a visible proof case for fabricated and mismatched references.”[cite:1][cite:2]

### Slide 8 — Implementation anatomy
- Say: “The code structure mirrors the theory: typed state, MECC, policies, traces, scenario adapters, Streamlit, and Weave.”[cite:1][cite:2]
- Say: “The architecture is visible in the repo, not hidden in prompts.”

### Slide 9 — Observability
- Say: “Weave turns the architecture diagram into runtime evidence.”[cite:1][cite:2]
- Say: “That makes this a strong Best Use of Weave story.”[cite:1][cite:2]

### Slide 10 — Roadmap
- Say: “We are precise about scope: claim support is v2, portability is demonstrated by stubs, not overclaimed.”[cite:1][cite:2]
- Say: “That honesty makes the architecture stronger.”

### Slide 11 — Closing
- Say: “The demo proves the point, but the real product is the harness.”[cite:1][cite:2]
- Final line: “CogTrace replaces the AI org chart with a real work system.”
