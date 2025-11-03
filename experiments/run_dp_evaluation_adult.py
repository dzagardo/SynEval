#!/usr/bin/env python3
"""
Differential Privacy Evaluation Runner tailored for the Adult Income dataset.
This script mirrors the functionality of the generic DP runner while adapting
path resolution, metadata handling, and utility configuration to match the new
adult dataset layout (non-windowed CSV files with mixed feature types).
"""

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
import pandas as pd
import yaml

# Add project root to path for imports (SynEval lives one level up from experiments/)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure module-level logging defaults; config can override log file via handlers.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dp_evaluation_adult.log"),
    ],
)
logger = logging.getLogger(__name__)


def _convert_numpy_for_json(obj: Any) -> Any:
    """Convert NumPy objects embedded in dictionaries/lists before JSON dumping."""
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
    """Generate filesystem-friendly identifiers from epsilon labels."""
    return "".join(ch if ch.isalnum() else "_" for ch in raw)


@dataclass
class AdultExperimentConfig:
    """Container for a single Adult DP evaluation variant."""

    group_key: str
    group_display_name: str
    epsilon: str
    delta: Optional[str]
    synthetic_data_path: Path
    train_data_path: Path
    test_data_path: Path
    results_dir: Path
    model_path: Optional[Path] = None
    model_checkpoint: Optional[Path] = None
    schedule_checkpoint: Optional[Path] = None
    model_checkpoint: Optional[Path] = None
    experiment_id: str = field(init=False)

    def __post_init__(self) -> None:
        epsilon_token = _sanitize_identifier(self.epsilon)
        self.experiment_id = f"{self.group_key}_eps{epsilon_token}"


