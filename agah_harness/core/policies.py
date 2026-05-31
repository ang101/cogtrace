from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ConstraintPolicy:
    policy_id: str
    layer: int
    rule: str
    on_violation: str
    enabled: bool = True
    threshold: float | None = None


class PolicyRegistry:
    def __init__(self, policies: list[ConstraintPolicy]):
        self.policies = {p.policy_id: p for p in policies}

    @classmethod
    def load_yaml(cls, path: str | Path) -> "PolicyRegistry":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        policies = [ConstraintPolicy(**row) for row in data.get("policies", [])]
        return cls(policies)

    def get(self, policy_id: str) -> ConstraintPolicy:
        return self.policies[policy_id]

    def all(self) -> list[ConstraintPolicy]:
        return list(self.policies.values())
