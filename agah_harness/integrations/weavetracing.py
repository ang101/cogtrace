from __future__ import annotations

from agah_harness.core.trace import TraceEmitter


def build_trace_emitter(project_name: str = "agah-hackathon") -> TraceEmitter:
    return TraceEmitter(project_name=project_name)
