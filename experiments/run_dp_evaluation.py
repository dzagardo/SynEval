#!/usr/bin/env python3
"""
Differential Privacy Evaluation Runner.

This script orchestrates SynEval across multiple experiment groups defined in
``configs/cross_group_dp.yaml``. Each experiment corresponds to a combination of
group directory and privacy epsilon, and the runner aggregates fidelity, utility,
diversity, privacy, and membership inference metrics into structured reports.

The utility evaluation is driven entirely by the configuration: users must
provide ``utility.target_column`` and ``utility.input_columns`` so the runner can
select the appropriate features when calling ``SynEval.evaluate_utility``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

# Ensure the repository root is available for imports such as ``run.SynEval``.
sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


DEFAULT_STOCK_COLUMNS = ["Open", "High", "Low", "Close", "Adj_Close", "Volume"]


def _convert_numpy_for_json(obj: Any) -> Any:
    """Convert NumPy scalars/arrays inside nested structures before JSON dumping."""
    import numpy as _np

    if isinstance(obj, _np.ndarray):
        return obj.tolist()
    if isinstance(obj, _np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {k: _convert_numpy_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(_convert_numpy_for_json(v) for v in obj)
    return obj


def _sanitize_identifier(raw: str) -> str:
    """Produce filesystem-friendly identifiers (used in result directory names)."""
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(raw))


@dataclass
class ExperimentConfig:
    """Configuration for a single DP evaluation experiment."""

    group_key: str
    group_display_name: str
    epsilon: str
    synthetic_data_path: Path
    train_data_path: Path
    test_data_path: Path
    results_dir: Path
    model_path: Optional[Path] = None
    dataset_name: Optional[str] = None
    mia_adapter: Optional[str] = None
    experiment_id: str = field(init=False)

    def __post_init__(self) -> None:
        epsilon_token = _sanitize_identifier(self.epsilon)
        self.experiment_id = f"{self.group_key}_eps{epsilon_token}"


class DPEvaluationRunner:
    """Main orchestrator for Differential Privacy evaluation experiments."""

    def __init__(self, config_path: str = "configs/cross_group_dp.yaml") -> None:
        self.project_root = Path(__file__).parent.parent
        self.config_path = self._resolve_path(config_path)
        self.config = self._load_config()

        self.report_cfg = self.config.get("reporting", {}) or {}
        reports_dir = self.report_cfg.get("reports_output_dir", "reports/dp_evaluation")
        self.results_base_dir = self._resolve_path(reports_dir)
        self.results_base_dir.mkdir(parents=True, exist_ok=True)

        self.execution_cfg = self.config.get("execution", {}) or {}
        self._configure_execution_environment()

        cache_dir = self.execution_cfg.get("cache_dir")
        if self.execution_cfg.get("enable_cache") and cache_dir:
            self._resolve_path(cache_dir).mkdir(parents=True, exist_ok=True)

        self.privacy_cfg = self.config.get("privacy", {}) or {}
        self.skip_privacy_anonymeter = bool(self.privacy_cfg.get("skip_anonymeter", True))
        max_rows = self.privacy_cfg.get("max_rows")
        self.max_privacy_rows: Optional[int] = int(max_rows) if max_rows else None

        self.syneval_experiments_cfg = self.config.get("syneval_experiments", {}) or {}
        self.mia_config = self.config.get("mia", {}) or {}

        self.utility_cfg = self.config.get("utility", {}) or {}
        self.utility_target_column: Optional[str] = self.utility_cfg.get("target_column")
        self.utility_input_columns: List[str] = list(self.utility_cfg.get("input_columns", []))
        self.utility_selected_metrics: Optional[List[str]] = self.utility_cfg.get("selected_metrics")

        if not self.utility_target_column:
            raise ValueError("utility.target_column must be defined in the configuration.")
        if not self.utility_input_columns:
            raise ValueError("utility.input_columns must provide at least one feature column.")

        data_cfg = self.config.get("data_config", {}) or {}
        configured_columns = data_cfg.get("column_names")
        if isinstance(configured_columns, list) and configured_columns:
            self.default_columns: List[str] = [str(col) for col in configured_columns]
        else:
            self.default_columns = DEFAULT_STOCK_COLUMNS

        log_file = self.execution_cfg.get("log_file", "dp_evaluation.log")
        self._ensure_file_handler(self._resolve_path(log_file))

        self._data_cache: Dict[Path, pd.DataFrame] = {}
        self.all_results: Dict[str, Dict[str, Any]] = {}
        self.group_results: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------ helpers
    def _resolve_path(self, path_like: str | Path) -> Path:
        path = Path(path_like)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        with open(self.config_path, "r") as handle:
            config = yaml.safe_load(handle)
        logger.info("Loaded configuration from %s", self.config_path)
        return config

    def _configure_execution_environment(self) -> None:
        log_level = self.execution_cfg.get("log_level")
        if isinstance(log_level, str):
            logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))

        openblas_threads = self.execution_cfg.get("openblas_threads")
        if openblas_threads:
            thread_str = str(openblas_threads)
            os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_str)
            os.environ.setdefault("OMP_NUM_THREADS", thread_str)
            os.environ.setdefault("MKL_NUM_THREADS", thread_str)

    def _ensure_file_handler(self, log_path: Path) -> None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                existing = Path(getattr(handler, "baseFilename", ""))
                if existing.resolve() == log_path.resolve():
                    return

        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        root_logger.addHandler(handler)

    # ---------------------------------------------------------------- configs
    def _generate_experiment_configs(self) -> List[ExperimentConfig]:
        experiment_configs: List[ExperimentConfig] = []

        directories = self.config.get("experiment_directories", {}) or {}
        epsilons = [str(eps) for eps in self.config.get("epsilons", [])]
        if not directories or not epsilons:
            raise ValueError("Config must define experiment_directories and epsilons.")

        data_cfg = self.config.get("data_config", {}) or {}
        model_cfg = self.config.get("model_config", {}) or {}
        prefix = self.config.get("experiment_prefix", "dp_eps")

        for group_key, group_info in directories.items():
            group_display_name = group_info.get("display_name", group_key)
            group_path = self._resolve_path(group_info["path"])
            dataset_name = group_info.get("dataset", self.mia_config.get("dataset"))
            mia_adapter = group_info.get("mia_adapter", self.mia_config.get("adapter"))

            for epsilon in epsilons:
                exp_dir = group_path / f"{prefix}{epsilon}"
                data_root = exp_dir / data_cfg.get("data_dir", "")

                synthetic_path = data_root / data_cfg.get("synthetic_data", "synthetic.csv")
                train_path = data_root / data_cfg.get("train_data", "train.csv")
                test_path = data_root / data_cfg.get("test_data", "test.csv")

                model_dir = exp_dir / model_cfg.get("model_dir", "")
                model_filename = model_cfg.get("model_file")
                model_path = model_dir / model_filename if model_filename else None

                eps_token = _sanitize_identifier(epsilon)
                results_dir = self.results_base_dir / group_key / f"eps_{eps_token}"
                results_dir.mkdir(parents=True, exist_ok=True)

                experiment_configs.append(
                    ExperimentConfig(
                        group_key=group_key,
                        group_display_name=group_display_name,
                        epsilon=epsilon,
                        synthetic_data_path=synthetic_path,
                        train_data_path=train_path,
                        test_data_path=test_path,
                        results_dir=results_dir,
                        model_path=model_path,
                        dataset_name=dataset_name,
                        mia_adapter=mia_adapter,
                    )
                )

        return experiment_configs

    def _validate_experiment_files(self, exp_config: ExperimentConfig) -> Tuple[bool, List[str]]:
        validation_cfg = self.config.get("validation", {}) or {}
        if not validation_cfg.get("check_files_exist", True):
            return True, []

        missing: List[str] = []
        if not exp_config.synthetic_data_path.exists():
            missing.append(f"Synthetic data: {exp_config.synthetic_data_path}")
        if not exp_config.train_data_path.exists():
            missing.append(f"Train data: {exp_config.train_data_path}")
        if not exp_config.test_data_path.exists():
            alternative_csv = exp_config.test_data_path.with_suffix(".csv")
            if not alternative_csv.exists():
                missing.append(f"Test data: {exp_config.test_data_path}")
        return (not missing, missing)

    # ----------------------------------------------------------------- loading
    def _read_dataframe(self, path: Path) -> pd.DataFrame:
        absolute = self._resolve_path(path)
        if absolute in self._data_cache:
            return self._data_cache[absolute].copy()

        if absolute.suffix.lower() == ".csv":
            df = pd.read_csv(absolute)
        elif absolute.suffix.lower() == ".npy":
            array = np.load(absolute, allow_pickle=True)
            if array.ndim == 3:
                array = array.reshape(-1, array.shape[-1])
            n_features = array.shape[1] if array.ndim > 1 else 1
            columns = self.default_columns[:n_features]
            df = pd.DataFrame(array, columns=columns)
        else:
            raise ValueError(f"Unsupported data format: {absolute}")

        df = self._rename_default_columns(df)
        self._data_cache[absolute] = df
        return df.copy()

    def _rename_default_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = df.copy()
        digit_like = all(str(col).isdigit() for col in renamed.columns)
        if digit_like:
            rename_map = {}
            for col in renamed.columns:
                idx = int(col)
                if 0 <= idx < len(self.default_columns):
                    rename_map[col] = self.default_columns[idx]
            if rename_map:
                renamed = renamed.rename(columns=rename_map)
        return renamed

    def _coerce_utility_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        coerced = df.copy()
        for col in self.utility_input_columns:
            if col in coerced.columns:
                coerced[col] = pd.to_numeric(coerced[col], errors="coerce")
        target = self.utility_target_column
        if target and target in coerced.columns and coerced[target].dtype == object:
            coerced[target] = coerced[target].astype(str).str.strip()
        return coerced

    def _load_data(self, exp_config: ExperimentConfig) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        synthetic = self._read_dataframe(exp_config.synthetic_data_path)
        train = self._read_dataframe(exp_config.train_data_path)

        test_path = exp_config.test_data_path
        if not test_path.exists() and test_path.with_suffix(".csv").exists():
            test_path = test_path.with_suffix(".csv")
        test = self._read_dataframe(test_path)

        reference_columns = train.columns.tolist()
        for name, df in (("synthetic", synthetic), ("test", test)):
            missing = [col for col in reference_columns if col not in df.columns]
            if missing:
                raise ValueError(
                    f"{name.capitalize()} data for {exp_config.experiment_id} missing columns: {missing}"
                )

        synthetic = synthetic[reference_columns]
        test = test[reference_columns]

        synthetic = self._coerce_utility_columns(synthetic)
        train = self._coerce_utility_columns(train)
        test = self._coerce_utility_columns(test)

        target = self.utility_target_column
        if target:
            for name, df in (("synthetic", synthetic), ("train", train), ("test", test)):
                if target not in df.columns:
                    raise ValueError(
                        f"Target column '{target}' not present in {name} data for {exp_config.experiment_id}."
                    )

        missing_inputs = [
            col
            for col in self.utility_input_columns
            if any(col not in df.columns for df in (synthetic, train, test))
        ]
        if missing_inputs:
            raise ValueError(
                f"Utility input columns missing for {exp_config.experiment_id}: {missing_inputs}"
            )

        return train, test, synthetic

    # ---------------------------------------------------------------- metadata
    def _generate_metadata(self, data: pd.DataFrame) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "columns": {},
            "primary_key": None,
            "METADATA_SPEC_VERSION": "1.0",
        }

        for col in data.columns:
            dtype = data[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                sdtype = "numerical"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                sdtype = "datetime"
            else:
                sdtype = "categorical"

            col_meta: Dict[str, Any] = {"sdtype": sdtype}
            if sdtype == "categorical":
                unique_vals = data[col].dropna().unique().tolist()
                col_meta["categories"] = [str(val) for val in unique_vals][:200]
            metadata["columns"][col] = col_meta

        return metadata

    # --------------------------------------------------------------- reporting
    def _call_individual_report_generator(self, exp_config: ExperimentConfig, results: Dict[str, Any]) -> None:
        if not self.report_cfg.get("individual_reports", True):
            return
        try:
            from experiments.utils.dp_html_generator import DPHtmlGenerator  # type: ignore
        except ImportError:
            try:
                from dp_html_generator import DPHtmlGenerator  # type: ignore
            except ImportError:
                logger.warning("HTML generator not available; skipping individual report.")
                return
        try:
            generator = DPHtmlGenerator(output_dir=exp_config.results_dir)
            generator.generate_individual_dashboard(results=results, experiment_name=exp_config.group_display_name)
        except Exception as exc:
            logger.error("Failed to generate individual report for %s: %s", exp_config.experiment_id, exc)

    def _call_in_group_report_generator(self, group_key: str, group_results: List[Dict[str, Any]]) -> None:
        if not self.report_cfg.get("in_group_comparisons", True):
            return
        try:
            from experiments.utils.dp_html_generator import DPHtmlGenerator  # type: ignore
        except ImportError:
            try:
                from dp_html_generator import DPHtmlGenerator  # type: ignore
            except ImportError:
                logger.warning("HTML generator not available; skipping in-group report.")
                return
        successful = [res for res in group_results if res.get("status") == "success"]
        if not successful:
            logger.warning("Skipping in-group report for %s: no successful experiments.", group_key)
            return
        display_name = (
            self.config.get("experiment_directories", {})
            .get(group_key, {})
            .get("display_name", group_key)
        )
        output_dir = self.results_base_dir / group_key / "in_group_comparison"
        try:
            generator = DPHtmlGenerator(output_dir=output_dir)
            generator.generate_in_group_comparison(group_results=successful, group_name=display_name)
        except Exception as exc:
            logger.error("Failed to generate in-group report for %s: %s", group_key, exc)

    def _call_cross_group_report_generator(self) -> None:
        if not self.report_cfg.get("cross_group_comparisons", True):
            return
        try:
            from experiments.utils.dp_html_generator import DPHtmlGenerator  # type: ignore
        except ImportError:
            try:
                from dp_html_generator import DPHtmlGenerator  # type: ignore
            except ImportError:
                logger.warning("HTML generator not available; skipping cross-group report.")
                return
        try:
            output_dir = self.results_base_dir / "cross_group_comparison"
            generator = DPHtmlGenerator(output_dir=output_dir)
            generator.generate_cross_group_comparison(all_results=self.group_results)
        except Exception as exc:
            logger.error("Failed to generate cross-group report: %s", exc)

    # -------------------------------------------------------------- execution
    def _run_syneval_experiment(self, exp_config: ExperimentConfig) -> Dict[str, Any]:
        logger.info("Running DP experiment %s", exp_config.experiment_id)

        valid, missing = self._validate_experiment_files(exp_config)
        if not valid:
            error_msg = f"Missing required files: {', '.join(missing)}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg, "experiment_id": exp_config.experiment_id}

        try:
            train_data, test_data, synthetic_data = self._load_data(exp_config)
        except Exception as exc:
            logger.error("Data loading failed for %s: %s", exp_config.experiment_id, exc)
            return {"status": "failed", "error": str(exc), "experiment_id": exp_config.experiment_id}

        real_data = pd.concat([train_data, test_data], ignore_index=True)

        if self.max_privacy_rows and self.max_privacy_rows > 0:
            if len(real_data) > self.max_privacy_rows:
                real_data = real_data.sample(n=self.max_privacy_rows, random_state=42).reset_index(drop=True)
            if len(synthetic_data) > self.max_privacy_rows:
                synthetic_data = (
                    synthetic_data.sample(n=self.max_privacy_rows, random_state=42).reset_index(drop=True)
                )

        metadata = self._generate_metadata(real_data)
        metadata_path = exp_config.results_dir / "metadata.json"
        with open(metadata_path, "w") as handle:
            json.dump(metadata, handle, indent=2)

        from run import SynEval  # Deferred import to avoid circular dependencies on startup.

        device = self.execution_cfg.get("device", "auto")
        syneval = SynEval(synthetic_data, real_data, metadata, device=device)

        results: Dict[str, Any] = {
            "experiment_id": exp_config.experiment_id,
            "group": exp_config.group_key,
            "group_display_name": exp_config.group_display_name,
            "epsilon": exp_config.epsilon,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        failure = False
        experiments_cfg = self.syneval_experiments_cfg

        if experiments_cfg.get("fidelity", {}).get("enabled", False):
            logger.info("  Running fidelity evaluation...")
            try:
                results["fidelity"] = syneval.evaluate_fidelity()
            except Exception as exc:
                logger.error("  Fidelity evaluation failed: %s", exc)
                results["fidelity"] = {"status": "failed", "error": str(exc)}
                failure = True

        if experiments_cfg.get("utility", {}).get("enabled", False):
            logger.info("  Running utility evaluation...")
            try:
                input_cols = [col for col in self.utility_input_columns if col in real_data.columns]
                if not input_cols:
                    raise ValueError("Configured utility input columns not present in dataset.")
                output_cols = [self.utility_target_column] if self.utility_target_column else []
                results["utility"] = syneval.evaluate_utility(
                    input_columns=input_cols,
                    output_columns=output_cols,
                    selected_metrics=self.utility_selected_metrics,
                    real_train_data=train_data,
                    real_test_data=test_data,
                )
            except Exception as exc:
                logger.error("  Utility evaluation failed: %s", exc)
                results["utility"] = {"status": "failed", "error": str(exc)}
                failure = True

        if experiments_cfg.get("privacy", {}).get("enabled", False):
            logger.info("  Running privacy evaluation...")
            privacy_metrics = ["exact_matches", "tabular_privacy", "text_privacy"]
            if self.mia_config.get("use_privacy_module_mia", False):
                privacy_metrics.insert(1, "membership_inference")
            if self.skip_privacy_anonymeter:
                logger.info("  Skipping anonymeter metrics per configuration.")
            else:
                privacy_metrics.append("anonymeter")
            try:
                results["privacy"] = syneval.evaluate_privacy(selected_metrics=privacy_metrics)
            except Exception as exc:
                logger.error("  Privacy evaluation failed: %s", exc)
                results["privacy"] = {"status": "failed", "error": str(exc), "selected_metrics": privacy_metrics}
                failure = True

        if experiments_cfg.get("diversity", {}).get("enabled", False):
            logger.info("  Running diversity evaluation...")
            try:
                results["diversity"] = syneval.evaluate_diversity()
            except Exception as exc:
                logger.error("  Diversity evaluation failed: %s", exc)
                results["diversity"] = {"status": "failed", "error": str(exc)}
                failure = True

        if experiments_cfg.get("mia", {}).get("enabled", False):
            logger.info("  Running membership inference attack (tabular fallback)...")
            try:
                from experiments.utils.membership_inference import run_mia_for_experiment
            except ImportError as exc:
                logger.warning("  Membership inference module unavailable: %s", exc)
                results["mia"] = {"status": "failed", "error": "membership_inference module not available"}
                failure = True
            else:
                try:
                    n_shadow = int(self.mia_config.get("n_shadow", 1000))
                    dataset_name = exp_config.dataset_name or self.mia_config.get("dataset")
                    adapter_name = exp_config.mia_adapter or self.mia_config.get("adapter")
                    model_path = exp_config.model_path if exp_config.model_path and exp_config.model_path.exists() else None
                    mia_results = run_mia_for_experiment(
                        model_path=model_path,
                        train_data_path=self._resolve_path(exp_config.train_data_path),
                        test_data_path=self._resolve_path(exp_config.test_data_path),
                        n_shadow=n_shadow,
                        dataset_name=dataset_name,
                        schedule_path=model_path,
                        adapter_name=adapter_name,
                    )
                    results["mia"] = mia_results
                    if isinstance(mia_results, dict):
                        status = mia_results.get("status", "unknown")
                        if status == "success":
                            logger.info(
                                "  MIA completed successfully: AUC=%s, mode=%s",
                                mia_results.get("auc"),
                                mia_results.get("attack_mode"),
                            )
                        elif status == "fallback":
                            logger.info("  MIA fallback used (model not loaded).")
                        else:
                            logger.warning(
                                "  MIA reported status=%s details=%s",
                                status,
                                mia_results.get("error") or mia_results.get("notes"),
                            )
                    else:
                        logger.warning("  Unexpected MIA result type: %s", type(mia_results))
                except Exception as exc:
                    logger.error("  Membership inference attack failed: %s", exc)
                    results["mia"] = {"status": "failed", "error": str(exc)}
                    failure = True

        results["status"] = "failed" if failure else "success"

        results_path = exp_config.results_dir / "results.json"
        with open(results_path, "w") as handle:
            json.dump(_convert_numpy_for_json(results), handle, indent=2)

        if results["status"] == "success":
            self._call_individual_report_generator(exp_config, results)

        return results

    def run_sequential(self) -> None:
        experiment_configs = self._generate_experiment_configs()
        total = len(experiment_configs)
        logger.info("Starting sequential execution for %d DP experiments.", total)

        for idx, exp_config in enumerate(experiment_configs, start=1):
            logger.info("[%d/%d] Executing %s", idx, total, exp_config.experiment_id)
            results = self._run_syneval_experiment(exp_config)
            self.all_results[exp_config.experiment_id] = results
            self.group_results.setdefault(exp_config.group_key, []).append(results)

        for group_key, group_results in self.group_results.items():
            self._call_in_group_report_generator(group_key, group_results)
        self._call_cross_group_report_generator()

    def run_parallel(self, max_workers: Optional[int] = None) -> None:
        experiment_configs = self._generate_experiment_configs()
        if not experiment_configs:
            logger.warning("No experiments configured; exiting.")
            return

        workers = max_workers or self.execution_cfg.get("parallel_workers", 4)
        logger.info(
            "Starting parallel execution for %d DP experiments with %d workers.",
            len(experiment_configs),
            workers,
        )

        fallback_needed = False
        fallback_configs: List[ExperimentConfig] = []

        try:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                future_to_config = {
                    executor.submit(self._run_syneval_experiment, cfg): cfg for cfg in experiment_configs
                }
                completed = 0
                while future_to_config:
                    future = next(as_completed(future_to_config))
                    exp_config = future_to_config.pop(future)
                    try:
                        results = future.result()
                        completed += 1
                        logger.info("[%d/%d] Completed %s", completed, len(experiment_configs), exp_config.experiment_id)
                        self.all_results[exp_config.experiment_id] = results
                        self.group_results.setdefault(exp_config.group_key, []).append(results)
                    except BrokenProcessPool as exc:
                        logger.error(
                            "Parallel worker crashed while processing %s: %s",
                            exp_config.experiment_id,
                            exc,
                        )
                        pending = [exp_config] + list(future_to_config.values())
                        fallback_configs = self._dedupe_configs(pending)
                        fallback_needed = True
                        break
                    except Exception as exc:
                        logger.error("Experiment %s failed: %s", exp_config.experiment_id, exc)
                        if not self.execution_cfg.get("continue_on_error", True):
                            raise
                else:
                    fallback_needed = False
        except BrokenProcessPool as exc:
            logger.error("Parallel execution failed: %s", exc)
            fallback_configs = self._dedupe_configs(fallback_configs or experiment_configs)
            fallback_needed = True

        if fallback_needed:
            fallback_configs = [cfg for cfg in fallback_configs if cfg.experiment_id not in self.all_results]
            if fallback_configs:
                logger.warning(
                    "Falling back to sequential execution for %d DP experiments.",
                    len(fallback_configs),
                )
                for cfg in fallback_configs:
                    results = self._run_syneval_experiment(cfg)
                    self.all_results[cfg.experiment_id] = results
                    self.group_results.setdefault(cfg.group_key, []).append(results)

        for group_key, group_results in self.group_results.items():
            self._call_in_group_report_generator(group_key, group_results)
        self._call_cross_group_report_generator()

    @staticmethod
    def _dedupe_configs(configs: List[ExperimentConfig]) -> List[ExperimentConfig]:
        seen: Dict[str, ExperimentConfig] = {}
        for cfg in configs:
            seen.setdefault(cfg.experiment_id, cfg)
        return list(seen.values())

    def save_summary(self) -> None:
        summary_path = self.results_base_dir / "execution_summary.json"
        unique_groups = list(self.group_results.keys())
        unique_epsilons = sorted(
            {res.get("epsilon") for res in self.all_results.values() if res.get("epsilon") is not None}
        )

        summary = {
            "timestamp": datetime.now().isoformat(),
            "config_path": str(self.config_path),
            "total_experiments": len(self.all_results),
            "successful": sum(1 for res in self.all_results.values() if res.get("status") == "success"),
            "failed": sum(1 for res in self.all_results.values() if res.get("status") == "failed"),
            "groups": unique_groups,
            "epsilons": unique_epsilons,
            "results": self.all_results,
        }

        with open(summary_path, "w") as handle:
            json.dump(_convert_numpy_for_json(summary), handle, indent=2)

        logger.info("Execution summary saved to %s", summary_path)
        print("\n" + "=" * 60)
        print("DP EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total experiments: {summary['total_experiments']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Summary saved to: {summary_path}")
        print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DP evaluation experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/cross_group_dp.yaml",
        help="Path to DP evaluation configuration file",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run experiments in parallel",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (used with --parallel)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    runner = DPEvaluationRunner(config_path=args.config)

    if args.parallel:
        runner.run_parallel(max_workers=args.workers)
    else:
        runner.run_sequential()

    runner.save_summary()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        logger.error("Execution failed: %s\n%s", exc, traceback.format_exc())
        sys.exit(1)
