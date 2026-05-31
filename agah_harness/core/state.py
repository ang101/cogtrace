from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FailureType(str, Enum):
    NOEVIDENCE = "noevidence"
    TIMEOUT = "timeout"
    CONSENSUSFAILURE = "consensusfailure"
    CONSTRAINTVIOLATION = "constraintviolation"
    ESCALATIONREQUIRED = "escalationrequired"
    EVIDENCECONFLICT = "evidenceconflict"


class ConsensusStatus(str, Enum):
    PENDING = "pending"
    AGREED = "agreed"
    DISSENT = "dissent"


class VerdictStatus(str, Enum):
    VALID = "VALID"
    FABRICATED = "FABRICATED"
    MISMATCHED = "MISMATCHED"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class EvidenceItem:
    source: str
    payload: dict[str, Any]
    citation_id: str | None = None


@dataclass
class FailureRecord:
    failuretype: FailureType
    originatinglayer: int
    message: str
    timestamp: datetime = field(default_factory=utc_now)
    resolution: str | None = None


@dataclass
class TraceEvent:
    timestamp: datetime
    event_type: str
    source: str
    target: str
    layer: int
    status: str
    message: str
    meccfired: bool = False
    violationflag: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MECCResult:
    action: str
    layer: int
    passed: bool
    violatedconstraints: list[str] = field(default_factory=list)
    escalationtarget: int | None = None
    rationale: str = ""


@dataclass
class AgentResult:
    agentname: str
    layer: int
    summary: str
    confidence: float
    proposedaction: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationInput:
    citation_id: str
    raw_text: str
    parsed: dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationVerdict:
    citation_id: str
    status: VerdictStatus
    matched_constraints: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


@dataclass
class HarnessState:
    goal: str
    scenariotype: str
    currentlayer: int = 1
    evidenceitems: list[EvidenceItem] = field(default_factory=list)
    agentoutputs: list[AgentResult] = field(default_factory=list)
    meccresults: list[MECCResult] = field(default_factory=list)
    consensusstatus: ConsensusStatus = ConsensusStatus.PENDING
    escalationtarget: str | None = None
    finaldecision: dict[str, Any] | None = None
    traceevents: list[TraceEvent] = field(default_factory=list)
    failurerecords: list[FailureRecord] = field(default_factory=list)
    citations: list[CitationInput] = field(default_factory=list)
    verdicts: list[CitationVerdict] = field(default_factory=list)
    started_at: datetime = field(default_factory=utc_now)
