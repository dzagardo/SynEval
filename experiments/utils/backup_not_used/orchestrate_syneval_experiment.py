#!/usr/bin/env python3
"""
SynEval orchestration pipeline for Diffusion_TS_DP time-series experiments.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from string import Template
from textwrap import dedent

from experiments.utils.data_prep import (
    DEFAULT_COLUMN_NAMES,
    StandardizationSummary,
    standardize_csv,
)
from experiments.utils.dashboard_data import ExperimentSummary, persist_summary
from experiments.utils.html_templates import (
    chart_block,
    render_dashboard_page,
    render_experiment_report,
    script_for_chart,
)
from experiments.utils.metadata_builder import MetadataConfig, write_metadata

LOGGER = logging.getLogger("orchestrator")

DEFAULT_STEPS: Sequence[str] = ("step_0010000", "step_0020000")
DEFAULT_DIMENSIONS: Sequence[str] = ("fidelity", "utility", "diversity", "privacy")
DEFAULT_PRIVACY_METRICS: Sequence[str] = (
    "exact_matches",
    "membership_inference",
    "tabular_privacy",
)
UTILITY_INPUT_COLUMNS: Sequence[str] = ("Open", "High", "Low", "Volume", "Adj_Close")
UTILITY_OUTPUT_COLUMNS: Sequence[str] = ("Close",)


def parse_epsilon(dp_level: str) -> Optional[float]:
    match = re.search(r"dp_eps([0-9_]+)", dp_level)
    if not match:
        return None
    token = match.group(1).replace("_", "")
    try:
        return float(token)
    except ValueError:
        return None


def safe_get(data: Dict, *keys, default: Optional[float] = None):
    cursor = data
    for key in keys:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
        if cursor is None:
            return default
    return cursor


@dataclass
class Experiment:
    key: str
    variant: str
    dp_level: str
    dataset: str
    step: str
    synthetic_raw: Path
    real_raw: Path
    synthetic_processed: Path
    real_processed: Path
    metadata_path: Path
    results_dir: Path
    stdout_log: Path
    stderr_log: Path
    epsilon: Optional[float] = None
    status: str = "pending"
    error: Optional[str] = None
    standardization: Dict[str, StandardizationSummary] = field(default_factory=dict)

    def to_summary(self, metrics: Dict[str, float]) -> ExperimentSummary:
        return ExperimentSummary(
            key=self.key,
            variant=self.variant,
            dp_level=self.dp_level,
            step=self.step,
            epsilon_value=self.epsilon,
            metrics=metrics,
            status=self.status,
            source_paths={
                "synthetic": str(self.synthetic_processed),
                "real": str(self.real_processed),
                "metadata": str(self.metadata_path),
                "results": str(self.results_dir / "results.json"),
            },
        )


class SynEvalOrchestrator:
    def __init__(
        self,
        source_dir: Path,
        working_dir: Path,
        dimensions: Sequence[str] = DEFAULT_DIMENSIONS,
        step_filter: Optional[Iterable[str]] = None,
        device: str = "auto",
        privacy_metrics: Sequence[str] = DEFAULT_PRIVACY_METRICS,
        variants_filter: Optional[Iterable[str]] = None,
        dp_levels_filter: Optional[Iterable[str]] = None,
    ):

        self.source_dir = Path(source_dir).expanduser().resolve()
        self.working_dir = Path(working_dir).expanduser().resolve()
        self.dimensions = list(dimensions)
        self.step_filter = set(step_filter) if step_filter else set(DEFAULT_STEPS)
        self.device = device
        self.privacy_metrics = list(privacy_metrics)
        self.variants_filter = set(variants_filter) if variants_filter else None
        self.dp_levels_filter = set(dp_levels_filter) if dp_levels_filter else None

        self.data_dir = self.working_dir / "data"
        self.results_dir = self.working_dir / "results"
        self.dashboards_dir = self.working_dir / "dashboards"
        self.logs_dir = self.working_dir / "logs"
        self.repo_root = Path(__file__).resolve().parent

        for directory in [
            self.data_dir,
            self.results_dir,
            self.dashboards_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        self.run_log_path = self.working_dir / "run_log.txt"
        self.error_log_path = self.working_dir / "error_log.txt"
        self.summary_path = self.working_dir / "experiments_summary.json"

        self.experiments: List[Experiment] = []
        self._real_cache: Dict[Path, Path] = {}
        self._dataframe_cache: Dict[Path, pd.DataFrame] = {}
        self._insights_cache: Dict[str, Dict] = {}

    def copy_data(self):
        LOGGER.info("Copying source data into working directory...")
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        if any(self.data_dir.iterdir()):
            LOGGER.info("Working data directory already populated; skipping copy.")
            return

        shutil.copytree(self.source_dir, self.data_dir, dirs_exist_ok=True)
        LOGGER.info("Data copy complete.")

    def discover_experiments(
        self, limit: Optional[int] = None, include_all_steps: bool = False
    ) -> List[Experiment]:
        LOGGER.info("Discovering experiments in %s", self.data_dir)
        experiments: List[Experiment] = []
        selected_steps = None if include_all_steps else self.step_filter

        synthetic_files = sorted(self.data_dir.rglob("synthetic.csv"))
        for synthetic_file in synthetic_files:
            if "processed" in synthetic_file.parts:
                continue

            step = synthetic_file.parent.name
            if selected_steps and step not in selected_steps:
                continue

            dataset_dir = synthetic_file.parents[2]
            dp_dir = synthetic_file.parents[3]
            variant_dir = synthetic_file.parents[4]

            if self.variants_filter and variant_dir.name not in self.variants_filter:
                continue
            if self.dp_levels_filter and dp_dir.name not in self.dp_levels_filter:
                continue

            samples_dir = dataset_dir / "samples"
            real_candidates = sorted(
                samples_dir.glob("*ground_truth*train*.csv")
            ) + sorted(samples_dir.glob("*train*.csv"))

            if not real_candidates:
                LOGGER.warning(
                    "No real data found alongside %s; skipping", synthetic_file
                )
                continue

            real_raw = real_candidates[0]
            processed_dir = dataset_dir / "processed" / step
            synthetic_processed = processed_dir / "synthetic.csv"
            real_processed = dataset_dir / "processed" / "real_train.csv"

            metadata_path = processed_dir / "metadata.json"
            key = f"{variant_dir.name}/{dp_dir.name}/{dataset_dir.name}/{step}"
            experiment = Experiment(
                key=key,
                variant=variant_dir.name,
                dp_level=dp_dir.name,
                dataset=dataset_dir.name,
                step=step,
                synthetic_raw=synthetic_file,
                real_raw=real_raw,
                synthetic_processed=synthetic_processed,
                real_processed=real_processed,
                metadata_path=metadata_path,
                results_dir=self.results_dir
                / variant_dir.name
                / dp_dir.name
                / step,
                stdout_log=self.logs_dir / f"{key.replace('/', '__')}_stdout.log",
                stderr_log=self.logs_dir / f"{key.replace('/', '__')}_stderr.log",
                epsilon=parse_epsilon(dp_dir.name),
            )
            experiments.append(experiment)

            if limit and len(experiments) >= limit:
                break

        self.experiments = experiments
        LOGGER.info("Discovered %d experiment(s)", len(self.experiments))
        return experiments

    def prepare_experiment(self, exp: Experiment):
        exp.results_dir.mkdir(parents=True, exist_ok=True)
        exp.stdout_log.parent.mkdir(parents=True, exist_ok=True)

        LOGGER.debug("Standardizing synthetic data for %s", exp.key)
        syn_summary = standardize_csv(exp.synthetic_raw, exp.synthetic_processed)
        exp.standardization["synthetic"] = syn_summary

        if exp.real_raw not in self._real_cache:
            LOGGER.debug("Standardizing real data for %s", exp.key)
            real_summary = standardize_csv(exp.real_raw, exp.real_processed)
            exp.standardization["real"] = real_summary
            self._real_cache[exp.real_raw] = exp.real_processed
        else:
            LOGGER.debug("Reusing cached real data for %s", exp.key)

        if not exp.metadata_path.exists():
            LOGGER.debug("Generating metadata for %s", exp.key)
            metadata = MetadataConfig(
                dataset_name=exp.key.replace("/", "__"),
                description=f"Diffusion_TS_DP synthetic evaluation ({exp.dp_level}, {exp.step})",
            )
            write_metadata(metadata, exp.metadata_path)

    def _load_dataframe(self, path: Path) -> pd.DataFrame:
        if path not in self._dataframe_cache:
            self._dataframe_cache[path] = pd.read_csv(path)
        return self._dataframe_cache[path]

    def _compute_privacy_insights(
        self, exp: Experiment, result: Dict
    ) -> Dict[str, Dict]:
        cache_key = f"privacy::{exp.key}"
        if cache_key in self._insights_cache:
            return self._insights_cache[cache_key]

        syn_df = self._load_dataframe(exp.synthetic_processed)
        real_df = self._load_dataframe(exp.real_processed)
        features = syn_df.columns.tolist()

        rounded_real_cache = {
            col: set(real_df[col].round(4).tolist()) for col in features
        }
        match_rates = []
        for col in features:
            coverage = (
                syn_df[col].round(4).isin(rounded_real_cache[col]).mean() * 100.0
            )
            match_rates.append({"feature": col, "coverage": float(coverage)})

        # Nearest neighbour distances
        real_matrix = real_df[features].to_numpy(dtype=float)
        syn_matrix = syn_df[features].to_numpy(dtype=float)

        rng = np.random.default_rng(42)
        if len(real_matrix) > 6000:
            idx = rng.choice(len(real_matrix), size=6000, replace=False)
            real_matrix = real_matrix[idx]
        if len(syn_matrix) > 1500:
            syn_idx = rng.choice(len(syn_matrix), size=1500, replace=False)
            syn_matrix_sample = syn_matrix[syn_idx]
        else:
            syn_matrix_sample = syn_matrix

        scaler = StandardScaler()
        scaler.fit(np.vstack([real_matrix, syn_matrix_sample]))
        real_scaled = scaler.transform(real_matrix)
        syn_scaled = scaler.transform(syn_matrix_sample)

        nbrs = NearestNeighbors(n_neighbors=1, algorithm="auto")
        nbrs.fit(real_scaled)
        distances, _ = nbrs.kneighbors(syn_scaled)
        distances = distances.flatten()
        hist_counts, bin_edges = np.histogram(distances, bins=20)
        bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()

        feature_stats = []
        for col in features:
            real_series = real_df[col]
            syn_series = syn_df[col]
            real_mean = float(real_series.mean())
            syn_mean = float(syn_series.mean())
            real_std = float(real_series.std())
            syn_std = float(syn_series.std())
            mean_diff = float(syn_mean - real_mean)
            std_diff = float(syn_std - real_std)
            feature_stats.append(
                {
                    "feature": col,
                    "real_mean": real_mean,
                    "syn_mean": syn_mean,
                    "mean_diff": mean_diff,
                    "real_std": real_std,
                    "syn_std": syn_std,
                    "std_diff": std_diff,
                    "real_min": float(real_series.min()),
                    "syn_min": float(syn_series.min()),
                    "real_max": float(real_series.max()),
                    "syn_max": float(syn_series.max()),
                }
            )

        max_mean_delta = max((abs(item["mean_diff"]) for item in feature_stats), default=1.0)
        max_std_delta = max((abs(item["std_diff"]) for item in feature_stats), default=1.0)
        for item in feature_stats:
            item["mean_intensity"] = (
                min(1.0, abs(item["mean_diff"]) / max_mean_delta) if max_mean_delta else 0.0
            )
            item["std_intensity"] = (
                min(1.0, abs(item["std_diff"]) / max_std_delta) if max_std_delta else 0.0
            )

        structured = safe_get(result, "privacy", "structured_privacy_metrics") or {}

        insights = {
            "match_rates": match_rates,
            "nearest_neighbor_hist": {
                "bins": [float(round(val, 4)) for val in bin_centers],
                "counts": hist_counts.tolist(),
            },
            "feature_stats": feature_stats,
            "structured_metrics": structured,
        }
        self._insights_cache[cache_key] = insights
        return insights

    def _compute_utility_insights(
        self, exp: Experiment, result: Dict
    ) -> Dict[str, Dict]:
        cache_key = f"utility::{exp.key}"
        if cache_key in self._insights_cache:
            return self._insights_cache[cache_key]

        syn_df = self._load_dataframe(exp.synthetic_processed)
        real_df = self._load_dataframe(exp.real_processed)
        features = syn_df.columns.tolist()

        rng = np.random.default_rng(123)
        if len(real_df) > len(syn_df):
            real_aligned = real_df.sample(
                n=len(syn_df), random_state=123, replace=False
            ).reset_index(drop=True)
        else:
            real_aligned = real_df.copy().reset_index(drop=True)
        syn_aligned = syn_df.reset_index(drop=True).iloc[: len(real_aligned)]

        feature_errors = []
        quantiles = np.linspace(0, 1, 21)
        quantile_series = []

        for col in features:
            diffs = syn_aligned[col] - real_aligned[col]
            mae = float(np.abs(diffs).mean())
            rmse = float(np.sqrt(np.mean(np.square(diffs))))
            rel_error = float(mae / (np.abs(real_aligned[col]).mean() + 1e-6))
            feature_errors.append(
                {
                    "feature": col,
                    "mae": mae,
                    "rmse": rmse,
                    "relative_error": rel_error,
                }
            )

            real_quantiles = real_aligned[col].quantile(quantiles).tolist()
            syn_quantiles = syn_aligned[col].quantile(quantiles).tolist()
            quantile_series.append(
                {
                    "feature": col,
                    "quantiles": quantiles.tolist(),
                    "real": [float(val) for val in real_quantiles],
                    "synthetic": [float(val) for val in syn_quantiles],
                }
            )

        real_corr = real_aligned.corr()
        syn_corr = syn_aligned.corr()
        corr_diff = (syn_corr - real_corr).abs()

        corr_rows = []
        max_corr_delta = corr_diff.to_numpy().max() if not corr_diff.empty else 1.0
        for row_feature in features:
            row_cells = []
            for col_feature in features:
                diff_value = float(corr_diff.loc[row_feature, col_feature])
                intensity = (
                    min(1.0, diff_value / max_corr_delta) if max_corr_delta else 0.0
                )
                row_cells.append(
                    {
                        "feature": col_feature,
                        "real": float(real_corr.loc[row_feature, col_feature]),
                        "synthetic": float(syn_corr.loc[row_feature, col_feature]),
                        "diff": diff_value,
                        "intensity": intensity,
                    }
                )
            corr_rows.append({"feature": row_feature, "cells": row_cells})

        insights = {
            "feature_errors": feature_errors,
            "quantile_series": quantile_series,
            "correlation_matrix": corr_rows,
        }
        self._insights_cache[cache_key] = insights
        return insights

    @staticmethod
    def _render_feature_similarity_table(stats: List[Dict]) -> str:
        if not stats:
            return ""

        def color_for(value: float, intensity: float) -> str:
            base_positive = (59, 130, 246)  # blue
            base_negative = (239, 68, 68)  # red
            base = base_positive if value >= 0 else base_negative
            alpha = 0.15 + 0.55 * min(1.0, intensity)
            return f"rgba({base[0]}, {base[1]}, {base[2]}, {alpha:.3f})"

        rows_html = []
        for item in stats:
            mean_style = (
                f"background:{color_for(item['mean_diff'], item['mean_intensity'])};"
            )
            std_style = (
                f"background:{color_for(item['std_diff'], item['std_intensity'])};"
            )
            rows_html.append(
                f"""
                <tr>
                    <td>{item['feature']}</td>
                    <td>{item['real_mean']:.3f}</td>
                    <td>{item['syn_mean']:.3f}</td>
                    <td style="{mean_style}">{item['mean_diff']:.3f}</td>
                    <td>{item['real_std']:.3f}</td>
                    <td>{item['syn_std']:.3f}</td>
                    <td style="{std_style}">{item['std_diff']:.3f}</td>
                </tr>
                """
            )

        return f"""
        <section style="margin-top: 2.5rem;">
            <h2 class="subtitle" style="color:#f3f4f6;">Feature Distribution Alignment</h2>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                Mean and standard deviation differences between synthetic and real data.
                Blue cells indicate synthetic values exceeding real values; red cells indicate lower values.
            </p>
            <div class="metric-card" style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Feature</th>
                            <th>Real Mean</th>
                            <th>Synthetic Mean</th>
                            <th>Mean Δ</th>
                            <th>Real Std</th>
                            <th>Synthetic Std</th>
                            <th>Std Δ</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
        </section>
        """

    @staticmethod
    def _render_correlation_heatmap(corr_rows: List[Dict]) -> str:
        if not corr_rows:
            return ""

        header_cells = "".join(
            f"<th>{cell['feature']}</th>" for cell in corr_rows[0]["cells"]
        )

        body_rows = []
        for row in corr_rows:
            cell_html = []
            for cell in row["cells"]:
                alpha = 0.15 + 0.6 * min(1.0, cell["intensity"])
                bg = f"rgba(139, 92, 246, {alpha:.3f})"
                cell_html.append(
                    f"""
                    <td style="background:{bg}">
                        <div style="display:flex;flex-direction:column;gap:0.25rem;">
                            <span style="font-size:0.9rem;">Δ {cell['diff']:.3f}</span>
                            <span style="font-size:0.75rem;color:var(--text-secondary);">
                                real {cell['real']:.2f} · syn {cell['synthetic']:.2f}
                            </span>
                        </div>
                    </td>
                    """
                )
            body_rows.append(
                f"<tr><th>{row['feature']}</th>{''.join(cell_html)}</tr>"
            )

        return f"""
        <section style="margin-top: 2.5rem;">
            <h2 class="subtitle" style="color:#f3f4f6;">Correlation Difference Heatmap</h2>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                Absolute correlation differences between synthetic and real data (darker indicates larger drift).
            </p>
            <div class="metric-card" style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Feature</th>
                            {header_cells}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(body_rows)}
                    </tbody>
                </table>
            </div>
        </section>
        """

    def prepare_all(self):
        LOGGER.info("Preparing %d experiment(s)", len(self.experiments))
        for exp in self.experiments:
            try:
                self.prepare_experiment(exp)
            except Exception as exc:
                exp.status = "failed"
                exp.error = f"Preparation failed: {exc}"
                LOGGER.exception("Preparation failed for %s", exp.key)

    def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        LOGGER.debug("Executing command: %s", " ".join(cmd))
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_membership_inference_attack(self, exp: Experiment):
        """
        Run Membership Inference Attack for an experiment.

        Adds MIA results to the results.json file under privacy.true_mia
        """
        try:
            from experiments.utils.membership_inference import run_mia_for_experiment

            LOGGER.info(f"Running Membership Inference Attack for {exp.key}")

            # Find checkpoint directory - look in various locations
            # Try: dataset_dir/checkpoints (most common)
            dataset_dir = exp.synthetic_raw.parents[2]  # stocks directory
            checkpoint_dir = dataset_dir / "checkpoints"

            # If not found, try parent of eval directory
            if not checkpoint_dir.exists():
                checkpoint_dir = exp.synthetic_raw.parent.parent / "checkpoints"

            # If still not found, try one more level up
            if not checkpoint_dir.exists():
                checkpoint_dir = exp.synthetic_raw.parents[3] / "checkpoints"

            if not checkpoint_dir.exists():
                LOGGER.warning(f"No checkpoints directory found for {exp.key} (tried multiple locations)")
                return

            # Try to find train and test data
            # Look in samples directory or parent directory
            samples_dir = exp.synthetic_raw.parents[2] / "samples"
            data_dir = exp.synthetic_raw.parents[2]

            # Try to find training data
            train_data = None
            for pattern in ["*ground_truth*train*.csv", "*train*.csv", "train.csv"]:
                matches = list(samples_dir.glob(pattern)) if samples_dir.exists() else []
                if not matches:
                    matches = list(data_dir.glob(pattern))
                if matches:
                    train_data = matches[0]
                    break

            # Try to find test data (CSV or NPY)
            test_data = None
            for pattern in ["*test*.csv", "*val*.csv", "test.csv", "validation.csv"]:
                matches = list(samples_dir.glob(pattern)) if samples_dir.exists() else []
                if not matches:
                    matches = list(data_dir.glob(pattern))
                if matches:
                    test_data = matches[0]
                    break

            # If no CSV found, try .npy files
            if test_data is None:
                for pattern in ["*test*.npy", "*val*.npy", "test.npy", "validation.npy"]:
                    matches = list(samples_dir.glob(pattern)) if samples_dir.exists() else []
                    if not matches:
                        matches = list(data_dir.glob(pattern))
                    if matches:
                        test_data_npy = matches[0]
                        # Convert .npy to CSV for MIA
                        import numpy as np
                        import pandas as pd
                        LOGGER.info(f"Converting {test_data_npy.name} to CSV for MIA")
                        data_array = np.load(test_data_npy)
                        # Reshape if 3D (n_samples, seq_len, n_features) -> 2D
                        if data_array.ndim == 3:
                            n_samples, seq_len, n_features = data_array.shape
                            data_array = data_array.reshape(n_samples, seq_len * n_features)
                        df = pd.DataFrame(data_array)
                        # Save as CSV in same directory
                        test_data = test_data_npy.parent / "test.csv"
                        df.to_csv(test_data, index=False)
                        LOGGER.info(f"Saved converted test data to {test_data.name}")
                        break

            if train_data is None:
                LOGGER.warning(f"Training data not found for MIA: {exp.key}")
                return

            if test_data is None:
                LOGGER.warning(f"Test data not found for MIA: {exp.key}")
                return

            LOGGER.info(f"MIA using train={train_data.name}, test={test_data.name}")

            # Run MIA
            mia_results = run_mia_for_experiment(
                experiment_dir=checkpoint_dir.parent,
                train_data_path=train_data,
                test_data_path=test_data
            )

            # Add to results.json
            results_file = exp.results_dir / "results.json"
            if results_file.exists():
                with open(results_file, "r") as f:
                    results = json.load(f)

                if "privacy" not in results:
                    results["privacy"] = {}

                results["privacy"]["true_mia"] = mia_results

                with open(results_file, "w") as f:
                    json.dump(results, f, indent=2)

                mia_auc = mia_results.get("auc")
                if mia_auc is not None:
                    LOGGER.info(f"MIA AUC for {exp.key}: {mia_auc:.4f}")
                else:
                    LOGGER.warning(f"MIA failed for {exp.key}: {mia_results.get('error', 'Unknown error')}")
            else:
                LOGGER.warning(f"Results file not found for MIA update: {results_file}")

        except Exception as e:
            LOGGER.error(f"MIA execution failed for {exp.key}: {e}", exc_info=True)

    def run_experiment(self, exp: Experiment):
        if exp.status == "failed":
            return

        cmd = [
            "python",
            "run.py",
            "--synthetic",
            str(exp.synthetic_processed),
            "--original",
            str(exp.real_processed),
            "--metadata",
            str(exp.metadata_path),
            "--output",
            str(exp.results_dir / "results.json"),
            "--device",
            self.device,
            "--force-cpu",
            "--plot",
        ]

        if self.dimensions:
            cmd += ["--dimensions"] + list(self.dimensions)

        cmd += ["--utility-input"] + list(UTILITY_INPUT_COLUMNS)
        cmd += ["--utility-output"] + list(UTILITY_OUTPUT_COLUMNS)

        if self.privacy_metrics:
            cmd += ["--privacy-metrics"] + list(self.privacy_metrics)

        result = self._run_command(cmd)

        exp.stdout_log.write_text(result.stdout)
        exp.stderr_log.write_text(result.stderr)

        if result.returncode != 0:
            exp.status = "failed"
            exp.error = (
                f"SynEval command failed (code {result.returncode}). "
                "See stderr log for details."
            )
            self._append_error(exp.key, exp.error)
            LOGGER.error("Evaluation failed for %s", exp.key)
        else:
            exp.status = "succeeded"
            LOGGER.info("Evaluation succeeded for %s", exp.key)

            # Run MIA after successful SynEval evaluation
            self._run_membership_inference_attack(exp)

    def run_all(self):
        LOGGER.info("Running SynEval for %d experiment(s)", len(self.experiments))
        for idx, exp in enumerate(self.experiments, start=1):
            LOGGER.info("[%d/%d] %s", idx, len(self.experiments), exp.key)
            self.run_experiment(exp)
            self._append_run_log(exp)

    def _append_run_log(self, exp: Experiment):
        timestamp = datetime.utcnow().isoformat()
        message = f"{timestamp}\t{exp.key}\t{exp.status}"
        if exp.error:
            message += f"\t{exp.error}"
        with open(self.run_log_path, "a", encoding="utf-8") as fh:
            fh.write(message + "\n")

    def _append_error(self, key: str, error: str):
        timestamp = datetime.utcnow().isoformat()
        with open(self.error_log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{timestamp}\t{key}\t{error}\n")

    def load_results(self) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}
        for exp in self.experiments:
            result_file = exp.results_dir / "results.json"
            if result_file.exists():
                with open(result_file, "r", encoding="utf-8") as fh:
                    results[exp.key] = json.load(fh)
        return results

    def build_metric_summary(self, result: Dict) -> Dict[str, float]:
        metrics: Dict[str, float] = {}

        fidelity_quality = safe_get(result, "fidelity", "quality", "Overall", "score")
        fidelity_diagnostic = safe_get(
            result, "fidelity", "diagnostic", "Overall", "score"
        )

        if fidelity_quality is not None:
            metrics["Fidelity Quality"] = float(fidelity_quality) * 100
        if fidelity_diagnostic is not None:
            metrics["Fidelity Diagnostic"] = float(fidelity_diagnostic) * 100

        real_rmse = safe_get(
            result, "utility", "tstr_accuracy", "real_data_model", "rmse"
        )
        syn_rmse = safe_get(
            result, "utility", "tstr_accuracy", "synthetic_data_model", "rmse"
        )
        real_r2 = safe_get(
            result, "utility", "tstr_accuracy", "real_data_model", "r2"
        )
        syn_r2 = safe_get(
            result, "utility", "tstr_accuracy", "synthetic_data_model", "r2"
        )

        if real_rmse is not None:
            metrics["Real RMSE"] = float(real_rmse)
        if syn_rmse is not None:
            metrics["Synthetic RMSE"] = float(syn_rmse)
        if real_r2 is not None:
            metrics["Real R2"] = float(real_r2)
        if syn_r2 is not None:
            metrics["Synthetic R2"] = float(syn_r2)

        distinguishability_auc = safe_get(
            result, "privacy", "membership_inference", "distinguishability_auc"
        )
        fidelity_based_on_auc = safe_get(
            result, "privacy", "membership_inference", "fidelity_score"
        )
        exact_match = safe_get(
            result, "privacy", "exact_matches", "exact_match_percentage"
        )

        if distinguishability_auc is not None:
            metrics["Distinguishability AUC"] = float(distinguishability_auc)
        if fidelity_based_on_auc is not None:
            metrics["AUC-Derived Fidelity"] = float(fidelity_based_on_auc)
        if exact_match is not None:
            metrics["Exact Match %"] = float(exact_match)

        diversity_entropy = safe_get(
            result, "diversity", "tabular_diversity", "entropy_metrics", "dataset_entropy", "entropy_ratio"
        )
        if diversity_entropy is not None:
            metrics["Entropy Ratio"] = float(diversity_entropy)

        return metrics

    def generate_experiment_reports(self, results: Dict[str, Dict]):
        for exp in self.experiments:
            result = results.get(exp.key)
            if not result:
                continue

            metrics = self.build_metric_summary(result)
            exp_summary = exp.to_summary(metrics)

            privacy_html = self._build_privacy_report(exp, result, metrics)
            utility_html = self._build_utility_report(exp, result, metrics)

            (exp.results_dir / "privacy_report.html").write_text(
                privacy_html, encoding="utf-8"
            )
            (exp.results_dir / "utility_report.html").write_text(
                utility_html, encoding="utf-8"
            )

        summaries = [
            exp.to_summary(self.build_metric_summary(results.get(exp.key, {})))
            for exp in self.experiments
            if exp.status == "succeeded"
        ]
        persist_summary(summaries, self.summary_path)

    def _build_privacy_report(
        self, exp: Experiment, result: Dict, metrics: Dict[str, float]
    ) -> str:
        membership = safe_get(result, "privacy", "membership_inference") or {}
        structured = safe_get(
            result, "privacy", "structured_privacy_metrics"
        ) or {}
        insights = self._compute_privacy_insights(exp, result)

        dist_auc = float(membership.get("distinguishability_auc", 0.0) or 0.0)
        fidelity_score = float(membership.get("fidelity_score", max(0.0, 1 - dist_auc)))

        # Get True MIA results
        true_mia = safe_get(result, "privacy", "true_mia") or {}
        mia_auc = true_mia.get("auc")

        gauge_config = {
            "type": "doughnut",
            "data": {
                "labels": ["Similarity (1 - AUC)", "Separability (AUC)"],
                "datasets": [
                    {
                        "data": [max(0.0, 1 - dist_auc), dist_auc],
                        "backgroundColor": ["#22c55e", "#ef4444"],
                        "hoverOffset": 4,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "cutout": "65%",
                "plugins": {
                    "legend": {"position": "bottom"}
                }
            },
        }

        coverage_config = {
            "type": "bar",
            "data": {
                "labels": [item["feature"] for item in insights.get("match_rates", [])],
                "datasets": [
                    {
                        "label": "Synthetic Coverage (%)",
                        "data": [item["coverage"] for item in insights.get("match_rates", [])],
                        "backgroundColor": "#3b82f6",
                    }
                ],
            },
            "options": {
                "responsive": True,
                "scales": {"y": {"beginAtZero": True, "max": 100}},
            },
        }

        nn_hist = insights.get("nearest_neighbor_hist", {})
        nn_config = {
            "type": "bar",
            "data": {
                "labels": nn_hist.get("bins", []),
                "datasets": [
                    {
                        "label": "Nearest Neighbor Distance",
                        "data": nn_hist.get("counts", []),
                        "backgroundColor": "#8b5cf6",
                    }
                ],
            },
            "options": {
                "responsive": True,
                "scales": {
                    "x": {"title": {"display": True, "text": "Distance (normalized units)"}},
                    "y": {"title": {"display": True, "text": "Frequency"}},
                },
            },
        }

        structured_dataset = []
        synthetic_metrics = [
            safe_get(structured, "IMS", "ims_syn_train") or 0,
            safe_get(structured, "DCR", "syn_train_5pct") or 0,
            safe_get(structured, "NNDR", "syn_train_5pct") or 0,
        ]
        baseline_metrics = [
            safe_get(structured, "IMS", "train_test_ims") or 0,
            safe_get(structured, "DCR", "train_train_5pct") or 0,
            safe_get(structured, "NNDR", "train_train_5pct") or 0,
        ]
        structured_dataset.append(
            {
                "label": "Synthetic vs Train",
                "data": synthetic_metrics,
                "backgroundColor": "#3b82f6",
            }
        )
        structured_dataset.append(
            {
                "label": "Train vs Train",
                "data": baseline_metrics,
                "backgroundColor": "#22c55e",
            }
        )

        structured_config = {
            "type": "bar",
            "data": {
                "labels": ["IMS", "DCR", "NNDR"],
                "datasets": structured_dataset,
            },
            "options": {
                "responsive": True,
                "scales": {"y": {"beginAtZero": True}},
            },
        }

        charts = [
            ("distinguishability-gauge", "Synthetic vs Real Separability", "Lower separability indicates higher fidelity.", gauge_config),
            ("coverage-bar", "Per-Feature Value Coverage", "How often synthetic values appear in the real dataset (rounded to 4 decimals).", coverage_config),
            ("nn-hist", "Nearest Neighbor Distance Distribution", "Distances between synthetic samples and their closest real neighbor after normalization.", nn_config),
            ("privacy-structured", "Structured Similarity Diagnostics", "Comparing IMS, DCR, and NNDR metrics against real data baselines.", structured_config),
        ]

        chart_blocks = []
        chart_scripts = []
        for canvas_id, heading, description, config in charts:
            chart_blocks.append(chart_block(canvas_id, heading, description))
            chart_scripts.append(script_for_chart(canvas_id, config))

        feature_table = self._render_feature_similarity_table(
            insights.get("feature_stats", [])
        )
        if feature_table:
            chart_blocks.append(feature_table)

        summary_metrics = {
            "Distinguishability AUC": metrics.get(
                "Distinguishability AUC", float("nan")
            ),
            "AUC-Derived Fidelity": fidelity_score,
            "True MIA AUC": mia_auc if mia_auc is not None else float("nan"),
            "Exact Match %": metrics.get("Exact Match %", float("nan")),
        }

        mia_interpretation = ""
        if mia_auc is not None:
            privacy_risk = "high" if mia_auc > 0.7 else "moderate" if mia_auc > 0.6 else "low"
            mia_interpretation = f"""<li><strong>True MIA AUC of {mia_auc:.3f}</strong> measures actual privacy risk. AUC near 0.5 = good privacy (model doesn't memorize). Current risk: <strong>{privacy_risk}</strong>.</li>"""
        else:
            mia_interpretation = """<li><strong>True MIA</strong> could not be computed (checkpoints or data not available).</li>"""

        narrative = f"""
        <section style="margin-top:2.5rem;">
            <div class="metric-card" style="line-height:1.6; color: var(--text-secondary);">
                <h3 style="color:#f9fafb; font-size:1.25rem; margin-bottom:0.75rem;">Privacy Metrics Interpretation</h3>
                <ul style="padding-left:1.25rem; list-style:disc;">
                    <li><strong>Distinguishability AUC of {dist_auc:.3f}</strong> measures fidelity/realism. High AUC = poor fidelity (synthetic is easily distinguished). (1 - AUC) gives fidelity score.</li>
                    {mia_interpretation}
                    <li>Coverage levels highlight which features most closely mimic the original support; gaps suggest where post-processing could improve fidelity.</li>
                    <li>Nearest neighbor distances summarise disclosure risk proxies—higher distances imply lower memorization of exact records.</li>
                    <li>Structured diagnostics (IMS, DCR, NNDR) compare distances relative to the original train/train baseline.</li>
                </ul>
                <div style="margin-top:1.5rem; padding:1rem; background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; border-radius:4px;">
                    <strong style="color:#3b82f6;">Key Distinction:</strong><br/>
                    <span style="font-size:0.9rem;">
                        • <strong>Distinguishability AUC</strong> = Can we tell synthetic from real? (measures fidelity)<br/>
                        • <strong>True MIA AUC</strong> = Does model memorize training data? (measures privacy leakage)
                    </span>
                </div>
            </div>
        </section>
        """
        chart_blocks.append(narrative)

        return render_experiment_report(
            title=f"{exp.key} – Privacy Analysis",
            subtitle=f"Epsilon {exp.epsilon or 'N/A'} · {exp.step}",
            summary_metrics=summary_metrics,
            chart_blocks=chart_blocks,
            script_blocks=chart_scripts,
        )

    def _build_utility_report(
        self, exp: Experiment, result: Dict, metrics: Dict[str, float]
    ) -> str:
        utility = safe_get(result, "utility", "tstr_accuracy") or {}
        insights = self._compute_utility_insights(exp, result)

        performance_config = {
            "type": "line",
            "data": {
                "labels": ["RMSE", "MAE", "R²"],
                "datasets": [
                    {
                        "label": "Real Model",
                        "data": [
                            safe_get(utility, "real_data_model", "rmse") or 0,
                            safe_get(utility, "real_data_model", "mae") or 0,
                            safe_get(utility, "real_data_model", "r2") or 0,
                        ],
                        "borderColor": "#22c55e",
                        "fill": False,
                    },
                    {
                        "label": "Synthetic Model",
                        "data": [
                            safe_get(utility, "synthetic_data_model", "rmse") or 0,
                            safe_get(utility, "synthetic_data_model", "mae") or 0,
                            safe_get(utility, "synthetic_data_model", "r2") or 0,
                        ],
                        "borderColor": "#ef4444",
                        "fill": False,
                    },
                ],
            },
            "options": {
                "responsive": True,
                "scales": {"y": {"beginAtZero": True}},
            },
        }

        feature_errors = insights.get("feature_errors", [])
        feature_labels = [item["feature"] for item in feature_errors]
        mae_values = [item["mae"] for item in feature_errors]
        rmse_values = [item["rmse"] for item in feature_errors]

        feature_error_config = {
            "type": "bar",
            "data": {
                "labels": feature_labels,
                "datasets": [
                    {
                        "label": "Mean Absolute Error",
                        "data": mae_values,
                        "backgroundColor": "#8b5cf6",
                    },
                    {
                        "label": "RMSE",
                        "data": rmse_values,
                        "backgroundColor": "#3b82f6",
                    },
                ],
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": "Error"},
                    }
                },
            },
        }

        quantile_series = insights.get("quantile_series", [])
        quantile_labels = quantile_series[0]["quantiles"] if quantile_series else []
        quantile_datasets = []
        color_palette = [
            "#3b82f6",
            "#22c55e",
            "#f97316",
            "#a855f7",
            "#ec4899",
            "#0ea5e9",
        ]
        for idx, item in enumerate(quantile_series):
            color_real = color_palette[idx % len(color_palette)]
            color_syn = color_palette[(idx + 3) % len(color_palette)]
            quantile_datasets.append(
                {
                    "label": f"{item['feature']} · real",
                    "data": item["real"],
                    "borderColor": color_real,
                    "fill": False,
                    "tension": 0.2,
                }
            )
            quantile_datasets.append(
                {
                    "label": f"{item['feature']} · synthetic",
                    "data": item["synthetic"],
                    "borderColor": color_syn,
                    "borderDash": [6, 4],
                    "fill": False,
                    "tension": 0.2,
                }
            )

        quantile_config = {
            "type": "line",
            "data": {
                "labels": quantile_labels,
                "datasets": quantile_datasets,
            },
            "options": {
                "responsive": True,
                "interaction": {"mode": "nearest", "axis": "x", "intersect": False},
                "scales": {
                    "x": {"title": {"display": True, "text": "Quantile"}},
                    "y": {"title": {"display": True, "text": "Value"}},
                },
            },
        }

        chart_specs = [
            ("utility-performance", "Model Performance (TSTR)", "Error metrics for models trained on real vs synthetic data.", performance_config),
            ("utility-feature-errors", "Per-Feature Error Breakdown", "Absolute and root-mean-square error across each feature.", feature_error_config),
            ("utility-quantiles", "Distribution Overlap", "Quantile comparison between synthetic and real data for each feature.", quantile_config),
        ]

        chart_blocks = []
        chart_scripts = []
        for canvas_id, heading, description, config in chart_specs:
            chart_blocks.append(chart_block(canvas_id, heading, description))
            chart_scripts.append(script_for_chart(canvas_id, config))

        correlation_html = self._render_correlation_heatmap(
            insights.get("correlation_matrix", [])
        )
        if correlation_html:
            chart_blocks.append(correlation_html)

        summary_metrics = {
            "Real RMSE": metrics.get("Real RMSE", float("nan")),
            "Synthetic RMSE": metrics.get("Synthetic RMSE", float("nan")),
            "Real R2": metrics.get("Real R2", float("nan")),
            "Synthetic R2": metrics.get("Synthetic R2", float("nan")),
        }

        narrative = f"""
        <section style=\"margin-top:2.5rem;\">
            <div class=\"metric-card\" style=\"line-height:1.6; color: var(--text-secondary);\">
                <h3 style=\"color:#f9fafb; font-size:1.25rem; margin-bottom:0.75rem;\">Interpretation</h3>
                <ul style=\"padding-left:1.25rem; list-style:disc;\">
                    <li>Feature-level errors highlight where the synthetic generator under-performs; consider targeted calibration for high-error columns.</li>
                    <li>Quantile overlays reveal whether distributional drift occurs in the tails versus central regions.</li>
                    <li>Correlation heatmaps expose structural relationships that may have weakened or inverted in synthetic data.</li>
                </ul>
            </div>
        </section>
        """
        chart_blocks.append(narrative)

        return render_experiment_report(
            title=f"{exp.key} – Utility Analysis",
            subtitle=f"Task: Regression (Close price) · Step {exp.step}",
            summary_metrics=summary_metrics,
            chart_blocks=chart_blocks,
            script_blocks=chart_scripts,
        )

    def generate_dashboards(self, results: Dict[str, Dict]):
        succeeded = [exp for exp in self.experiments if exp.status == "succeeded"]
        if not succeeded:
            LOGGER.warning("No successful experiments to include in dashboards.")
            return

        records = []
        for exp in succeeded:
            result = results.get(exp.key, {})
            metric_summary = self.build_metric_summary(result)
            records.append(
                {
                    "key": exp.key,
                    "variant": exp.variant,
                    "dp_level": exp.dp_level,
                    "step": exp.step,
                    "epsilon": exp.epsilon,
                    "metrics": metric_summary,
                }
            )

        overview_html = self._build_overview_dashboard(records)
        privacy_html = self._build_dimension_dashboard(records, dimension="privacy")
        utility_html = self._build_dimension_dashboard(records, dimension="utility")
        methodology_html = self._build_methodology_notes()

        (self.dashboards_dir / "comprehensive_overview.html").write_text(
            overview_html, encoding="utf-8"
        )
        (self.dashboards_dir / "comprehensive_privacy_dashboard.html").write_text(
            privacy_html, encoding="utf-8"
        )
        (self.dashboards_dir / "comprehensive_utility_dashboard.html").write_text(
            utility_html, encoding="utf-8"
        )
        (self.dashboards_dir / "methodology_notes.html").write_text(
            methodology_html, encoding="utf-8"
        )


    def _build_overview_dashboard(self, records: List[Dict]) -> str:
        if not records:
            return render_dashboard_page(
                title="Diffusion_TS_DP – Comprehensive Overview",
                subtitle="Aggregated privacy and utility signals",
                summary_metrics={},
                controls_html="",
                sections=[],
                script_blocks=[],
            )

        df = pd.DataFrame(
            [
                {
                    "key": item["key"],
                    "variant": item["variant"],
                    "step": item["step"],
                    "dp_level": item["dp_level"],
                    "epsilon": item["epsilon"],
                    "fidelity_quality": item["metrics"].get("Fidelity Quality", 0.0),
                    "distinguishability_auc": item["metrics"].get("Distinguishability AUC", 0.0),
                    "auc_fidelity": item["metrics"].get("AUC-Derived Fidelity", 0.0),
                    "synthetic_rmse": item["metrics"].get("Synthetic RMSE", 0.0),
                }
                for item in records
            ]
        )

        best_fidelity = df.loc[df["fidelity_quality"].idxmax()]
        best_utility = df.loc[df["synthetic_rmse"].idxmin()]

        summary_metrics = {
            "Configurations": float(len(df)),
            "Median Fidelity (%)": float(df["fidelity_quality"].median()),
            "Median Distinguishability AUC": float(df["distinguishability_auc"].median()),
            "Top Fidelity Variant": best_fidelity["variant"],
            "Best RMSE": float(best_utility["synthetic_rmse"]),
        }

        variants = ["all"] + sorted(df["variant"].unique())
        steps = ["all"] + sorted(df["step"].unique())

        variant_button_parts: List[str] = []
        for idx, variant in enumerate(variants):
            active_class = " active" if idx == 0 else ""
            variant_button_parts.append(
                f'<button class="control-button{active_class}" data-filter-type="variant" data-filter-value="{variant}">{variant}</button>'
            )
        variant_buttons = "".join(variant_button_parts)

        step_button_parts: List[str] = []
        for idx, step in enumerate(steps):
            active_class = " active" if idx == 0 else ""
            step_button_parts.append(
                f'<button class="control-button{active_class}" data-filter-type="step" data-filter-value="{step}">{step}</button>'
            )
        step_buttons = "".join(step_button_parts)

        controls_html = f"""
        <section style="margin-top: 2rem;">
            <h2 class="subtitle" style="color:#f3f4f6; margin-bottom:1rem;">Interactive Filters</h2>
            <div class="control-panel" data-filter-group="variant">
                {variant_buttons}
            </div>
            <div class="control-panel" data-filter-group="step" style="margin-top:1rem;">
                {step_buttons}
            </div>
        </section>
        """

        sections = [
            chart_block(
                "overview-radar",
                "Cross-Experiment Privacy & Fidelity",
                "Radar view summarising separability and fidelity metrics across the selected cohort.",
            ),
            chart_block(
                "privacy-utility-scatter",
                "Privacy–Utility Trade-off",
                "Scatter plot comparing distinguishability AUC versus synthetic RMSE.",
            ),
            chart_block(
                "epsilon-rmse-line",
                "RMSE Progression by ε",
                "How utility evolves with the privacy budget for each configuration.",
            ),
        ]

        table_rows = []
        for _, row in df.iterrows():
            epsilon_display = (
                f"{row['epsilon']:.2f}" if isinstance(row["epsilon"], (int, float)) else "N/A"
            )
            table_rows.append(
                f"""
                <tr data-key="{row['key']}" data-variant="{row['variant']}" data-step="{row['step']}">
                    <td>{row['key']}</td>
                    <td>{row['variant']}</td>
                    <td>{row['step']}</td>
                    <td>{row['dp_level']}</td>
                    <td>{epsilon_display}</td>
                    <td>{row['fidelity_quality']:.2f}</td>
                    <td>{row['distinguishability_auc']:.3f}</td>
                    <td>{row['synthetic_rmse']:.3f}</td>
                    <td>{row['auc_fidelity']:.3f}</td>
                </tr>
                """
            )

        matrix_section = f"""
        <section style="margin-top: 3rem;">
            <h2 class="subtitle" style="color:#f3f4f6;">Comparison Matrix</h2>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">Sortable overview of privacy and utility signals for the active subset.</p>
            <div class="metric-card" style="overflow-x:auto;">
                <table id="overview-table">
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th>Variant</th>
                            <th>Step</th>
                            <th>DP Level</th>
                            <th>ε</th>
                            <th>Fidelity %</th>
                            <th>Distinguishability AUC</th>
                            <th>Synthetic RMSE</th>
                            <th>AUC-Derived Fidelity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
        </section>
        """
        sections.append(matrix_section)

        dataset_payload = [
            {
                "key": row["key"],
                "variant": row["variant"],
                "step": row["step"],
                "dp_level": row["dp_level"],
                "epsilon": row["epsilon"],
                "fidelity_quality": row["fidelity_quality"],
                "distinguishability_auc": row["distinguishability_auc"],
                "synthetic_rmse": row["synthetic_rmse"],
                "auc_fidelity": row["auc_fidelity"],
            }
            for _, row in df.iterrows()
        ]

        script_template = Template(
            dedent(
                """
                __registerChartConfig(function () {
                    const dataset = $dataset;
                    let activeVariant = 'all';
                    let activeStep = 'all';
                    const colorPalette = ['#3b82f6','#22c55e','#f97316','#8b5cf6','#ef4444','#0ea5e9'];

                    const radarCanvas = document.getElementById('overview-radar');
                    const scatterCanvas = document.getElementById('privacy-utility-scatter');
                    const lineCanvas = document.getElementById('epsilon-rmse-line');
                    if (!(radarCanvas && scatterCanvas && lineCanvas)) {
                        console.error('Overview canvases missing; aborting chart initialization.');
                        return;
                    }

                    const radarChart = new Chart(radarCanvas.getContext('2d'), {
                        type: 'radar',
                        data: { labels: [], datasets: [] },
                        options: {
                            responsive: true,
                            scales: {
                                r: {
                                    angleLines: { color: 'rgba(148,163,184,0.3)' },
                                    grid: { color: 'rgba(148,163,184,0.2)' },
                                    pointLabels: { color: '#f9fafb', font: { size: 12 } },
                                }
                            }
                        }
                    });

                    const scatterChart = new Chart(scatterCanvas.getContext('2d'), {
                        type: 'scatter',
                        data: { datasets: [] },
                        options: {
                            responsive: true,
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const d = ctx.raw;
                                            return d.key + ' — RMSE ' + d.y.toFixed(3) + ', AUC ' + d.x.toFixed(3);
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: { title: { display: true, text: 'Distinguishability AUC' }, min: 0, max: 1 },
                                y: { title: { display: true, text: 'Synthetic RMSE' }, beginAtZero: true }
                            }
                        }
                    });

                    const lineChart = new Chart(lineCanvas.getContext('2d'), {
                        type: 'line',
                        data: { labels: [], datasets: [] },
                        options: {
                            responsive: true,
                            interaction: { mode: 'index', intersect: false },
                            scales: {
                                x: { title: { display: true, text: 'ε' } },
                                y: { title: { display: true, text: 'Synthetic RMSE' }, beginAtZero: true }
                            }
                        }
                    });

                    function filteredItems() {
                        return dataset.filter(function (item) {
                            const variantMatch = activeVariant === 'all' || item.variant === activeVariant;
                            const stepMatch = activeStep === 'all' || item.step === activeStep;
                            return variantMatch && stepMatch;
                        });
                    }

                    function updateRadar(items) {
                        radarChart.data.labels = items.map(function (d) { return d.key; });
                        radarChart.data.datasets = [
                            {
                                label: 'Distinguishability AUC',
                                data: items.map(function (d) { return d.distinguishability_auc; }),
                                backgroundColor: 'rgba(59,130,246,0.2)',
                                borderColor: '#3b82f6'
                            },
                            {
                                label: 'Fidelity (%)',
                                data: items.map(function (d) { return d.fidelity_quality; }),
                                backgroundColor: 'rgba(139,92,246,0.2)',
                                borderColor: '#8b5cf6'
                            }
                        ];
                        radarChart.update();
                    }

                    function updateScatter(items) {
                        const grouped = {};
                        items.forEach(function (item) {
                            if (!grouped[item.variant]) grouped[item.variant] = [];
                            grouped[item.variant].push({ x: item.distinguishability_auc, y: item.synthetic_rmse, key: item.key });
                        });
                        scatterChart.data.datasets = Object.keys(grouped).map(function (variant, idx) {
                            return {
                                label: variant,
                                data: grouped[variant],
                                backgroundColor: colorPalette[idx % colorPalette.length]
                            };
                        });
                        scatterChart.update();
                    }

                    function updateLine(items) {
                        const valid = items.filter(function (item) { return typeof item.epsilon === 'number'; });
                        const labels = Array.from(new Set(valid.map(function (item) { return item.epsilon; }))).sort(function (a, b) { return a - b; });
                        const grouped = {};
                        valid.forEach(function (item) {
                            if (!grouped[item.variant]) grouped[item.variant] = [];
                            grouped[item.variant].push({ epsilon: item.epsilon, rmse: item.synthetic_rmse });
                        });
                        lineChart.data.labels = labels;
                        lineChart.data.datasets = Object.keys(grouped).map(function (variant, idx) {
                            const points = grouped[variant].sort(function (a, b) { return a.epsilon - b.epsilon; });
                            return {
                                label: variant,
                                data: points.map(function (p) { return p.rmse; }),
                                borderColor: colorPalette[idx % colorPalette.length],
                                fill: false,
                                spanGaps: true
                            };
                        });
                        lineChart.update();
                    }

                    function updateTable(items) {
                        const rows = document.querySelectorAll('#overview-table tbody tr');
                        rows.forEach(function (row) {
                            const key = row.getAttribute('data-key');
                            const visible = items.some(function (item) { return item.key === key; });
                            row.style.display = visible ? '' : 'none';
                        });
                    }

                    function refresh() {
                        const filtered = filteredItems();
                        if (filtered.length === 0) {
                            radarChart.data.labels = [];
                            radarChart.data.datasets = [];
                            radarChart.update();
                            scatterChart.data.datasets = [];
                            scatterChart.update();
                            lineChart.data.labels = [];
                            lineChart.data.datasets = [];
                            lineChart.update();
                            updateTable(filtered);
                            return;
                        }
                        updateRadar(filtered);
                        updateScatter(filtered);
                        updateLine(filtered);
                        updateTable(filtered);
                    }

                    variantButtons.forEach(function (button) {
                        button.addEventListener('click', function () {
                            activeVariant = button.getAttribute('data-filter-value');
                            variantButtons.forEach(function (btn) { btn.classList.toggle('active', btn === button); });
                            refresh();
                        });
                    });

                    stepButtons.forEach(function (button) {
                        button.addEventListener('click', function () {
                            activeStep = button.getAttribute('data-filter-value');
                            stepButtons.forEach(function (btn) { btn.classList.toggle('active', btn === button); });
                            refresh();
                        });
                    });

                    refresh();
                });
                """
            )
        )

        script = script_template.substitute(dataset=json.dumps(dataset_payload))

        return render_dashboard_page(
            title="Diffusion_TS_DP – Comprehensive Overview",
            subtitle="Aggregated privacy and utility signals across configurations",
            summary_metrics=summary_metrics,
            controls_html=controls_html,
            sections=sections,
            script_blocks=[script],
        )


    def _build_dimension_dashboard(
        self, records: List[Dict], dimension: str
    ) -> str:
        if not records:
            return render_dashboard_page(
                title="Comprehensive Dashboard",
                subtitle="",
                summary_metrics={},
                controls_html="",
                sections=[],
                script_blocks=[],
            )

        df = pd.DataFrame(
            [
                {
                    "key": item["key"],
                    "variant": item["variant"],
                    "step": item["step"],
                    "dp_level": item["dp_level"],
                    "epsilon": item["epsilon"],
                    "fidelity_quality": item["metrics"].get("Fidelity Quality", 0.0),
                    "distinguishability_auc": item["metrics"].get("Distinguishability AUC", 0.0),
                    "synthetic_rmse": item["metrics"].get("Synthetic RMSE", 0.0),
                }
                for item in records
            ]
        )

        metric_field = "distinguishability_auc" if dimension == "privacy" else "synthetic_rmse"
        metric_label = "Distinguishability AUC" if dimension == "privacy" else "Synthetic RMSE"
        title = (
            "Comprehensive Privacy Dashboard"
            if dimension == "privacy"
            else "Comprehensive Utility Dashboard"
        )
        subtitle = (
            "Exploring separability trends across DP configurations"
            if dimension == "privacy"
            else "Evaluating downstream performance across DP configurations"
        )

        summary_metrics = {
            "Median": float(df[metric_field].median()),
            "Minimum": float(df[metric_field].min()),
            "Maximum": float(df[metric_field].max()),
        }

        variants = ["all"] + sorted(df["variant"].unique())
        steps = ["all"] + sorted(df["step"].unique())

        variant_button_parts: List[str] = []
        for idx, variant in enumerate(variants):
            active_class = " active" if idx == 0 else ""
            variant_button_parts.append(
                f'<button class="control-button{active_class}" data-filter-type="variant" data-filter-value="{variant}">{variant}</button>'
            )
        variant_buttons = "".join(variant_button_parts)

        step_button_parts: List[str] = []
        for idx, step in enumerate(steps):
            active_class = " active" if idx == 0 else ""
            step_button_parts.append(
                f'<button class="control-button{active_class}" data-filter-type="step" data-filter-value="{step}">{step}</button>'
            )
        step_buttons = "".join(step_button_parts)

        controls_html = f"""
        <section style="margin-top: 2rem;">
            <h2 class="subtitle" style="color:#f3f4f6; margin-bottom:1rem;">Interactive Filters</h2>
            <div class="control-panel" data-filter-group="variant">
                {variant_buttons}
            </div>
            <div class="control-panel" data-filter-group="step" style="margin-top:1rem;">
                {step_buttons}
            </div>
        </section>
        """

        line_canvas = "privacy-epsilon-line" if dimension == "privacy" else "utility-epsilon-line"
        bar_canvas = "privacy-step-bar" if dimension == "privacy" else "utility-step-bar"
        table_id = f"dimension-table-{dimension}"

        sections = [
            chart_block(
                line_canvas,
                f"{metric_label} vs ε",
                "Separability as a function of the privacy budget (ε)." if dimension == "privacy" else "Utility (RMSE) as a function of ε.",
            ),
            chart_block(
                bar_canvas,
                f"{metric_label} by Training Step",
                "Average separability grouped by training step." if dimension == "privacy" else "Average RMSE grouped by training step.",
            ),
        ]

        table_rows = []
        for _, row in df.iterrows():
            epsilon_display = (
                f"{row['epsilon']:.2f}" if isinstance(row["epsilon"], (int, float)) else "N/A"
            )
            table_rows.append(
                f"""
                <tr data-key="{row['key']}" data-variant="{row['variant']}" data-step="{row['step']}">
                    <td>{row['key']}</td>
                    <td>{row['variant']}</td>
                    <td>{row['step']}</td>
                    <td>{row['dp_level']}</td>
                    <td>{epsilon_display}</td>
                    <td>{row[metric_field]:.3f}</td>
                    <td>{row['fidelity_quality']:.2f}</td>
                </tr>
                """
            )

        sections.append(
            f"""
            <section style="margin-top: 3rem;">
                <h2 class="subtitle" style="color:#f3f4f6;">Detailed Metrics</h2>
                <p style="color: var(--text-secondary); margin-bottom: 1rem;">Filter-aware table summarising key indicators.</p>
                <div class="metric-card" style="overflow-x:auto;">
                    <table id="{table_id}">
                        <thead>
                            <tr>
                                <th>Configuration</th>
                                <th>Variant</th>
                                <th>Step</th>
                                <th>DP Level</th>
                                <th>ε</th>
                                <th>{metric_label}</th>
                                <th>Fidelity %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
            </section>
            """
        )

        dataset_payload = [
            {
                "key": row["key"],
                "variant": row["variant"],
                "step": row["step"],
                "dp_level": row["dp_level"],
                "epsilon": row["epsilon"],
                "metric": row[metric_field],
                "fidelity_quality": row["fidelity_quality"],
            }
            for _, row in df.iterrows()
        ]

        script_template = Template(
            dedent(
                """
                __registerChartConfig(function () {
                    const dataset = $dataset;
                    let activeVariant = 'all';
                    let activeStep = 'all';
                    const colors = ['#3b82f6','#22c55e','#f97316','#8b5cf6','#ef4444','#0ea5e9'];

                    const lineChart = new Chart(document.getElementById('$line_canvas').getContext('2d'), {
                        type: 'line',
                        data: { labels: [], datasets: [] },
                        options: {
                            responsive: true,
                            interaction: { mode: 'index', intersect: false },
                            scales: {
                                x: { title: { display: true, text: 'ε' } },
                                y: { title: { display: true, text: '$metric_label' }, beginAtZero: true }
                            }
                        }
                    });

                    const barChart = new Chart(document.getElementById('$bar_canvas').getContext('2d'), {
                        type: 'bar',
                        data: { labels: [], datasets: [] },
                        options: {
                            responsive: true,
                            scales: {
                                x: { title: { display: true, text: 'Training Step' } },
                                y: { title: { display: true, text: '$metric_label' }, beginAtZero: true }
                            }
                        }
                    });

                    const tableRows = document.querySelectorAll('#$table_id tbody tr');

                    function filtered() {
                        return dataset.filter(function (item) {
                            const variantMatch = activeVariant === 'all' || item.variant === activeVariant;
                            const stepMatch = activeStep === 'all' || item.step === activeStep;
                            return variantMatch && stepMatch;
                        });
                    }

                    function updateLine(items) {
                        const valid = items.filter(function (item) { return typeof item.epsilon === 'number'; });
                        const labels = Array.from(new Set(valid.map(function (item) { return item.epsilon; }))).sort(function (a, b) { return a - b; });
                        const grouped = {};
                        valid.forEach(function (item) {
                            if (!grouped[item.variant]) grouped[item.variant] = [];
                            grouped[item.variant].push({ epsilon: item.epsilon, metric: item.metric });
                        });
                        lineChart.data.labels = labels;
                        lineChart.data.datasets = Object.keys(grouped).map(function (variant, idx) {
                            const points = grouped[variant].sort(function (a, b) { return a.epsilon - b.epsilon; });
                            return {
                                label: variant,
                                data: points.map(function (p) { return p.metric; }),
                                borderColor: colors[idx % colors.length],
                                fill: false,
                                spanGaps: true
                            };
                        });
                        lineChart.update();
                    }

                    function updateBar(items) {
                        const grouped = {};
                        items.forEach(function (item) {
                            if (!grouped[item.step]) grouped[item.step] = [];
                            grouped[item.step].push(item.metric);
                        });
                        const labels = Object.keys(grouped);
                        const values = labels.map(function (step) {
                            const arr = grouped[step];
                            return arr.reduce(function (acc, val) { return acc + val; }, 0) / arr.length;
                        });
                        barChart.data.labels = labels;
                        barChart.data.datasets = [{
                            label: '$metric_label',
                            data: values,
                            backgroundColor: '#8b5cf6'
                        }];
                        barChart.update();
                    }

                    function updateTable(items) {
                        tableRows.forEach(function (row) {
                            const key = row.getAttribute('data-key');
                            const visible = items.some(function (item) { return item.key === key; });
                            row.style.display = visible ? '' : 'none';
                        });
                    }

                    function refresh() {
                        const items = filtered();
                        if (items.length === 0) {
                            lineChart.data.labels = [];
                            lineChart.data.datasets = [];
                            lineChart.update();
                            barChart.data.labels = [];
                            barChart.data.datasets = [];
                            barChart.update();
                            updateTable(items);
                            return;
                        }
                        updateLine(items);
                        updateBar(items);
                        updateTable(items);
                    }

                    const variantButtons = document.querySelectorAll('[data-filter-type="variant"]');
                    const stepButtons = document.querySelectorAll('[data-filter-type="step"]');

                    variantButtons.forEach(function (button) {
                        button.addEventListener('click', function () {
                            activeVariant = button.getAttribute('data-filter-value');
                            variantButtons.forEach(function (btn) { btn.classList.toggle('active', btn === button); });
                            refresh();
                        });
                    });

                    stepButtons.forEach(function (button) {
                        button.addEventListener('click', function () {
                            activeStep = button.getAttribute('data-filter-value');
                            stepButtons.forEach(function (btn) { btn.classList.toggle('active', btn === button); });
                            refresh();
                        });
                    });

                    refresh();
                });
                """
            )
        )

        script = script_template.substitute(
            dataset=json.dumps(dataset_payload),
            line_canvas=line_canvas,
            bar_canvas=bar_canvas,
            metric_label=metric_label,
            table_id=table_id,
        )

        return render_dashboard_page(
            title=title,
            subtitle=subtitle,
            summary_metrics=summary_metrics,
            controls_html=controls_html,
            sections=sections,
            script_blocks=[script],
        )

    def _build_methodology_notes(self) -> str:
        notes = """
        <section style="margin-top: 2rem;">
            <h2 class="subtitle" style="color: #f3f4f6;">Methodology Highlights</h2>
            <div class="metric-card">
                <p style="color: var(--text-secondary); line-height: 1.6;">
                    Evaluations were executed with SynEval across fidelity, utility, diversity,
                    and privacy dimensions. Utility relies on a Train-on-Synthetic, Test-on-Real (TSTR)
                    regression task that predicts the close price. Privacy analysis measures how
                    distinguishable synthetic samples are from real data (AUC), tracks exact match coverage,
                    and inspects proximity metrics (IMS/DCR/NNDR) to surface potential memorisation.
                    All datasets are standardised to a consistent OHLCV schema before scoring.
                </p>
            </div>
        </section>
        """
        return render_experiment_report(
            title="Methodology Notes",
            subtitle="How to interpret the Diffusion_TS_DP SynEval dashboards",
            summary_metrics={
                "Dimensions": 4,
                "Utility Task": "Regression (Close)",
                "Privacy Metrics": "Distinguishability · Exact Matches · Structured",
            },
            chart_blocks=[notes],
            script_blocks=[],
        )

    def validate_outputs(self) -> Dict[str, List[str]]:
        validation = {"missing_results": [], "missing_html": []}
        for exp in self.experiments:
            results_file = exp.results_dir / "results.json"
            if not results_file.exists():
                validation["missing_results"].append(exp.key)

            privacy_html = exp.results_dir / "privacy_report.html"
            utility_html = exp.results_dir / "utility_report.html"
            if not privacy_html.exists() or not utility_html.exists():
                validation["missing_html"].append(exp.key)
        return validation

    def run_pipeline(self, skip_copy: bool = False, limit: Optional[int] = None):
        LOGGER.info("===== SynEval Orchestration Started =====")
        if not skip_copy:
            self.copy_data()

        self.discover_experiments(limit=limit)
        if not self.experiments:
            LOGGER.error("No experiments found; aborting.")
            return

        self.prepare_all()
        self.run_all()

        results = self.load_results()
        self.generate_experiment_reports(results)
        self.generate_dashboards(results)

        validation = self.validate_outputs()
        LOGGER.info("Validation summary: %s", validation)
        LOGGER.info("===== Pipeline Completed =====")


