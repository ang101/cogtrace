from __future__ import annotations

from collections import Counter

from agah_harness.core.state import ConsensusStatus


def consensus_status(values: list[str]) -> ConsensusStatus:
    if not values:
        return ConsensusStatus.PENDING
    counts = Counter(values)
    return ConsensusStatus.AGREED if len(counts) == 1 else ConsensusStatus.DISSENT
