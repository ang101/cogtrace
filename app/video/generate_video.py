#!/usr/bin/env python3
"""
CogTrace Demo Video Generator

Install dependencies first:
    pip install edge-tts "moviepy==1.0.3" pillow numpy

Then run:
    python app/video/generate_video.py

Output: app/video/cogtrace_demo.mp4  (~3 minutes)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── paths ─────────────────────────────────────────────────────────────────────
OUT_DIR   = Path(__file__).parent
AUDIO_DIR = OUT_DIR / "_audio"
OUTPUT    = OUT_DIR / "cogtrace_demo.mp4"

# ── settings ──────────────────────────────────────────────────────────────────
W, H  = 1920, 1080
FPS   = 24
VOICE = "en-US-AriaNeural"

# ── palette ───────────────────────────────────────────────────────────────────
BG     = (12,  14,  22)
PANEL  = (22,  26,  40)
WHITE  = (238, 241, 248)
DIM    = (115, 122, 150)
ACCENT = (88,  166, 255)
GREEN  = (46,  200,  87)
RED    = (220,  45,  45)
ORANGE = (255, 148,  25)
PURPLE = (178,  98, 220)
GRAY   = ( 90,  95, 115)

LAYER_C = {
    5: (52,  168,  83),
    4: (240, 180,  30),
    3: ( 66, 133, 244),
    2: ( 98, 118, 142),
    1: ( 72,  76,  90),
}
LAYER_N = {
    5: "Functional Purpose",
    4: "Abstract Function",
    3: "Generalized Function",
    2: "Physical Function",
    1: "Physical Form",
}
LAYER_A = {
    5: "Goal Governor",
    4: "Constraint Reasoner + MECC",
    3: "Workflow Orchestrator",
    2: "Capability Router",
    1: "LangGraph (execution only)",
}

# ── fonts ─────────────────────────────────────────────────────────────────────
_FCACHE: dict = {}


def fnt(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold, mono)
    if key in _FCACHE:
        return _FCACHE[key]
    if mono:
        paths = [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
    elif bold:
        paths = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    else:
        paths = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    f: ImageFont.FreeTypeFont = ImageFont.load_default()
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            break
        except Exception:
            pass
    _FCACHE[key] = f
    return f


# ── helpers ───────────────────────────────────────────────────────────────────

def new_frame(bg: tuple = BG) -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)


def text_size(draw: ImageDraw.Draw, text: str, f: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def cx(draw: ImageDraw.Draw, text: str, y: int, f: ImageFont.FreeTypeFont,
        color: tuple = WHITE) -> None:
    tw, _ = text_size(draw, text, f)
    draw.text(((W - tw) // 2, y), text, font=f, fill=color)


def wrap_text(draw: ImageDraw.Draw, text: str, x: int, y: int, max_w: int,
              f: ImageFont.FreeTypeFont, color: tuple = WHITE, gap: int = 6) -> int:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        tw, _ = text_size(draw, test, f)
        if tw <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    total = 0
    for line in lines:
        draw.text((x, y + total), line, font=f, fill=color)
        _, lh = text_size(draw, line, f)
        total += lh + gap
    return total


def pill(draw: ImageDraw.Draw, x: int, y: int, label: str, bg: tuple,
         fg: tuple = WHITE, pad: int = 14, r: int = 8) -> int:
    f = fnt(28, bold=True)
    tw, th = text_size(draw, label, f)
    x1, y1 = x + tw + pad * 2, y + th + pad
    draw.rounded_rectangle([x, y, x1, y1], radius=r, fill=bg)
    draw.text((x + pad, y + pad // 2), label, font=f, fill=fg)
    return x1 - x


def top_bar(draw: ImageDraw.Draw, label: str, color: tuple) -> None:
    draw.rectangle([0, 0, W, 6], fill=color)
    draw.rectangle([0, 6, W, 76], fill=PANEL)
    draw.text((44, 22), label, font=fnt(32, bold=True), fill=color)


# ── frame creators ────────────────────────────────────────────────────────────

def frame_title() -> np.ndarray:
    img, draw = new_frame()
    draw.rectangle([0, H // 2 - 3, W, H // 2 + 3], fill=ACCENT)
    cx(draw, "COGTRACE", H // 2 - 230, fnt(150, bold=True), WHITE)
    cx(draw, "Abstraction-Grounded Citation Verification", H // 2 - 48, fnt(44), DIM)
    cx(draw, "Hackathon Demo · 2026", H // 2 + 44, fnt(34), DIM)
    cx(draw, "Built on AGAH — the harness IS the contribution", H // 2 + 140, fnt(30), ACCENT)
    return np.array(img)


def frame_hook() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "THE PROBLEM", RED)
    cx(draw, "2,500,000", 110, fnt(190, bold=True), RED)
    cx(draw, "biomedical papers audited  ·  Lancet, May 2026", 345, fnt(48), WHITE)
    cx(draw, "Fabricated and mismatched citations found at scale", 430, fnt(42), ORANGE)
    cx(draw, "Not just plagiarism — citations to papers that don't exist", 520, fnt(36), DIM)
    draw.rectangle([W // 5, 630, 4 * W // 5, 632], fill=PANEL)
    cx(draw, "Not a model problem.", 670, fnt(52, bold=True), WHITE)
    cx(draw, "A harness problem.", 745, fnt(52, bold=True), ACCENT)
    return np.array(img)


def frame_problem() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "THE BROKEN PATTERN", ORANGE)
    cx(draw, "Most multi-agent systems are organised like org charts", 96, fnt(44), WHITE)

    roles   = ["Researcher", "Reviewer", "Critic"]
    clrs    = [ACCENT, PURPLE, ORANGE]
    bw, bh  = 310, 110
    gap     = 90
    total_w = len(roles) * bw + (len(roles) - 1) * gap
    sx      = (W - total_w) // 2
    y0      = 235

    for i, (label, clr) in enumerate(zip(roles, clrs)):
        x0 = sx + i * (bw + gap)
        draw.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=10, fill=PANEL,
                                outline=clr, width=3)
        tw, _ = text_size(draw, label, fnt(40, bold=True))
        draw.text((x0 + (bw - tw) // 2, y0 + 30), label, font=fnt(40, bold=True), fill=clr)
        if i < len(roles) - 1:
            ax = x0 + bw + gap // 2
            ay = y0 + bh // 2
            draw.text((ax - 12, ay - 20), "→", font=fnt(44), fill=DIM)
        # big red X
        draw.line([x0 + 10, y0 + 10, x0 + bw - 10, y0 + bh - 10], fill=RED, width=5)
        draw.line([x0 + bw - 10, y0 + 10, x0 + 10, y0 + bh - 10], fill=RED, width=5)

    cx(draw, "Imports human cognitive limits into systems that don't need them", 420, fnt(38), WHITE)
    cx(draw, "Bundles retrieval · judgment · policy-check · anomaly-detection into one «role»", 488, fnt(32), DIM)

    draw.rectangle([W // 5, 590, 4 * W // 5, 592], fill=PANEL)
    cx(draw, "AGAH replaces role labels with representational functions", 624, fnt(42, bold=True), ACCENT)
    cx(draw, "What information can this agent see?   What constraints does it enforce?   At which layer?",
       698, fnt(30), DIM)
    return np.array(img)


def frame_layers() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "THE SOLUTION — RASMUSSEN'S ABSTRACTION HIERARCHY", GREEN)

    y0    = 90
    row_h = 92
    cols  = [60, 110, 450, 920, 1380]
    hdrs  = ["", "Layer", "AH Level", "AGAH Component", "Role"]
    for i, h in enumerate(hdrs):
        draw.text((cols[i], y0), h, font=fnt(28, bold=True), fill=DIM)

    roles_desc = {
        5: "Mission objectives, ethical bounds, success criteria",
        4: "Invariants, conservation constraints, cross-layer safety",
        3: "Standard operational patterns, fallback chains",
        2: "Tool specs, API contracts, model capabilities",
        1: "HTTP calls, file I/O, LLM invocations",
    }

    for idx, layer in enumerate(range(5, 0, -1)):
        y   = y0 + 48 + idx * row_h
        clr = LAYER_C[layer]
        draw.rectangle([60, y, W - 60, y + row_h - 8], fill=PANEL)
        draw.rectangle([60, y, 70, y + row_h - 8], fill=clr)
        draw.text((cols[1], y + 22), f"L{layer}", font=fnt(38, bold=True), fill=clr)
        draw.text((cols[2], y + 22), LAYER_N[layer], font=fnt(32), fill=WHITE)
        draw.text((cols[3], y + 22), LAYER_A[layer], font=fnt(32, bold=True), fill=clr)
        draw.text((cols[4], y + 22), roles_desc[layer], font=fnt(26), fill=DIM)

    y_note = y0 + 48 + 5 * row_h + 16
    cx(draw, "LangGraph is deliberately at L1.  It is the execution substrate, not the architecture.",
       y_note, fnt(34), ACCENT)
    return np.array(img)


def frame_mecc() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "THE MECC — MEANS-ENDS CONSISTENCY CHECKER", LAYER_C[4])

    cx(draw, "The most important primitive in AGAH", 88, fnt(48, bold=True), WHITE)

    formula = "MECC(A, L) = permitted(A, L)  ∧  (∀k ≥ L: ¬violates(A, Cₖ))  ∧  (∃g ∈ G: advances(A, g))"
    fw, fh  = text_size(draw, formula, fnt(30, mono=True))
    fx0     = (W - fw) // 2 - 30
    fy0     = 188
    draw.rounded_rectangle([fx0 - 20, fy0 - 16, fx0 + fw + 50, fy0 + fh + 24],
                            radius=10, fill=PANEL, outline=LAYER_C[4], width=2)
    draw.text((fx0, fy0), formula, font=fnt(30, mono=True), fill=LAYER_C[4])

    bullets = [
        (ACCENT,  "Cross-layer admissibility gate",
         "Checks constraints at ALL layers above the action's origin — not just its own layer"),
        (GREEN,   "Not a policy list",
         "A policy evaluator checks rules at one layer.  MECC enforces the full hierarchy at runtime."),
        (ORANGE,  "Invoked before every action",
         "Before any API call  ·  Before any verdict  ·  Before any escalation  ·  After any proposal"),
    ]

    y = fy0 + fh + 70
    for clr, title, desc in bullets:
        draw.rectangle([120, y, 128, y + 76], fill=clr)
        draw.text((148, y + 4),  title, font=fnt(38, bold=True), fill=clr)
        draw.text((148, y + 46), desc,  font=fnt(28),            fill=DIM)
        y += 116

    return np.array(img)


def frame_citations_input() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "LIVE DEMO — FOUR CITATIONS", ACCENT)
    cx(draw, "One real · one fabricated · one mismatched · one missing",
       92, fnt(42), WHITE)

    cits = [
        ("CIT-1", "Yao et al. 2023 · ReAct: Synergizing Reasoning and Acting in Language Models",
         "DOI: 10.48550/arXiv.2210.03629",
         "Real paper, correct DOI, correct title and year", GREEN, "VALID"),
        ("CIT-2", "Smith et al. 2024 · A Revolutionary Biomedical Agent Pipeline · Nature",
         "DOI: 10.1038/s41586-2024-99999-x",
         "Plausible-looking DOI — this paper does not exist", RED, "FABRICATED"),
        ("CIT-3", "Yao et al. 2023 · Chain-of-Thought Prompting Elicits Reasoning in LLMs",
         "DOI: 10.48550/arXiv.2210.03629",
         "Real DOI but the title belongs to a completely different paper", ORANGE, "MISMATCHED"),
        ("CIT-4", "Anonymous 2024 · Undocumented Findings in Biomedical Research",
         "No DOI or arXiv ID",
         "Cannot begin verification without an identifier", GRAY, "UNRESOLVABLE"),
    ]

    row_h = 155
    y0    = 176
    for i, (cid, title, doi, note, clr, badge) in enumerate(cits):
        y = y0 + i * row_h
        draw.rounded_rectangle([60, y, W - 60, y + row_h - 10],
                                radius=8, fill=PANEL, outline=(30, 34, 54), width=1)
        draw.rectangle([60, y, 70, y + row_h - 10], fill=clr)
        draw.text(( 90, y + 14), cid,   font=fnt(28, bold=True), fill=DIM)
        draw.text(( 90, y + 44), title, font=fnt(32, bold=True), fill=WHITE)
        draw.text(( 90, y + 86), doi,   font=fnt(26, mono=True), fill=DIM)
        draw.text(( 90, y + 116), note, font=fnt(26),            fill=DIM)
        pill(draw, W - 310, y + 50, badge, bg=clr)

    return np.array(img)


def frame_fabricated() -> np.ndarray:
    img, draw = new_frame((76, 6, 6))
    draw.rectangle([0, 0, W, 74], fill=(105, 10, 10))
    draw.text((44, 22),
              "MECC  ·  Constraint C001  ·  Layer 4 — Abstract Function",
              font=fnt(32), fill=(210, 90, 90))

    badge    = "⚠  FABRICATED"
    f_big    = fnt(148, bold=True)
    bw, _    = text_size(draw, badge, f_big)
    draw.text(((W - bw) // 2, 110), badge, font=f_big, fill=(255, 55, 55))

    cx(draw, "DOI: 10.1038/s41586-2024-99999-x", 380, fnt(48, mono=True), (215, 145, 145))
    cx(draw, "Crossref returned HTTP 404.  This paper does not exist.", 466, fnt(42), (228, 175, 175))

    draw.rounded_rectangle([200, 576, W - 200, 726], radius=12, fill=(105, 10, 10))
    draw.text((240, 596),
              "C001  ·  DOI must resolve to a real Crossref record",
              font=fnt(36, bold=True), fill=(255, 110, 110))
    draw.text((240, 650),
              "Severity: HARD BLOCK  ·  No LLM call  ·  No fallback  ·  Verdict emitted immediately",
              font=fnt(30), fill=(195, 115, 115))

    cx(draw, "The harness caught it.  Not the model.", 796, fnt(50, bold=True), (255, 80, 80))
    return np.array(img)


def frame_results_table() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "PIPELINE RESULTS", GREEN)
    cx(draw, "Four citations · 1 valid · 2 flagged · 1 unresolvable", 88, fnt(38), DIM)

    cols    = [60, 270, 600, 880, 1120]
    y0      = 155
    headers = ["Citation", "Status", "Constraint", "Similarity", "Why"]
    for i, h in enumerate(headers):
        draw.text((cols[i], y0), h, font=fnt(28, bold=True), fill=DIM)
    draw.rectangle([60, y0 + 36, W - 60, y0 + 38], fill=(38, 42, 62))

    rows = [
        ("CIT-1", "VALID",        "—",    "0.97",
         "DOI resolved · title and year match",                      GREEN),
        ("CIT-2", "FABRICATED",   "C001", "n/a",
         "DOI 404 on Crossref — paper does not exist",               RED),
        ("CIT-3", "MISMATCHED",   "C002", "0.11",
         "Title similarity below 0.85 · assessor confirmed mismatch", ORANGE),
        ("CIT-4", "UNRESOLVABLE", "C008", "n/a",
         "No DOI or arXiv ID in citation text",                      GRAY),
    ]

    row_h = 112
    for i, (cid, status, cstr, sim, why, clr) in enumerate(rows):
        y = y0 + 48 + i * row_h
        if i % 2 == 0:
            draw.rectangle([60, y, W - 60, y + row_h - 4], fill=PANEL)
        draw.rectangle([60, y, 70, y + row_h - 4], fill=clr)
        draw.text((cols[0] + 14, y + 32), cid,  font=fnt(32, bold=True), fill=WHITE)
        pill(draw, cols[1], y + 26, status, bg=clr)
        draw.text((cols[2], y + 32), cstr, font=fnt(32, mono=True), fill=clr)
        draw.text((cols[3], y + 32), sim,  font=fnt(32),            fill=WHITE)
        wrap_text(draw, why, cols[4], y + 18, W - cols[4] - 80, fnt(28), DIM)

    y_s = y0 + 48 + 4 * row_h + 18
    draw.rounded_rectangle([60, y_s, W - 60, y_s + 68], radius=8, fill=PANEL)
    stats = [
        ("4 citations",       DIM),
        ("1 ✓ valid",         GREEN),
        ("2 ✗ flagged",       RED),
        ("1 ⚠ unresolvable",  GRAY),
        ("LLM calls: 1",      PURPLE),
        ("Est. cost: $0.0003", DIM),
    ]
    sx = 100
    for label, clr in stats:
        draw.text((sx, y_s + 18), label, font=fnt(30), fill=clr)
        tw, _ = text_size(draw, label, fnt(30))
        sx += tw + 60

    return np.array(img)


def frame_ah_trace() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "ABSTRACTION HIERARCHY TRACE", PURPLE)
    cx(draw, "The architecture diagram made live — every event, every layer, every constraint",
       88, fnt(38), WHITE)

    band_h = 128
    y_base = 155
    for layer in range(5, 0, -1):
        y   = y_base + (5 - layer) * band_h
        clr = LAYER_C[layer]
        draw.rectangle([60, y, W - 60, y + band_h - 4], fill=(16, 18, 30))
        draw.rectangle([60, y, 70,     y + band_h - 4], fill=clr)
        label = f"L{layer}  {LAYER_N[layer]}"
        draw.text((85, y + band_h // 2 - 14), label, font=fnt(24, bold=True), fill=clr)

    events = [
        (0.18, 3, ACCENT,        8,  "parse CIT-1"),
        (0.23, 3, ACCENT,        8,  "parse CIT-2"),
        (0.28, 3, ACCENT,        8,  "parse CIT-3"),
        (0.33, 3, GRAY,          8,  "parse CIT-4 → C008 block"),
        (0.40, 2, ACCENT,        8,  "retrieve CIT-1"),
        (0.45, 2, RED,           8,  "retrieve CIT-2 → 404"),
        (0.50, 2, ACCENT,        8,  "retrieve CIT-3"),
        (0.58, 4, RED,          16,  "MECC C001 → CIT-2 FABRICATED"),
        (0.64, 4, ORANGE,       16,  "MECC C002 → CIT-3 sim 0.11"),
        (0.70, 4, PURPLE,       16,  "Assessor → MISMATCHED"),
        (0.76, 4, GREEN,        12,  "MECC CIT-1 all pass"),
        (0.83, 5, GREEN,        16,  "L5 C007 pass → proceed"),
        (0.88, 5, WHITE,        14,  "verdict emitted"),
    ]

    for xf, layer, clr, r, lbl in events:
        x = int(60 + xf * (W - 120))
        y = y_base + (5 - layer) * band_h + band_h // 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=clr)
        draw.text((x + r + 8, y - 12), lbl, font=fnt(20), fill=DIM)

    # escalation arrow L4 → L5
    ex  = int(60 + 0.58 * (W - 120))
    y4  = y_base + (5 - 4) * band_h + band_h // 2
    y5  = y_base + (5 - 5) * band_h + band_h // 2 + 16
    draw.line([ex, y4 - 16, ex, y5 + 10], fill=RED, width=3)
    draw.polygon([(ex - 8, y5 + 10), (ex + 8, y5 + 10), (ex, y5 - 4)], fill=RED)

    legend_y = y_base + 5 * band_h + 12
    legend   = [("● agent event", ACCENT), ("● violation", RED),
                ("● mismatch", ORANGE), ("● assessor (LLM)", PURPLE),
                ("● verdict", GREEN), ("↑ escalation", RED)]
    lx = 80
    for lbl, clr in legend:
        draw.text((lx, legend_y), lbl, font=fnt(24), fill=clr)
        tw, _ = text_size(draw, lbl, fnt(24))
        lx += tw + 50

    return np.array(img)


def frame_weave() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "OBSERVABILITY — W&B WEAVE INTEGRATION", PURPLE)
    cx(draw, "The hierarchy is not just described.  It is traced.", 88, fnt(44, bold=True), WHITE)

    spans = [
        ("scenario_complete",       "L5", "42 ms",  GREEN),
        ("citation_verdict:CIT-1",  "L4", "18 ms",  GREEN),
        ("mecc_evaluation",         "L4", " 2 ms",  GREEN),
        ("citation_verdict:CIT-2",  "L4", "12 ms",  RED),
        ("mecc_evaluation:C001",    "L4", " 1 ms",  RED),
        ("citation_verdict:CIT-3",  "L4", "28 ms",  ORANGE),
        ("assessor_llm_call",       "L4", "620 ms", PURPLE),
        ("api_crossref",            "L2", "310 ms", ACCENT),
        ("api_crossref:fixture",    "L2", "  0 ms", DIM),
    ]

    cols    = [60, 680, 870, 1060]
    y0      = 165
    headers = ["Weave Span", "Layer", "Latency", "Status"]
    for i, h in enumerate(headers):
        draw.text((cols[i], y0), h, font=fnt(28, bold=True), fill=DIM)
    draw.rectangle([60, y0 + 36, W - 60, y0 + 38], fill=(38, 42, 62))

    row_h = 64
    for i, (name, layer, lat, clr) in enumerate(spans):
        y = y0 + 48 + i * row_h
        if i % 2 == 0:
            draw.rectangle([60, y, W - 60, y + row_h - 4], fill=PANEL)
        lnum = int(layer[1])
        draw.text((cols[0], y + 14), name,  font=fnt(28, mono=True), fill=WHITE)
        draw.text((cols[1], y + 14), layer, font=fnt(28, bold=True), fill=LAYER_C[lnum])
        draw.text((cols[2], y + 14), lat,   font=fnt(28, mono=True), fill=DIM)
        badge_label = ("PASS" if clr == GREEN else "FAIL" if clr == RED
                       else "LLM" if clr == PURPLE else "OK")
        pill(draw, cols[3], y + 8, badge_label, bg=clr)

    y_b = y0 + 48 + len(spans) * row_h + 18
    cx(draw, "Filter by  ah_layer_name  ·  constraint_id  ·  verdict  in W&B workspace", y_b,      fnt(30), ACCENT)
    cx(draw, "Human feedback (👍 / 👎) logged back for continuous evaluation",            y_b + 52, fnt(30), DIM)
    return np.array(img)


def frame_close() -> np.ndarray:
    img, draw = new_frame()
    top_bar(draw, "PORTABILITY — SAME HARNESS, DIFFERENT YAML", ACCENT)

    scenarios = [
        ("Citation Integrity",       "Live demo",     GREEN,
         "Biomedical paper citation fabrication and mismatch"),
        ("Destructive Action Safety", "Stub included", ORANGE,
         "MECC gates DROP TABLE / DELETE / RESTART before execution"),
        ("Sensor Escalation",         "Stub included", ACCENT,
         "Cross-agent seismic / tsunami inconsistency resolution"),
    ]

    bh = 162
    y0 = 110
    for i, (name, status, clr, desc) in enumerate(scenarios):
        y = y0 + i * (bh + 18)
        draw.rounded_rectangle([60, y, W - 60, y + bh], radius=10,
                                fill=PANEL, outline=(30, 34, 54), width=1)
        draw.rectangle([60, y, 70, y + bh], fill=clr)
        draw.text(( 94, y + 20),  name,   font=fnt(42, bold=True), fill=WHITE)
        pill(draw, 94, y + 74, status, bg=clr)
        draw.text(( 94, y + 120), desc,   font=fnt(28),            fill=DIM)

    y_tag = y0 + 3 * (bh + 18) + 20
    cx(draw, "Same 5-layer harness.   Different policies.yaml.   That is the point.",
       y_tag, fnt(46, bold=True), ACCENT)
    draw.rectangle([0, y_tag + 80, W, y_tag + 84], fill=ACCENT)
    cx(draw, "AGAH — where the harness IS the architecture", y_tag + 96, fnt(34), DIM)
    return np.array(img)


# ── narration segments ────────────────────────────────────────────────────────

SEGMENTS: list[dict] = [
    {
        "id":       "title",
        "frame_fn": frame_title,
        "text":     "",      # silent title card
        "duration": 3.5,
    },
    {
        "id":       "hook",
        "frame_fn": frame_hook,
        "text": (
            "A study published in the Lancet in May 2026 audited two and a half million biomedical papers "
            "and found fabricated and mismatched citations at scale. "
            "Not just plagiarism — citations to papers that don't exist. "
            "References where the D-O-I resolves to a completely different study. "
            "This is a trust problem. And it is a hard problem to catch automatically. "
            "Not because the models aren't good enough — "
            "because the harness isn't designed to catch it."
        ),
    },
    {
        "id":       "problem",
        "frame_fn": frame_problem,
        "text": (
            "Most multi-agent systems today are organised like org charts. "
            "You have a Researcher agent. A Reviewer agent. A Critic. "
            "That pattern is intuitive — but it imports human organisational assumptions "
            "into systems that don't have human cognitive limits or role identities. "
            "The agents end up doing overlapping work, passing full context to each other, "
            "and there is no principled way to decide which agent should catch which failure."
        ),
    },
    {
        "id":       "layers",
        "frame_fn": frame_layers,
        "text": (
            "CogTrace is built on a different principle. "
            "Rasmussen's Abstraction Hierarchy — a framework from cognitive engineering — "
            "gives us five distinct levels of representation in any work domain. "
            "Instead of naming agents by job title, we allocate them by representational function: "
            "what information they're allowed to see, what constraints they enforce, "
            "and which layer of the domain they inhabit. "
            "At the top, Layer 5: the Goal Governor — mission objectives and ethical bounds. "
            "Layer 4: the Constraint Reasoner — this is where the MECC lives. "
            "Layer 3: Workflow Orchestrator. Layer 2: Capability Router. "
            "Layer 1: LangGraph — HTTP calls, LLM invocations, and nothing else."
        ),
    },
    {
        "id":       "mecc",
        "frame_fn": frame_mecc,
        "text": (
            "The key primitive is the MECC — the Means-Ends Consistency Checker. "
            "Before any external API call, before any verdict is emitted, "
            "MECC checks the proposed action against constraints at every layer above it. "
            "It is not a policy list. "
            "A policy evaluator checks rules at one layer. "
            "MECC is a cross-layer admissibility gate. "
            "That is what makes the hierarchy enforced at runtime, not just described."
        ),
    },
    {
        "id":       "citations_input",
        "frame_fn": frame_citations_input,
        "text": (
            "I have four citations loaded. "
            "Citation one: Yao et al., 2023, the ReAct paper — real D-O-I, correct title, correct year. Should be valid. "
            "Citation two: Smith et al., 2024, a paper in Nature with a D-O-I ending in ninety-nine-ninety-nine-x. "
            "This paper does not exist. "
            "Citation three: the same real D-O-I as citation one, but the title has been swapped to a different paper entirely. "
            "Should be mismatched. "
            "Citation four: no D-O-I at all. We cannot even begin verification."
        ),
    },
    {
        "id":       "fabricated",
        "frame_fn": frame_fabricated,
        "text": (
            "There it is. "
            "Citation two — Crossref returns a four-oh-four. "
            "Constraint C-zero-zero-one fires at Layer 4. "
            "Verdict: FABRICATED. "
            "That is not a model judgment call. "
            "That is a hard constraint, enforced by MECC, at the right layer, "
            "before anything else could execute. "
            "The harness caught it. Not the model."
        ),
    },
    {
        "id":       "results",
        "frame_fn": frame_results_table,
        "text": (
            "Looking at all four results. "
            "Citation one is valid — D-O-I resolved, title and year match. "
            "Citation two is fabricated. "
            "Citation three is mismatched — title similarity was zero point one one, "
            "well below the threshold of zero point eight five. "
            "The assessor — the only LLM call in the entire pipeline — "
            "confirmed this was a clear mismatch, not an ambiguous case. "
            "Citation four is unresolvable. No identifier to work with. "
            "Total estimated cost: three tenths of a cent."
        ),
    },
    {
        "id":       "ah_trace",
        "frame_fn": frame_ah_trace,
        "text": (
            "This is the abstraction hierarchy trace — the architecture diagram made live. "
            "Each dot is an event. Each horizontal band is a layer. "
            "Green is valid. Orange is a mismatch. Red is fabricated. "
            "The purple dot is the assessor invocation — the LLM was called here, and only here. "
            "The escalation arrow shows a MECC violation at Layer 4 surfacing to Layer 5. "
            "The Goal Governor checks: do we have enough to proceed? "
            "We do. Citation one is valid. The run completes."
        ),
    },
    {
        "id":       "weave",
        "frame_fn": frame_weave,
        "text": (
            "Every one of these events is a Weave span in Weights and Biases. "
            "Every MECC evaluation. Every layer transition. Every assessor call. "
            "You can filter by layer, by constraint ID, by verdict. "
            "Human feedback — correct or incorrect — feeds back into the workspace. "
            "This is not observability bolted on. It is woven into the harness from day one."
        ),
    },
    {
        "id":       "close",
        "frame_fn": frame_close,
        "text": (
            "The same harness runs three scenarios. "
            "Citation integrity is the live demo. "
            "Destructive action safety — MECC gates DROP TABLE and DELETE commands before execution. "
            "Sensor escalation — cross-agent inconsistency resolution for seismic events. "
            "Different domain. Different YAML constraints. Same five layers. Same MECC gate. "
            "Same harness. Different YAML. That is the point of AGAH. "
            "The abstraction hierarchy is the architecture. Thank you."
        ),
    },
]


# ── TTS generation ────────────────────────────────────────────────────────────

async def generate_audio(segments: list[dict], audio_dir: Path) -> None:
    try:
        import edge_tts
        import edge_tts.communicate as _etcom
    except ImportError:
        print("ERROR: edge-tts not installed.  Run: pip install edge-tts")
        sys.exit(1)

    # Python 3.13 / Windows: inject the native OS certificate store so aiohttp
    # can verify speech.platform.bing.com using the system-trusted CA chain.
    import truststore
    truststore.inject_into_ssl()

    audio_dir.mkdir(exist_ok=True)
    for seg in segments:
        if not seg.get("text"):
            continue
        out = audio_dir / f"{seg['id']}.mp3"
        if out.exists():
            print(f"  [skip] {out.name} already exists")
            continue
        print(f"  [tts]  {seg['id']}...")
        comm = edge_tts.Communicate(seg["text"], VOICE)
        await comm.save(str(out))


# ── video assembly ────────────────────────────────────────────────────────────

def build_video(segments: list[dict], audio_dir: Path, output: Path) -> None:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("ERROR: moviepy not installed.  Run: pip install 'moviepy==1.0.3'")
        sys.exit(1)

    clips = []
    for seg in segments:
        print(f"  [frame] {seg['id']}...")
        frame    = seg["frame_fn"]()
        aud_path = audio_dir / f"{seg['id']}.mp3"

        if aud_path.exists():
            audio    = AudioFileClip(str(aud_path))
            duration = audio.duration + 0.5
        else:
            audio    = None
            duration = float(seg.get("duration", 3.5))

        clip = ImageClip(frame).set_duration(duration)
        if audio is not None:
            clip = clip.set_audio(audio)
        clips.append(clip)

    print("  [concat] assembling clips...")
    final = concatenate_videoclips(clips, method="compose")
    print(f"  [export] writing {output}  (this takes ~30s)...")
    final.write_videofile(
        str(output),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    final.close()


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("CogTrace Demo Video Generator")
    print("=" * 44)

    missing = []
    for pkg in ("edge_tts", "moviepy", "PIL", "numpy"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace("_", "-"))
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run:  pip install edge-tts 'moviepy==1.0.3' pillow numpy")
        sys.exit(1)

    AUDIO_DIR.mkdir(exist_ok=True)

    print("\n[1/3] Generating TTS audio...")
    asyncio.run(generate_audio(SEGMENTS, AUDIO_DIR))

    print("\n[2/3] Building frames and assembling video...")
    build_video(SEGMENTS, AUDIO_DIR, OUTPUT)

    print(f"\n[3/3] Done.")
    print(f"      Output → {OUTPUT}")
    total = len([s for s in SEGMENTS if s.get("text")])
    print(f"      Segments: {len(SEGMENTS)}  ({total} narrated)")


if __name__ == "__main__":
    main()
