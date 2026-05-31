from __future__ import annotations

from datetime import datetime, timezone

from agah_harness.core.state import TraceEvent


class TraceEmitter:
    """Emits TraceEvent objects into HarnessState for the Streamlit layer timeline.

    Weave tracing is handled by @weave.op decorators on MECC.evaluate,
    AssessorAgent.assess, and CitationIntegrityScenario.evaluate — not here.
    """

    def emit(
        self,
        state,
        event_type: str,
        source: str,
        target: str,
        layer: int,
        status: str,
        message: str,
        **metadata,
    ) -> TraceEvent:
        event = TraceEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            source=source,
            target=target,
            layer=layer,
            status=status,
            message=message,
            meccfired=metadata.get("meccfired", False),
            violationflag=metadata.get("violationflag", False),
            metadata=metadata,
        )
        state.traceevents.append(event)
        return event
