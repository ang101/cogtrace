from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

# ── AH Layer metadata ─────────────────────────────────────────────────────────

LAYER_LABELS: dict[int, str] = {
    5: "L5 Functional Purpose",
    4: "L4 Abstract Function (MECC)",
    3: "L3 Generalized Function",
    2: "L2 Physical Function",
    1: "L1 Physical Form",
}

# Okabe-Ito color-blind safe palette anchored to #1A4D2E (user spec)
_PALETTE = {
    "valid":      "#1A4D2E",   # forest green — pass/valid         contrast 8.5:1
    "mecc_pass":  "#0072B2",   # blue          — MECC evaluated ok  contrast 5.7:1
    "violation":  "#D55E00",   # vermilion     — constraint blocked  contrast 4.6:1
    "escalation": "#E69F00",   # amber/orange  — escalation/alert   (fill only)
    "assessor":   "#CC79A7",   # reddish-purple — LLM assessor fired
    "neutral":    "#4B5563",   # mid-gray       — normal trace event contrast 7.0:1
    "substrate":  "#9CA3AF",   # light gray     — L1 decoration
}

# Semi-transparent fills for the five layer bands
_LAYER_FILLS: dict[int, str] = {
    5: "rgba(26,77,46,0.07)",    # L5 dark-green tint
    4: "rgba(0,114,178,0.07)",   # L4 blue tint  (MECC layer)
    3: "rgba(230,159,0,0.06)",   # L3 amber tint
    2: "rgba(86,180,233,0.06)",  # L2 sky-blue tint
    1: "rgba(153,153,153,0.05)", # L1 gray tint
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _event_color(event: Any) -> str:
    if event.violationflag or event.status in {"FABRICATED", "blocked", "CRITICAL"}:
        return _PALETTE["violation"]
    if event.status in {"MISMATCHED", "ESCALATED", "ALERT"}:
        return _PALETTE["escalation"]
    if event.metadata.get("cross_agent_inconsistency") or event.metadata.get("assessor_used"):
        return _PALETTE["assessor"]
    if event.meccfired and not event.violationflag:
        return _PALETTE["mecc_pass"]
    if event.layer == 1:
        return _PALETTE["substrate"]
    return _PALETTE["neutral"]


def _event_symbol(event: Any) -> str:
    if event.event_type in {"actionverdict", "citationverdict"}:
        return "star"
    if event.meccfired:
        return "diamond"
    return "circle"


def _event_size(event: Any) -> int:
    if event.meccfired and event.violationflag:
        return 15
    if event.meccfired:
        return 13
    if event.event_type in {"actionverdict", "citationverdict"}:
        return 13
    return 9


def _hover_text(event: Any, idx: int) -> str:
    ts = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
    layer_name = LAYER_LABELS.get(event.layer, f"L{event.layer}")
    constraints = event.metadata.get("violatedconstraints") or event.metadata.get("constraintsfired")
    c_line = f"<br><b>Constraints:</b> {', '.join(constraints)}" if constraints else ""
    return (
        f"<b>{layer_name}</b><br>"
        f"<b>Type:</b> {event.event_type}<br>"
        f"<b>Time:</b> {ts}<br>"
        f"<b>Source → Target:</b> {event.source} → {event.target}<br>"
        f"<b>Status:</b> {event.status}"
        f"{c_line}<br>"
        f"<i>{event.message[:120]}</i>"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def build_ah_figure(trace_events: list, verdicts: list, scenario_type: str) -> go.Figure:
    """Build a Plotly AH trace figure from HarnessState.traceevents.

    Five horizontal bands (L1–L5) with events as scatter points.
    Colors are Okabe-Ito color-blind safe; shapes encode event type.
    MECC violations show upward escalation arrows.
    Grid lines are suppressed; only layer band fills and dotted separators remain.
    """
    fig = go.Figure()

    if not trace_events:
        fig.add_annotation(
            text="No trace events — run a scenario to generate the AH trace",
            x=0.5, y=3, xref="paper", yref="y",
            showarrow=False, font=dict(size=14, color="#4B5563"),
        )
        _apply_layout(fig, scenario_type, 0)
        return fig

    # 1. Layer band fills
    for layer, fill in _LAYER_FILLS.items():
        fig.add_hrect(
            y0=layer - 0.45, y1=layer + 0.45,
            fillcolor=fill, line_width=0, layer="below",
        )

    # 2. Subtle dotted separators between layers
    for y in [1.5, 2.5, 3.5, 4.5]:
        fig.add_hline(y=y, line_width=0.5, line_color="#E5E7EB", line_dash="dot")

    # 3. Faint connecting line across all events
    fig.add_trace(go.Scatter(
        x=list(range(len(trace_events))),
        y=[e.layer for e in trace_events],
        mode="lines",
        line=dict(width=0.8, color="#D1D5DB", dash="dot"),
        hoverinfo="skip",
        showlegend=False,
    ))

    # 4. One scatter point per event
    for i, event in enumerate(trace_events):
        fig.add_trace(go.Scatter(
            x=[i],
            y=[event.layer],
            mode="markers",
            marker=dict(
                color=_event_color(event),
                size=_event_size(event),
                symbol=_event_symbol(event),
                line=dict(width=1.5, color="#111827"),
                opacity=0.92,
            ),
            hovertemplate=_hover_text(event, i) + "<extra></extra>",
            showlegend=False,
        ))

    # 5. Escalation arrows: MECC violations at L4 → upward to L5
    for i, event in enumerate(trace_events):
        if event.meccfired and event.violationflag and event.layer == 4:
            fig.add_annotation(
                x=i, y=4.45, ax=i, ay=4.85,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=2, arrowsize=1.2,
                arrowcolor=_PALETTE["violation"],
                arrowwidth=1.8,
                text="", hovertext="Constraint violation → L5 escalation",
            )

    _apply_layout(fig, scenario_type, len(trace_events))
    return fig


def _apply_layout(fig: go.Figure, scenario_type: str, n_events: int) -> None:
    verdict_label = {
        "citationintegrity": "Citation Integrity",
        "destructiveaction": "Destructive Action",
        "sensorescalation": "Sensor Escalation",
    }.get(scenario_type, scenario_type)

    fig.update_layout(
        title=dict(
            text=f"Abstraction Hierarchy Trace — {verdict_label} — {n_events} events",
            font=dict(size=14, color="#111827", family="Inter, system-ui, sans-serif"),
            x=0,
        ),
        xaxis=dict(
            title=dict(text="Event sequence", font=dict(color="#4B5563", size=11)),
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#4B5563", size=10),
        ),
        yaxis=dict(
            tickvals=[1, 2, 3, 4, 5],
            ticktext=[LAYER_LABELS[i] for i in [1, 2, 3, 4, 5]],
            showgrid=False,
            zeroline=False,
            range=[0.4, 5.6],
            tickfont=dict(color="#111827", size=11),
        ),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=210, r=40, t=50, b=50),
        height=420,
        font=dict(family="Inter, system-ui, sans-serif", color="#111827"),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#E5E7EB",
            font=dict(size=12, color="#111827"),
        ),
    )