class AdultDPEvaluationRunner:
    """DP evaluation orchestrator specialized for the Adult Income dataset."""

    def __init__(self, config_path: str = "configs/cross_group_dp_adult.yaml") -> None:
        self.project_root = Path(__file__).parent.parent
        self.config_path = self._resolve_path(config_path)
        self.config = self._load_config()

        reporting_cfg = self.config.get("reporting", {})
        results_dir = reporting_cfg.get("reports_output_dir", "reports/dp_evaluation_adult")
        self.results_base_dir = self._resolve_path(results_dir)
        self.results_base_dir.mkdir(parents=True, exist_ok=True)

        exec_cfg = self.config.get("execution", {})
        if exec_cfg.get("enable_cache", False):
            cache_dir = self._resolve_path(exec_cfg.get("cache_dir", "./cache"))
            cache_dir.mkdir(parents=True, exist_ok=True)

        # Constrain BLAS thread count to avoid crashes on large privacy jobs
        openblas_threads = exec_cfg.get("openblas_threads")
        if openblas_threads:
            thread_str = str(openblas_threads)
            os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_str)
            os.environ.setdefault("OMP_NUM_THREADS", thread_str)
            os.environ.setdefault("MKL_NUM_THREADS", thread_str)

        self.skip_privacy_anonymeter = bool(self.config.get("privacy", {}).get("skip_anonymeter", True))
        max_rows = self.config.get("privacy", {}).get("max_rows")
        self.max_privacy_rows: Optional[int] = int(max_rows) if max_rows else None

        real_data_cfg = self.config.get("real_data", {})
        if "train_path" not in real_data_cfg or "test_path" not in real_data_cfg:
            raise ValueError("Config real_data section must include train_path and test_path.")

        self.train_data_path = self._resolve_path(real_data_cfg["train_path"])
        self.test_data_path = self._resolve_path(real_data_cfg["test_path"])
        self.info_json_path = None

        metadata_cfg = self.config.get("metadata", {})
        if metadata_cfg.get("info_json_path"):
            info_path = self._resolve_path(metadata_cfg["info_json_path"])
            if info_path.exists():
                self.info_json_path = info_path

        self.column_overrides = self._load_column_overrides()

        utility_cfg = self.config.get("utility", {})
        self.utility_target_column: Optional[str] = utility_cfg.get("target_column")
        self.utility_input_columns: List[str] = utility_cfg.get("input_columns", [])
        if not self.utility_target_column:
            raise ValueError("utility.target_column must be defined in the config.")
        if not self.utility_input_columns:
            raise ValueError("utility.input_columns must provide at least one feature column.")

        self.syneval_experiments_cfg = self.config.get("syneval_experiments", {})
        self.mia_config = self.config.get("mia", {}) or {}

        # Caches for real data to avoid re-reading on every experiment.
        self._train_cache: Optional[pd.DataFrame] = None
        self._test_cache: Optional[pd.DataFrame] = None

        # Containers for aggregated results.
        self.all_results: Dict[str, Dict] = {}
        self.group_results: Dict[str, List[Dict]] = {}

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _resolve_path(self, path_like: str) -> Path:
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

    def _load_column_overrides(self) -> Dict[str, Dict[str, Any]]:
        """Generate column metadata overrides from the optional info.json."""
        overrides: Dict[str, Dict[str, Any]] = {}
        if not self.info_json_path:
            return overrides

        try:
            with open(self.info_json_path, "r") as handle:
                info = json.load(handle)
        except Exception as exc:
            logger.warning("Failed to parse info.json at %s (%s)", self.info_json_path, exc)
            return overrides

        column_names: List[str] = info.get("column_names", [])
        column_info: Dict[str, Dict[str, Any]] = info.get("column_info", {})
        for idx, name in enumerate(column_names):
            details = column_info.get(str(idx), {})
            col_type = details.get("type", "").lower()
            if col_type == "numerical":
                overrides[name] = {"sdtype": "numerical"}
            elif col_type == "categorical":
                categories = details.get("categorizes")
                if categories:
                    categories = [str(cat).strip() for cat in categories]
                overrides[name] = {"sdtype": "categorical", "categories": categories}
        return overrides

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------
    def _get_train_data(self) -> pd.DataFrame:
        if self._train_cache is None:
            self._train_cache = self._clean_dataframe(pd.read_csv(self.train_data_path))
        return self._train_cache.copy()

    def _get_test_data(self) -> pd.DataFrame:
        if self._test_cache is None:
            self._test_cache = self._clean_dataframe(pd.read_csv(self.test_data_path))
        return self._test_cache.copy()

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace from string columns to keep categorical levels consistent."""
        cleaned = df.copy()
        for col in cleaned.select_dtypes(include=["object"]).columns:
            cleaned[col] = cleaned[col].astype(str).str.strip()
        return cleaned

    def _coerce_numeric_inputs(self, df: pd.DataFrame) -> pd.DataFrame:
        coerced = df.copy()
        for col in self.utility_input_columns:
            if col in coerced.columns:
                coerced[col] = pd.to_numeric(coerced[col], errors="coerce")
        target = self.utility_target_column
        if target and target in coerced.columns:
            coerced[target] = coerced[target].astype(str).str.strip()
        return coerced

    def _generate_experiment_configs(self) -> List[AdultExperimentConfig]:
        experiments: List[AdultExperimentConfig] = []
        group_cfg = self.config.get("experiment_groups", {})

        if not group_cfg:
            raise ValueError("Config must define at least one entry under experiment_groups.")

        for group_key, group_info in group_cfg.items():
            display_name = group_info.get("display_name", group_key)
            group_default_model = group_info.get("mia_model_path")
            if group_default_model:
                group_default_model = self._resolve_path(group_default_model)
            for entry in group_info.get("experiments", []):
                epsilon = str(entry.get("epsilon"))
                delta = entry.get("delta")
                synthetic_path_raw = entry.get("synthetic_path")
                if not synthetic_path_raw:
                    raise ValueError(f"Experiment entry for {group_key}/{epsilon} missing synthetic_path.")
                synthetic_path = self._resolve_path(synthetic_path_raw)

                # Resolve optional MIA model path (entry overrides group default)
                mia_model_raw = entry.get("mia_model_path", group_default_model)
                model_path = None
                if mia_model_raw:
                    model_path = self._resolve_path(mia_model_raw) if not isinstance(mia_model_raw, Path) else mia_model_raw

                # Determine model checkpoints
                variant_dir = synthetic_path.parent
                # The directory immediately under "adult" encodes the DP variant.
                while variant_dir != variant_dir.parent:
                    if variant_dir.parent.name == "adult":
                        break
                    variant_dir = variant_dir.parent
                if variant_dir.parent.name == "adult":
                    variant_name = variant_dir.name
                else:
                    variant_name = synthetic_path.parent.parent.name

                ckpt_dir = self._resolve_path(f"experiments/data_adult/ckpt/adult/{variant_name}")
                if "EMA" in group_key.upper():
                    primary_checkpoint = ckpt_dir / "ema_model_8000.pt"
                    schedule_checkpoint = ckpt_dir / "model_8000.pt"
                else:
                    primary_checkpoint = ckpt_dir / "model_8000.pt"
                    schedule_checkpoint = primary_checkpoint

                safe_eps = _sanitize_identifier(epsilon if epsilon else "unknown")
                if delta:
                    safe_eps = f"{safe_eps}_delta_{_sanitize_identifier(str(delta))}"

                results_dir = self.results_base_dir / group_key / f"eps_{safe_eps}"
                results_dir.mkdir(parents=True, exist_ok=True)

                experiments.append(
                    AdultExperimentConfig(
                        group_key=group_key,
                        group_display_name=display_name,
                        epsilon=epsilon,
                        delta=str(delta) if delta is not None else None,
                        synthetic_data_path=synthetic_path,
                        train_data_path=self.train_data_path,
                        test_data_path=self.test_data_path,
                        model_path=model_path,
                        model_checkpoint=primary_checkpoint,
                        schedule_checkpoint=schedule_checkpoint,
                        results_dir=results_dir,
                    )
                )

        return experiments

    def _validate_experiment_files(self, exp_config: AdultExperimentConfig) -> Tuple[bool, List[str]]:
        if not self.config.get("validation", {}).get("check_files_exist", True):
            return True, []

        missing: List[str] = []
        if not exp_config.synthetic_data_path.exists():
            missing.append(f"Synthetic data: {exp_config.synthetic_data_path}")
        if not exp_config.train_data_path.exists():
            missing.append(f"Train data: {exp_config.train_data_path}")
        if not exp_config.test_data_path.exists():
            missing.append(f"Test data: {exp_config.test_data_path}")
        return (not missing, missing)

    def _load_data(self, exp_config: AdultExperimentConfig) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        synthetic = pd.read_csv(exp_config.synthetic_data_path)
        train = self._get_train_data()
        test = self._get_test_data()

        synthetic = self._clean_dataframe(synthetic)

        expected_columns = train.columns.tolist()
        missing_cols = [col for col in expected_columns if col not in synthetic.columns]
        if missing_cols:
            raise ValueError(
                f"Synthetic data columns missing for {exp_config.experiment_id}: {missing_cols}"
            )
        synthetic = synthetic[expected_columns]

        # Ensure consistent types for utility inputs/targets.
        synthetic = self._coerce_numeric_inputs(synthetic)
        train = self._coerce_numeric_inputs(train)
        test = self._coerce_numeric_inputs(test)

        target = self.utility_target_column
        if target not in synthetic.columns or target not in train.columns or target not in test.columns:
            raise ValueError(f"Target column '{target}' not present in all datasets for {exp_config.experiment_id}.")

        return train, test, synthetic

    def _generate_metadata(self, data: pd.DataFrame) -> Dict[str, Any]:
        metadata = {
            "columns": {},
            "primary_key": None,
            "METADATA_SPEC_VERSION": "1.0",
        }
        for col in data.columns:
            override = self.column_overrides.get(col, {})
            col_meta = dict(override)
            if not col_meta:
                dtype = data[col].dtype
                if pd.api.types.is_numeric_dtype(dtype):
                    col_meta["sdtype"] = "numerical"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    col_meta["sdtype"] = "datetime"
                else:
                    col_meta["sdtype"] = "categorical"

            if col_meta.get("sdtype") == "categorical" and "categories" not in col_meta:
                unique_values = (
                    data[col].dropna().unique().tolist() if not data[col].empty else []
                )
                col_meta["categories"] = [str(val) for val in unique_values][:200]
            metadata["columns"][col] = col_meta
        return metadata

    # ------------------------------------------------------------------
    # Reporting helpers (HTML dashboards)
    # ------------------------------------------------------------------
    def _call_individual_report_generator(self, exp_config: AdultExperimentConfig, results: Dict) -> None:
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
            generator.generate_individual_dashboard(
                results=results,
                experiment_name=exp_config.group_display_name,
            )
        except Exception as exc:
            logger.error("Failed to generate individual report for %s: %s", exp_config.experiment_id, exc)

    def _call_in_group_report_generator(self, group_key: str, group_results: List[Dict]) -> None:
        try:
            from experiments.utils.dp_html_generator import DPHtmlGenerator  # type: ignore
        except ImportError:
            try:
                from dp_html_generator import DPHtmlGenerator  # type: ignore
            except ImportError:
                logger.warning("HTML generator not available; skipping in-group report.")
                return
        display_name = self.config.get("experiment_groups", {}).get(group_key, {}).get(
            "display_name", group_key
        )
        successful = [res for res in group_results if res.get("status") == "success"]
        if not successful:
            logger.warning("Skipping in-group report for %s: no successful experiments.", group_key)
            return
        try:
            output_dir = self.results_base_dir / group_key / "in_group_comparison"
            generator = DPHtmlGenerator(output_dir=output_dir)
            generator.generate_in_group_comparison(group_results=successful, group_name=display_name)
        except Exception as exc:
            logger.error("Failed to generate in-group report for %s: %s", group_key, exc)

    def _call_cross_group_report_generator(self) -> None:
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

    # ------------------------------------------------------------------
    # Experiment execution
    # ------------------------------------------------------------------
    def _run_syneval_experiment(self, exp_config: AdultExperimentConfig) -> Dict[str, Any]:
        logger.info("Running Adult DP experiment %s", exp_config.experiment_id)

        valid, missing = self._validate_experiment_files(exp_config)
        if not valid:
            error_msg = f"Missing required files: {', '.join(missing)}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        train_data, test_data, synthetic_data = self._load_data(exp_config)
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

        from run import SynEval  # Deferred import to avoid circular dependencies during startup.

        device = self.config.get("execution", {}).get("device", "auto")
        syneval = SynEval(synthetic_data, real_data, metadata, device=device)

        results: Dict[str, Any] = {
            "experiment_id": exp_config.experiment_id,
            "group": exp_config.group_key,
            "group_display_name": exp_config.group_display_name,
            "epsilon": exp_config.epsilon,
            "delta": exp_config.delta,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        experiments_cfg = self.syneval_experiments_cfg

        if experiments_cfg.get("fidelity", {}).get("enabled", False):
            logger.info("  Running fidelity evaluation...")
            results["fidelity"] = syneval.evaluate_fidelity()

        if experiments_cfg.get("utility", {}).get("enabled", False):
            logger.info("  Running utility evaluation...")
            input_cols = [col for col in self.utility_input_columns if col in real_data.columns]
            if not input_cols:
                raise ValueError("Configured utility input columns not present in dataset.")
            output_cols = [self.utility_target_column]
            results["utility"] = syneval.evaluate_utility(
                input_columns=input_cols,
                output_columns=output_cols,
                real_train_data=train_data,
                real_test_data=test_data,
            )

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

        if experiments_cfg.get("diversity", {}).get("enabled", False):
            logger.info("  Running diversity evaluation...")
            results["diversity"] = syneval.evaluate_diversity()

        if experiments_cfg.get("mia", {}).get("enabled", False):
            logger.info("  Running membership inference attack (tabular fallback)...")
            try:
                from experiments.utils.membership_inference import (
                    run_mia_for_experiment,
                )
            except ImportError as exc:
                logger.warning("  Membership inference module unavailable: %s", exc)
                results["mia"] = {
                    "status": "failed",
                    "error": "membership_inference module not available",
                }
            else:
                try:
                    n_shadow = int(self.mia_config.get("n_shadow", 1000))
                    mia_results = run_mia_for_experiment(
                        model_path=exp_config.model_checkpoint,
                        schedule_path=exp_config.schedule_checkpoint,
                        train_data_path=exp_config.train_data_path,
                        test_data_path=exp_config.test_data_path,
                        n_shadow=n_shadow,
                        dataset_name=self.mia_config.get("dataset", "adult"),
                        adapter_name=self.mia_config.get("adapter"),
                    )
                    results["mia"] = mia_results
                    if isinstance(mia_results, dict):
                        status = mia_results.get("status", "unknown")
                        attack_mode = mia_results.get("attack_mode")
                        auc = mia_results.get("auc")
                        reliability = mia_results.get("attack_reliability")
                        risk_level = mia_results.get("privacy_risk_level")
                        if status == "fallback":
                            logger.info(
                                "  MIA fallback used (no model loaded). attack_mode=%s, reliability=%s, notes=%s",
                                attack_mode,
                                reliability,
                                mia_results.get("notes"),
                            )
                        elif status == "success":
                            logger.info(
                                "  MIA completed successfully: AUC=%.4f, mode=%s, reliability=%s, risk=%s",
                                float(auc) if isinstance(auc, (int, float)) else float("nan"),
                                attack_mode,
                                reliability,
                                risk_level,
                            )
                        else:
                            logger.warning(
                                "  MIA status=%s; details: %s",
                                status,
                                mia_results.get("error") or mia_results.get("notes"),
                            )
                except Exception as exc:
                    logger.error("  Membership inference attack failed: %s", exc)
                    results["mia"] = {"status": "failed", "error": str(exc)}

        results_path = exp_config.results_dir / "results.json"
        with open(results_path, "w") as handle:
            json.dump(_convert_numpy_for_json(results), handle, indent=2)

        self._call_individual_report_generator(exp_config, results)

        return results

    def run_sequential(self) -> None:
        experiment_configs = self._generate_experiment_configs()
        total = len(experiment_configs)
        logger.info("Starting sequential execution for %d Adult DP experiments.", total)

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
        workers = max_workers or self.config.get("execution", {}).get("parallel_workers", 4)
        logger.info(
            "Starting parallel execution for %d Adult DP experiments with %d workers.",
            len(experiment_configs),
            workers,
        )

        fallback_needed = False
        fallback_configs: List[AdultExperimentConfig] = []

        try:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                future_to_config = {
                    executor.submit(self._run_syneval_experiment, cfg): cfg
                    for cfg in experiment_configs
                }
                completed = 0
                while future_to_config:
                    future = next(as_completed(future_to_config))
                    exp_config = future_to_config.pop(future)
                    try:
                        results = future.result()
                        completed += 1
                        logger.info(
                            "[%d/%d] Completed %s",
                            completed,
                            len(experiment_configs),
                            exp_config.experiment_id,
                        )
                        self.all_results[exp_config.experiment_id] = results
                        self.group_results.setdefault(exp_config.group_key, []).append(results)
                    except BrokenProcessPool as exc:
                        logger.error(
                            "Parallel worker crashed while processing %s: %s",
                            exp_config.experiment_id,
                            exc,
                        )
                        # Collect remaining configurations (including this one and queued ones)
                        pending = [exp_config] + list(future_to_config.values())
                        fallback_configs = self._dedupe_configs(pending)
                        fallback_needed = True
                        break
                    except Exception as exc:
                        logger.error("Experiment %s failed: %s", exp_config.experiment_id, exc)
                        if not self.config.get("execution", {}).get("continue_on_error", True):
                            raise
                else:
                    fallback_needed = False
        except BrokenProcessPool as exc:
            logger.error("Parallel execution failed: %s", exc)
            fallback_configs = self._dedupe_configs(fallback_configs or experiment_configs)
            fallback_needed = True

        if fallback_needed:
            # Exclude any configs that already completed successfully
            fallback_configs = [cfg for cfg in fallback_configs if cfg.experiment_id not in self.all_results]
            if fallback_configs:
                logger.warning(
                    "Falling back to sequential execution for %d Adult DP experiments.",
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
    def _dedupe_configs(configs: List[AdultExperimentConfig]) -> List[AdultExperimentConfig]:
        seen: Dict[str, AdultExperimentConfig] = {}
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
        print("ADULT DP EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total experiments: {summary['total_experiments']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Summary saved to: {summary_path}")
        print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Adult DP evaluation experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/cross_group_dp_adult.yaml",
        help="Path to Adult DP configuration file",
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
        help="Number of parallel workers (only used with --parallel)",
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

    runner = AdultDPEvaluationRunner(config_path=args.config)

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
