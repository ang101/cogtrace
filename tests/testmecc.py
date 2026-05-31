from pathlib import Path

from agah_harness.core.mecc import MECC
from agah_harness.core.policies import PolicyRegistry


def test_mecc_flags_unresolved_doi():
    registry = PolicyRegistry.load_yaml(
        Path(__file__).resolve().parents[1]
        / "agah_harness"
        / "scenarios"
        / "citationintegrity"
        / "policies.yaml"
    )
    mecc = MECC(registry)
    result = mecc.evaluate("emit_verdict", 4, {"retrieved": {"resolved": False}, "verifiable_count": 1})
    assert result.passed is False
    assert "C001" in result.violatedconstraints
