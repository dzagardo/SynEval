#!/usr/bin/env python3
"""
Utilities for building dashboard-ready datasets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExperimentSummary:
    key: str
    variant: str
    dp_level: str
    step: str
    epsilon_value: Optional[float]
    metrics: Dict[str, float]
    status: str
    source_paths: Dict[str, str]

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["metrics"] = {k: float(v) for k, v in self.metrics.items()}
        return payload


def persist_summary(summaries: List[ExperimentSummary], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as fh:
        json.dump([summary.to_dict() for summary in summaries], fh, indent=2)
    return destination

