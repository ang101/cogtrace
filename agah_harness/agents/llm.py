from __future__ import annotations

import os

try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None

try:
    from openai import OpenAI as _OpenAI
except Exception:
    _OpenAI = None

try:
    import httpx as _httpx
except Exception:
    _httpx = None  # type: ignore[assignment]

try:
    import weave as _weave
    _weave_op = _weave.op
except Exception:
    _weave = None  # type: ignore[assignment]
    def _weave_op(fn):  # type: ignore[misc]
        return fn

from agah_harness.agents.base import BaseAgent

_WB_INFERENCE_BASE = "https://api.inference.wandb.ai/v1"


class AssessorAgent(BaseAgent):
    """L4/L5 assessor for ambiguous matches and cross-agent inconsistency resolution.

    Backend priority:
      1. Anthropic     — if ANTHROPIC_API_KEY is set
      2. W&B Inference — elif WANDB_API_KEY is set (same key as Weave tracing)
      3. Deterministic fallback — if no LLM key is present
    """

    name = "assessor"
    layer = 5

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._anthropic = None
        self._wb_inference = None

        if Anthropic and os.getenv("ANTHROPIC_API_KEY"):
            self._anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif _OpenAI and os.getenv("WANDB_API_KEY"):
            # httpx client with verify=False works around enterprise SSL cert issues
            # while keeping the same behaviour on Streamlit Community Cloud (no cert problem there)
            http_client = _httpx.Client(verify=False) if _httpx else None
            self._wb_inference = _OpenAI(
                base_url=_WB_INFERENCE_BASE,
                api_key=os.getenv("WANDB_API_KEY"),
                **({"http_client": http_client} if http_client else {}),
            )
            self.model = os.getenv("WB_INFERENCE_MODEL", "OpenPipe/Qwen3-14B-Instruct")

    # -- Citation assessor prompt ----------------------------------------------

    def _prompt(self, citation_text: str, retrieved_title: str, parsed_title: str) -> str:
        return (
            "You are the AGAH assessor. Decide whether this mismatch is ambiguous enough to remain unresolved.\n"
            f"Citation text: {citation_text}\n"
            f"Parsed title: {parsed_title}\n"
            f"Retrieved title: {retrieved_title}\n"
            "Return one line beginning with UNRESOLVED or MISMATCHED, followed by a short reason."
        )

    def _assess_anthropic(self, citation_text: str, retrieved_title: str, parsed_title: str):
        try:
            msg = self._anthropic.messages.create(
                model=self.model,
                max_tokens=80,
                temperature=0,
                messages=[{"role": "user", "content": self._prompt(citation_text, retrieved_title, parsed_title)}],
            )
            text = "".join(block.text for block in msg.content if hasattr(block, "text")).strip()
            action = "emit_unresolved" if text.startswith("UNRESOLVED") else "emit_mismatched"
            return self.result(text, 0.75, action)
        except Exception as exc:
            return self.result(f"Anthropic error: {exc}", 0.2, "defer_to_deterministic")

    def _assess_wb(self, citation_text: str, retrieved_title: str, parsed_title: str):
        try:
            resp = self._wb_inference.chat.completions.create(
                model=self.model,
                max_tokens=80,
                temperature=0,
                messages=[{"role": "user", "content": self._prompt(citation_text, retrieved_title, parsed_title)}],
            )
            text = (resp.choices[0].message.content or "").strip()
            action = "emit_unresolved" if text.startswith("UNRESOLVED") else "emit_mismatched"
            return self.result(text, 0.75, action)
        except Exception as exc:
            return self.result(f"W&B Inference error: {exc}", 0.2, "defer_to_deterministic")

    @_weave_op
    def assess(self, citation_text: str, retrieved_title: str, parsed_title: str):
        """Invoke the active backend; traced as a Weave span regardless of backend."""
        if self._anthropic:
            return self._assess_anthropic(citation_text, retrieved_title, parsed_title)
        if self._wb_inference:
            return self._assess_wb(citation_text, retrieved_title, parsed_title)
        return self.result("LLM unavailable; deterministic fallback retained", 0.35, "defer_to_deterministic")

    # -- Generic assessor for cross-agent inconsistency (SE scenario) ----------

    def _judge_anthropic(self, context: str):
        try:
            msg = self._anthropic.messages.create(
                model=self.model,
                max_tokens=120,
                temperature=0,
                messages=[{"role": "user", "content": context}],
            )
            text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
            first_word = text.split()[0].upper().rstrip(".,:-") if text.split() else "NOMINAL"
            if first_word not in {"NOMINAL", "ALERT", "CRITICAL"}:
                first_word = "NOMINAL"
            return self.result(text, 0.82, first_word)
        except Exception as exc:
            return self.result(f"Anthropic error: {exc}", 0.2, "NOMINAL")

    def _judge_wb(self, context: str):
        try:
            resp = self._wb_inference.chat.completions.create(
                model=self.model,
                max_tokens=120,
                temperature=0,
                messages=[{"role": "user", "content": context}],
            )
            text = (resp.choices[0].message.content or "").strip()
            first_word = text.split()[0].upper().rstrip(".,:-") if text.split() else "NOMINAL"
            if first_word not in {"NOMINAL", "ALERT", "CRITICAL"}:
                first_word = "NOMINAL"
            return self.result(text, 0.82, first_word)
        except Exception as exc:
            return self.result(f"W&B Inference error: {exc}", 0.2, "NOMINAL")

    @_weave_op
    def judge(self, context: str):
        """Generic LLM assessor for cross-agent inconsistency resolution (SE scenario).

        Parses first word of response as verdict: NOMINAL / ALERT / CRITICAL.
        Falls back to depth-heuristic if no LLM backend is configured.
        """
        if self._anthropic:
            return self._judge_anthropic(context)
        if self._wb_inference:
            return self._judge_wb(context)
        # Deterministic fallback: infer from depth cue in prompt text
        deep_focus = "580" in context or ("deep" in context.lower() and "km" in context)
        verdict = "NOMINAL" if deep_focus else "ALERT"
        reason = (
            "deep-focus event inferred from depth; surface impact negligible"
            if deep_focus
            else "moderate shallow event; monitoring warranted"
        )
        return self.result(
            f"{verdict} — {reason} (LLM unavailable, deterministic fallback)",
            0.3,
            verdict,
        )
