#!/usr/bin/env python3
"""
Data preparation helpers for SynEval orchestration.

These routines standardize the stock time-series CSV exports by applying
consistent column names, sorting, and basic sanity checks before they are
passed into the SynEval pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd

DEFAULT_COLUMN_NAMES: Sequence[str] = (
    "Open",
    "High",
    "Low",
    "Close",
    "Adj_Close",
    "Volume",
)


@dataclass(frozen=True)
class StandardizationSummary:
    """Lightweight report describing the outcome of a standardization pass."""

    source: Path
    destination: Path
    num_rows: int
    num_columns: int
    columns: List[str]


def standardize_csv(
    source: Path,
    destination: Path,
    column_names: Iterable[str] = DEFAULT_COLUMN_NAMES,
    dropna: bool = True,
) -> StandardizationSummary:
    """
    Read a CSV file, apply canonical column names, and write the result.

    Args:
        source: Path to the raw CSV file.
        destination: Path where the cleaned CSV should be stored.
        column_names: Desired column labels in order.
        dropna: Whether to drop rows containing NaN/inf after coercion.

    Returns:
        StandardizationSummary capturing the transformation footprint.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source)

    if len(df.columns) != len(tuple(column_names)):
        raise ValueError(
            f"Source {source} has {len(df.columns)} columns, expected {len(tuple(column_names))}"
        )

    df = df.copy()
    df.columns = list(column_names)

    # Attempt numeric coercion; non-numeric columns are left as-is.
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if dropna:
        df = df.dropna().reset_index(drop=True)

    df.to_csv(destination, index=False)

    return StandardizationSummary(
        source=source,
        destination=destination,
        num_rows=len(df),
        num_columns=len(df.columns),
        columns=df.columns.tolist(),
    )

