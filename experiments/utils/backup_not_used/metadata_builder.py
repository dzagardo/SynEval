#!/usr/bin/env python3
"""
Metadata construction utilities for SynEval experiments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

DEFAULT_COLUMN_SCHEMA = [
    ("Open", "numerical"),
    ("High", "numerical"),
    ("Low", "numerical"),
    ("Close", "numerical"),
    ("Adj_Close", "numerical"),
    ("Volume", "numerical"),
]


@dataclass
class MetadataConfig:
    dataset_name: str
    description: str
    columns: Sequence[tuple[str, str]] = tuple(DEFAULT_COLUMN_SCHEMA)
    sequence_length: Optional[int] = 24
    sequence_groupby: Optional[str] = None
    utility_task_type: str = "regression"
    utility_inputs: Sequence[str] = ("Open", "High", "Low", "Volume", "Adj_Close")
    utility_outputs: Sequence[str] = ("Close",)

    def to_dict(self) -> Dict:
        column_map: Dict[str, Dict] = {}
        for column, sdtype in self.columns:
            column_map[column] = {
                "sdtype": sdtype,
                "pii": False,
            }

        metadata: Dict = {
            "dataset_name": self.dataset_name,
            "description": self.description,
            "columns": column_map,
        }

        if self.sequence_length:
            metadata["sequence"] = {
                "length": self.sequence_length,
                "groupby": self.sequence_groupby,
            }

        metadata["utility"] = {
            "task_type": self.utility_task_type,
            "input_columns": list(self.utility_inputs),
            "output_columns": list(self.utility_outputs),
        }

        return metadata


def write_metadata(metadata: MetadataConfig, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, indent=2)
    return destination


def infer_basic_statistics(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """
    Compute lightweight summary statistics for logging/reporting.
    """
    df = pd.read_csv(csv_path)
    summary: Dict[str, Dict[str, float]] = {}
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            summary[column] = {
                "min": float(df[column].min()),
                "max": float(df[column].max()),
                "mean": float(df[column].mean()),
                "std": float(df[column].std()),
            }
    return summary