def configure_logging(debug: bool, log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "orchestration.log"),
        ],
    )


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate SynEval evaluation pipeline for Diffusion_TS_DP outputs."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Source directory containing experiment artifacts (read-only).",
    )
    parser.add_argument(
        "--working-dir",
        type=Path,
        default=Path("./experiments"),
        help="Workspace directory for data copies, results, and dashboards.",
    )
    parser.add_argument(
        "--dimensions",
        nargs="+",
        default=list(DEFAULT_DIMENSIONS),
        choices=list(DEFAULT_DIMENSIONS),
        help="Evaluation dimensions to execute.",
    )
    parser.add_argument(
        "--privacy-metrics",
        nargs="+",
        default=list(DEFAULT_PRIVACY_METRICS),
        choices=list(DEFAULT_PRIVACY_METRICS) + ["text_privacy", "anonymeter"],
        help="Privacy metrics to enable.",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        default=list(DEFAULT_STEPS),
        help="Training steps to include (e.g., step_0010000).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["auto", "cpu", "cuda"],
        help="Device preference forwarded to SynEval.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of experiments to process.",
    )
    parser.add_argument(
        "--skip-copy",
        action="store_true",
        help="Skip copying data from the source directory.",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        help="Optional list of experiment variant directories to include (e.g., OUTPUT_GRID_ROW_DP_EXTREMA).",
    )
    parser.add_argument(
        "--dp-levels",
        nargs="+",
        help="Optional list of dp levels (e.g., dp_eps1, dp_eps1000) to include.",
    )
    parser.add_argument(
        "--debug-mode",
        action="store_true",
        help="Enable verbose logging for development.",
    )
    parser.add_argument(
        "--comprehensive-dashboard",
        action="store_true",
        help="(retained for CLI compatibility) Dashboards are always generated.",
    )
    parser.add_argument(
        "--validate-outputs",
        action="store_true",
        help="(retained for CLI compatibility) Outputs are validated at the end.",
    )
    return parser.parse_args()


def main():
    args = parse_cli()
    configure_logging(args.debug_mode, Path(args.working_dir) / "logs")

    orchestrator = SynEvalOrchestrator(
        source_dir=args.source_dir,
        working_dir=args.working_dir,
        dimensions=args.dimensions,
        step_filter=args.steps,
        device=args.device,
        privacy_metrics=args.privacy_metrics,
        variants_filter=args.variants,
        dp_levels_filter=args.dp_levels,
    )
    orchestrator.run_pipeline(skip_copy=args.skip_copy, limit=args.limit)

    if args.validate_outputs:
        validation = orchestrator.validate_outputs()
        LOGGER.info("Validation results: %s", validation)


if __name__ == "__main__":
    main()
