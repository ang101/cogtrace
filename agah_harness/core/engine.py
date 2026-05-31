from __future__ import annotations

from pathlib import Path

from agah_harness.scenarios.citationintegrity.scenario import CitationIntegrityScenario
from agah_harness.scenarios.destructiveaction.scenario import DestructiveActionScenario
from agah_harness.scenarios.sensorescalation.scenario import SeismicEscalationScenario


class HarnessEngine:
    def __init__(self, root: str | Path, scenario_type: str = "citationintegrity"):
        root = Path(root)
        self.root = root
        self.scenario_type = scenario_type
        scenarios_root = root / "agah_harness" / "scenarios"

        if scenario_type == "destructiveaction":
            self.scenario = DestructiveActionScenario(
                scenarios_root / "destructiveaction" / "policies.yaml"
            )
        elif scenario_type == "sensorescalation":
            self.scenario = SeismicEscalationScenario(
                scenarios_root / "sensorescalation" / "policies.yaml"
            )
        else:
            self.scenario = CitationIntegrityScenario(
                scenarios_root / "citationintegrity" / "policies.yaml"
            )

    def run(self, raw_text: str):
        return self.scenario.evaluate(raw_text)
