from __future__ import annotations

from agah_harness.core.state import AgentResult


class BaseAgent:
    name = "base"
    layer = 0

    def result(self, summary: str, confidence: float, proposedaction: str, **metadata) -> AgentResult:
        return AgentResult(
            agentname=self.name,
            layer=self.layer,
            summary=summary,
            confidence=confidence,
            proposedaction=proposedaction,
            metadata=metadata,
        )
