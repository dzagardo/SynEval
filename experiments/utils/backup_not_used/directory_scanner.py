#!/usr/bin/env python3
"""
Dynamic Experiment Directory Scanner
=====================================
Discovers experiments with flexible directory structures.

Expected hierarchy (flexible):
    data_dir/
        experiment_name/
            epsilon_level/  (optional, e.g., dp_eps1, dp_epsInf)
                dataset_name/
                    step_*/  (optional, e.g., step_0010000)
                        checkpoints/
                            model_*.pt
                        train_data.csv
                        test_data.csv
                        synthetic.csv
                        real.csv

The scanner adapts to various structures and missing levels.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExperimentSpec:
    """Specification for a discovered experiment."""

    experiment_name: str
    epsilon_value: Optional[float]  # None for non-DP
    epsilon_label: str  # "dp_eps1", "dp_epsInf", etc.
    dataset_name: str
    step_number: Optional[int]
    step_label: Optional[str]

    # Paths
    root_path: Path
    checkpoint_dir: Optional[Path]
    train_data: Optional[Path]
    test_data: Optional[Path]
    synthetic_data: Optional[Path]
    real_data: Optional[Path]

    def __str__(self):
        step_str = f"/{self.step_label}" if self.step_label else ""
        return f"{self.experiment_name}/{self.epsilon_label}/{self.dataset_name}{step_str}"


class ExperimentScanner:
    """Scans directory trees to discover experiment configurations."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def parse_epsilon_label(self, label: str) -> tuple:
        """
        Parse epsilon label to extract numeric value.

        Examples:
            "dp_eps1" → (1.0, "dp_eps1")
            "dp_eps10" → (10.0, "dp_eps10")
            "dp_eps1000" → (1000.0, "dp_eps1000")
            "dp_epsInf" → (float('inf'), "dp_epsInf")
            "dp_eps99999" → (99999.0, "dp_eps99999")  # Treat as inf proxy
            "nondp" → (float('inf'), "nondp")

        Returns:
            (epsilon_value, original_label)
        """
        label_lower = label.lower()

        # Check for infinite/non-DP
        if "inf" in label_lower or "nondp" in label_lower:
            return (float("inf"), label)

        # Check for very large epsilon (treat as inf)
        match = re.search(r"eps(\d+\.?\d*)", label_lower)
        if match:
            eps_val = float(match.group(1))
            if eps_val >= 99999:
                return (float("inf"), label)
            return (eps_val, label)

        # Default: treat as non-DP
        return (float("inf"), label)

    def find_data_files(self, directory: Path) -> Dict[str, Optional[Path]]:
        """
        Find data files in a directory.

        Looks for common patterns:
            - train_data.csv, train.csv, training.csv, *train*.csv, *ground_truth*train*.csv
            - test_data.csv, test.csv, testing.csv, *test*.csv, val.csv
            - synthetic_data.csv, synthetic.csv, synth.csv, generated.csv
            - real_data.csv, real.csv, original.csv
        """
        files = {"train": None, "test": None, "synthetic": None, "real": None}

        # Train data patterns (prioritize specific names)
        for pattern in [
            "train_data.csv",
            "train.csv",
            "training.csv",
            "*ground_truth*train*.csv",
            "train_*.csv",
            "*train*.csv",
        ]:
            matches = list(directory.glob(pattern))
            if matches:
                files["train"] = matches[0]
                break

        # Test data patterns
        for pattern in [
            "test_data.csv",
            "test.csv",
            "testing.csv",
            "val.csv",
            "validation.csv",
            "test_*.csv",
            "*test*.csv",
        ]:
            matches = list(directory.glob(pattern))
            if matches:
                files["test"] = matches[0]
                break

        # Synthetic data patterns
        for pattern in [
            "synthetic_data.csv",
            "synthetic.csv",
            "synth.csv",
            "generated.csv",
            "fake.csv",
            "gen.csv",
        ]:
            matches = list(directory.glob(pattern))
            if matches:
                files["synthetic"] = matches[0]
                break

        # Real data patterns
        for pattern in [
            "real_data.csv",
            "real.csv",
            "original.csv",
            "true.csv",
            "ground_truth.csv",
        ]:
            matches = list(directory.glob(pattern))
            if matches:
                files["real"] = matches[0]
                break

        return files

    def is_epsilon_level(self, dirname: str) -> bool:
        """Check if directory name looks like an epsilon level."""
        dirname_lower = dirname.lower()
        return (
            "eps" in dirname_lower
            or "dp" in dirname_lower
            or "nondp" in dirname_lower
            or dirname_lower in ["private", "nonprivate", "public"]
        )

    def is_step_level(self, dirname: str) -> bool:
        """Check if directory name looks like a step/checkpoint level."""
        dirname_lower = dirname.lower()
        return "step" in dirname_lower or "epoch" in dirname_lower

    def extract_step_number(self, step_label: str) -> Optional[int]:
        """Extract numeric step number from label."""
        match = re.search(r"(\d+)", step_label)
        return int(match.group(1)) if match else None

    def scan_directory_level(
        self,
        current_path: Path,
        experiment_name: str,
        epsilon_label: str,
        epsilon_value: float,
        dataset_name: str,
    ) -> List[ExperimentSpec]:
        """
        Scan a directory level for experiments.

        Handles both flat and nested structures.
        """
        specs = []

        # Check for step subdirectories
        subdirs = [d for d in current_path.iterdir() if d.is_dir()]
        step_dirs = [d for d in subdirs if self.is_step_level(d.name)]

        if step_dirs:
            # Has step subdirectories
            for step_dir in sorted(step_dirs):
                checkpoint_dir = step_dir / "checkpoints"
                data_files = self.find_data_files(step_dir)

                # Also check parent directory for data files
                parent_data_files = self.find_data_files(current_path)
                for key in ["train", "test", "real"]:
                    if data_files[key] is None and parent_data_files[key] is not None:
                        data_files[key] = parent_data_files[key]

                # Also check samples subdirectory
                samples_dir = current_path / "samples"
                if samples_dir.exists():
                    samples_data = self.find_data_files(samples_dir)
                    for key in ["train", "test", "real"]:
                        if data_files[key] is None and samples_data[key] is not None:
                            data_files[key] = samples_data[key]

                if checkpoint_dir.exists() or any(data_files.values()):
                    spec = ExperimentSpec(
                        experiment_name=experiment_name,
                        epsilon_value=epsilon_value,
                        epsilon_label=epsilon_label,
                        dataset_name=dataset_name,
                        step_number=self.extract_step_number(step_dir.name),
                        step_label=step_dir.name,
                        root_path=step_dir,
                        checkpoint_dir=checkpoint_dir if checkpoint_dir.exists() else None,
                        train_data=data_files["train"],
                        test_data=data_files["test"],
                        synthetic_data=data_files["synthetic"],
                        real_data=data_files["real"],
                    )
                    specs.append(spec)
                    logger.debug(f"    ✓ Found: {spec}")
        else:
            # No step subdirectories, data is directly here
            checkpoint_dir = current_path / "checkpoints"
            data_files = self.find_data_files(current_path)

            # Also check samples subdirectory
            samples_dir = current_path / "samples"
            if samples_dir.exists():
                samples_data = self.find_data_files(samples_dir)
                for key in ["train", "test", "real"]:
                    if data_files[key] is None and samples_data[key] is not None:
                        data_files[key] = samples_data[key]

            if checkpoint_dir.exists() or any(data_files.values()):
                spec = ExperimentSpec(
                    experiment_name=experiment_name,
                    epsilon_value=epsilon_value,
                    epsilon_label=epsilon_label,
                    dataset_name=dataset_name,
                    step_number=None,
                    step_label=None,
                    root_path=current_path,
                    checkpoint_dir=checkpoint_dir if checkpoint_dir.exists() else None,
                    train_data=data_files["train"],
                    test_data=data_files["test"],
                    synthetic_data=data_files["synthetic"],
                    real_data=data_files["real"],
                )
                specs.append(spec)
                logger.debug(f"    ✓ Found: {spec}")

        return specs

    def scan(
        self,
        experiment_filter: Optional[List[str]] = None,
        epsilon_filter: Optional[List[str]] = None,
        step_filter: Optional[List[str]] = None,
    ) -> List[ExperimentSpec]:
        """
        Scan directory tree and discover all experiments.

        Args:
            experiment_filter: Only include experiments matching these names
            epsilon_filter: Only include epsilon levels matching these labels
            step_filter: Only include steps matching these labels

        Returns:
            List of discovered ExperimentSpec objects
        """
        discovered = []

        logger.info(f"Scanning {self.data_dir}...")

        if not self.data_dir.exists():
            logger.error(f"Data directory does not exist: {self.data_dir}")
            return discovered

        # Level 1: Experiment names
        for exp_dir in sorted(self.data_dir.iterdir()):
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name

            # Apply experiment filter
            if experiment_filter and exp_name not in experiment_filter:
                continue

            logger.info(f"  Scanning experiment: {exp_name}")

            # Check if this level has epsilon subdirs or goes straight to data
            subdirs = [d for d in exp_dir.iterdir() if d.is_dir()]

            # Check if subdirs look like epsilon levels
            epsilon_levels = [d for d in subdirs if self.is_epsilon_level(d.name)]

            if epsilon_levels:
                # Level 2: Epsilon levels
                for eps_dir in sorted(epsilon_levels):
                    eps_label = eps_dir.name

                    # Apply epsilon filter
                    if epsilon_filter and eps_label not in epsilon_filter:
                        continue

                    eps_value, _ = self.parse_epsilon_label(eps_label)

                    # Level 3: Dataset names
                    dataset_dirs = [d for d in eps_dir.iterdir() if d.is_dir()]

                    if dataset_dirs:
                        for dataset_dir in sorted(dataset_dirs):
                            dataset_name = dataset_dir.name

                            # Skip processed directories
                            if dataset_name in ["processed", "checkpoints", "logs"]:
                                continue

                            specs = self.scan_directory_level(
                                dataset_dir, exp_name, eps_label, eps_value, dataset_name
                            )

                            # Apply step filter
                            if step_filter:
                                specs = [
                                    s
                                    for s in specs
                                    if s.step_label is None or s.step_label in step_filter
                                ]

                            discovered.extend(specs)
                    else:
                        # No dataset dirs, epsilon level is the dataset
                        specs = self.scan_directory_level(
                            eps_dir, exp_name, eps_label, eps_value, "default"
                        )

                        # Apply step filter
                        if step_filter:
                            specs = [
                                s
                                for s in specs
                                if s.step_label is None or s.step_label in step_filter
                            ]

                        discovered.extend(specs)
            else:
                # No epsilon levels, data is directly under experiment
                # Treat as non-DP
                specs = self.scan_directory_level(
                    exp_dir, exp_name, "nondp", float("inf"), "default"
                )

                # Apply step filter
                if step_filter:
                    specs = [
                        s
                        for s in specs
                        if s.step_label is None or s.step_label in step_filter
                    ]

                discovered.extend(specs)

        logger.info(f"Total experiments discovered: {len(discovered)}")
        return discovered

    def group_by_experiment(
        self, specs: List[ExperimentSpec]
    ) -> Dict[str, List[ExperimentSpec]]:
        """Group experiment specs by experiment name."""
        groups = {}
        for spec in specs:
            if spec.experiment_name not in groups:
                groups[spec.experiment_name] = []
            groups[spec.experiment_name].append(spec)
        return groups

    def group_by_epsilon(
        self, specs: List[ExperimentSpec]
    ) -> Dict[str, List[ExperimentSpec]]:
        """Group experiment specs by epsilon level."""
        groups = {}
        for spec in specs:
            if spec.epsilon_label not in groups:
                groups[spec.epsilon_label] = []
            groups[spec.epsilon_label].append(spec)
        return groups

    def group_by_step(
        self, specs: List[ExperimentSpec]
    ) -> Dict[str, List[ExperimentSpec]]:
        """Group experiment specs by step label."""
        groups = {}
        for spec in specs:
            step_key = spec.step_label if spec.step_label else "no_step"
            if step_key not in groups:
                groups[step_key] = []
            groups[step_key].append(spec)
        return groups
