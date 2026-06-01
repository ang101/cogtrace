# CogTrace Demo Script
# Target: 3 minutes | Screen-record the Streamlit app while reading this

---

## [0:00–0:20] THE HOOK

A study published in the Lancet in May 2026 audited 2.5 million biomedical papers
and found fabricated and mismatched citations at scale.

Not just plagiarism — citations to papers that don't exist.
References where the DOI resolves to a completely different study.

This is a trust problem. And it's a hard problem to catch automatically.

Not because the models aren't good enough —
because the *harness* isn't designed to catch it.

---

## [0:20–0:50] THE PROBLEM

[DEMO: keep the app visible but don't interact yet]

Most multi-agent systems today are designed like org charts.
You've got a Researcher agent. A Reviewer agent. A Critic.

That pattern is intuitive, but it imports human organizational assumptions
into systems that don't have human cognitive limits or role identities.

The agents end up doing overlapping work, passing full context to each other,
and there's no principled way to decide *which agent* should catch *which failure*.

---

## [0:50–1:20] THE SOLUTION — AGAH

CogTrace is built on a different principle.

Rasmussen's Abstraction Hierarchy — a framework from cognitive engineering —
gives us five distinct levels of representation in any work domain.

Instead of naming agents by job title, we allocate them by representational function:
what information they're allowed to see, what constraints they enforce,
and which layer of the domain they inhabit.

[DEMO: point at the sidebar — show the layer labels]

At the top, Layer 5: the Goal Governor. Mission objectives, ethical bounds.
Layer 4: the Constraint Reasoner — this is where MECC lives.
Layer 3: Workflow Orchestrator. Standard patterns, fallback chains.
Layer 2: Capability Router. API contracts, model specs.
Layer 1: LangGraph. HTTP calls, LLM invocations. That's all it does.

LangGraph is deliberately at the bottom. It's the execution substrate, not the architecture.

---

## [1:20–1:35] THE MECC

The key primitive is the MECC — Means-Ends Consistency Checker.

Before any external API call, before any verdict is emitted,
MECC checks the proposed action against constraints at *every layer above it*.

It's not a policy list. It's a cross-layer admissibility gate.
That's what makes the hierarchy enforced at runtime, not just described.

---

## [1:35–1:50] DEMO SETUP

[DEMO: point at the text area in the sidebar]

I've got four citations loaded. Let me walk you through what they are:

- Citation 1: Yao et al. 2023 — the ReAct paper. Real DOI, correct title, correct year. Should be VALID.
- Citation 2: Smith et al. 2024 — a paper in Nature with a DOI ending in 99999-x. This one doesn't exist.
- Citation 3: Same real DOI as Citation 1, but the title has been swapped to a different paper. Should be MISMATCHED.
- Citation 4: No DOI at all. Can't even begin verification.

[DEMO: click "Run CogTrace pipeline"]

---

## [1:50–2:15] THE FABRICATED BADGE

[DEMO: pause — let results load — then point at Citation 2]

There it is.

Citation 2 — DOI 10.1038/s41586-2024-99999-x — Crossref returns a 404.
Constraint C001 fires at Layer 4.
Verdict: FABRICATED.

[DEMO: pause 2 seconds on the red badge]

That's not a model judgment call. That's a hard constraint, enforced by MECC,
at the right layer, before anything else could execute.

Now look at Citation 3 — MISMATCHED.
Title similarity came back at 0.11. Way below the 0.85 threshold.
In this case the assessor — the only LLM call in the pipeline —
was invoked to confirm: is this ambiguous, or is this clearly wrong?

It confirmed: clearly wrong. Different paper entirely.

---

## [2:15–2:45] THE WEAVE TRACE

[DEMO: scroll down to the Abstraction Hierarchy trace chart]

This is the architecture diagram made live.

Each dot is an event. Each horizontal band is a layer.
Green is valid. Orange is a mismatch. Red is fabricated.
The purple diamonds are assessor invocations — the LLM was called here, and only here.
The stars are verdicts emitted.

[DEMO: hover over a red diamond if possible]

You can see the escalation arrow — when MECC fires a violation at Layer 4,
it surfaces to Layer 5. The Goal Governor decides: do we have enough to proceed?

We do — Citation 1 is valid — so the run completes.

[DEMO: point at Weave link or the latency table on the right]

Every one of these events is a Weave span in W&B.
Filterable by layer. Queryable by constraint ID.
This is the observability story — the hierarchy is inspectable end to end.

---

## [2:45–3:00] THE CLOSE

[DEMO: show the scenario selector in the sidebar]

The same harness runs three scenarios.
Citation integrity is the demo — but there's also destructive action safety
and sensor escalation for seismic events.

Different domain. Different YAML constraints. Same five layers. Same MECC gate.

That's the point of AGAH — the abstraction hierarchy is the architecture.
Swap the scenario, the structure holds.

Thank you.

---

## Recording Tips

- Run the app before recording: `streamlit run app/streamlitapp.py`
- Use Windows Game Bar (Win+G) or OBS to screen-record
- Set browser to fullscreen (F11) for a cleaner frame
- Paste the 4-citation input into the sidebar text area before hitting record
- Read at a steady pace — 3 minutes is ~420 words, you have ~600 here, so take your time
- The natural pause after the FABRICATED badge lands best — don't rush past it
