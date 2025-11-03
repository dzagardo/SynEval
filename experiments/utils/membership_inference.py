"""Membership inference attack orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from experiments.mia_adapters import build_adapter, MIABaseAdapter

logger = logging.getLogger(__name__)


class MembershipInferenceAttack:
    """Orchestrates the membership inference pipeline."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        dataset_name: Optional[str] = None,
        schedule_path: Optional[Path] = None,
        adapter_name: Optional[str] = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.schedule_path = Path(schedule_path) if schedule_path else None
        self.dataset_name = dataset_name
        self.model_loaded = False

        self.device = None
        self._torch_available = self._check_torch()

        self.adapter: Optional[MIABaseAdapter] = build_adapter(adapter_name, dataset_name)
        if self.adapter and self._torch_available:
            self.adapter.device = self.device  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ helpers
    def _check_torch(self) -> bool:
        try:
            import torch

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            return True
        except ImportError:
            logger.warning("PyTorch not available; falling back to statistical attack")
            return False

    # ------------------------------------------------------------------ lifecycle
    def load_model(self, model_path: Optional[Path] = None) -> bool:
        if model_path:
            self.model_path = Path(model_path)

        if not self.adapter or not self._torch_available:
            self.model_loaded = False
            return False

        try:
            self.model_loaded = bool(self.adapter.load_model(self.model_path, self.schedule_path))
            return self.model_loaded
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Adapter model load failed: %s", exc)
            self.model_loaded = False
            return False

    # ---------------------------------------------------------------- dataset io
    def prepare_attack_data(
        self,
        train_path: Path,
        test_path: Path,
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self.adapter:
            try:
                return self.adapter.load_datasets(train_path, test_path)
            except Exception as exc:
                logger.error("Adapter dataset load failed: %s", exc)

        train_data = self._load_generic_data(train_path)
        test_data = self._load_generic_data(test_path)
        train_flat, test_flat = self._prepare_attack_arrays(train_data, test_data)
        return train_flat, test_flat

    # ----------------------------------------------------------------- run logic
    def compute_loss_dict(self, batch: np.ndarray) -> Dict[str, np.ndarray]:
        if self.adapter and self._torch_available:
            try:
                losses = self.adapter.compute_losses(batch)
                if losses and "total_loss" in losses:
                    return losses
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Adapter loss computation failed: %s", exc)

        return {"total_loss": self._compute_statistical_losses(batch)}

    def compute_gradient_dict(self, batch: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        if self.adapter and self._torch_available and self.adapter.supports_gradients():
            try:
                gradients = self.adapter.compute_gradients(batch)
                if gradients:
                    return gradients
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Adapter gradient computation failed: %s", exc)
        return None

    def run_attack(
        self,
        train_data: Union[np.ndarray, pd.DataFrame],
        test_data: Union[np.ndarray, pd.DataFrame],
        n_shadow: int = 1000,
    ) -> Dict:
        logger.info("Running Membership Inference Attack...")

        train_array, test_array = self._prepare_attack_arrays(train_data, test_data)
        if train_array.ndim == 0 or test_array.ndim == 0:
            raise ValueError("Train/Test data for MIA must contain at least one sample.")

        rng = np.random.default_rng(42)
        train_array = train_array.astype(np.float64, copy=False)
        test_array = test_array.astype(np.float64, copy=False)

        attack_samples = min(n_shadow, len(train_array), len(test_array))
        if attack_samples < 10:
            raise ValueError("Not enough samples to run membership inference attack.")

        train_indices = rng.choice(len(train_array), attack_samples, replace=False)
        test_indices = rng.choice(len(test_array), attack_samples, replace=False)
        train_subset = train_array[train_indices]
        test_subset = test_array[test_indices]

        train_loss_dict = self.compute_loss_dict(train_subset)
        test_loss_dict = self.compute_loss_dict(test_subset)

        train_losses = train_loss_dict.get("total_loss")
        test_losses = test_loss_dict.get("total_loss")

        component_keys = sorted(k for k in train_loss_dict.keys() if k != "total_loss")
        train_feature_cols: List[np.ndarray] = [train_losses.reshape(-1, 1)]
        test_feature_cols: List[np.ndarray] = [test_losses.reshape(-1, 1)]

        for key in component_keys:
            train_feature_cols.append(train_loss_dict[key].reshape(-1, 1))
            column = test_loss_dict.get(key, test_losses)
            test_feature_cols.append(column.reshape(-1, 1))

        gradient_used = False
        if self.adapter and self.adapter.supports_gradients():
            train_grad_dict = self.compute_gradient_dict(train_subset)
            test_grad_dict = self.compute_gradient_dict(test_subset)
            if train_grad_dict and test_grad_dict:
                common_grad_keys = sorted(set(train_grad_dict.keys()) & set(test_grad_dict.keys()))
                for key in common_grad_keys:
                    train_vals = train_grad_dict.get(key)
                    test_vals = test_grad_dict.get(key)
                    if train_vals is None or test_vals is None:
                        continue

                    train_vals = np.asarray(train_vals)
                    test_vals = np.asarray(test_vals)

                    if train_vals.shape != test_vals.shape:
                        logger.warning(
                            "Gradient feature '%s' has mismatched shapes (%s vs %s); skipping.",
                            key,
                            train_vals.shape,
                            test_vals.shape,
                        )
                        continue

                    if train_vals.ndim == 1:
                        train_feature_cols.append(train_vals.reshape(-1, 1))
                        test_feature_cols.append(test_vals.reshape(-1, 1))
                        gradient_used = True
                    elif train_vals.ndim == 2:
                        for col_idx in range(train_vals.shape[1]):
                            train_feature_cols.append(train_vals[:, col_idx].reshape(-1, 1))
                            test_feature_cols.append(test_vals[:, col_idx].reshape(-1, 1))
                        gradient_used = True
                    else:
                        flat_train = train_vals.reshape(train_vals.shape[0], -1)
                        flat_test = test_vals.reshape(test_vals.shape[0], -1)
                        train_feature_cols.append(flat_train)
                        test_feature_cols.append(flat_test)
                        gradient_used = True

        train_features = np.hstack(train_feature_cols)
        test_features = np.hstack(test_feature_cols)

        X = np.vstack([train_features, test_features])
        y = np.concatenate([np.ones(len(train_features)), np.zeros(len(test_features))])

        clf = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "logreg",
                    LogisticRegression(
                        random_state=42,
                        max_iter=2000,
                        class_weight="balanced",
                    ),
                ),
            ]
        )

        n_splits = min(5, len(y) // 2)
        n_splits = max(2, n_splits)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc")

        clf.fit(X, y)
        y_proba = clf.predict_proba(X)[:, 1]
        y_pred = clf.predict(X)

        auc = roc_auc_score(y, y_proba)
        accuracy = accuracy_score(y, y_pred)
        precision = precision_score(y, y_pred, zero_division=0)
        recall = recall_score(y, y_pred, zero_division=0)
        f1 = f1_score(y, y_pred, zero_division=0)
        bal_acc = balanced_accuracy_score(y, y_pred)
        ci_95 = 1.96 * cv_scores.std()

        majority_baseline = 0.5
        collapse_detected = accuracy <= majority_baseline + 1e-6 or np.isclose(accuracy, majority_baseline)
        collapse_reason = None
        if collapse_detected:
            collapse_reason = (
                "Attack classifier failed to beat majority baseline; predictions collapse to a single class."
            )
            logger.warning("Attack collapse detected: accuracy %.4f vs baseline %.4f", accuracy, majority_baseline)

        if self.model_loaded:
            attack_mode = "adapter_model"
            reliability = "high"
        else:
            attack_mode = "statistical_fallback"
            reliability = "very_low"

        results = {
            "auc": float(auc),
            "accuracy": float(accuracy),
            "balanced_accuracy": float(bal_acc),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "ci_95_lower": float(max(0, auc - ci_95)),
            "ci_95_upper": float(min(1, auc + ci_95)),
            "cv_auc_mean": float(cv_scores.mean()),
            "cv_auc_std": float(cv_scores.std()),
            "train_loss_mean": float(train_losses.mean()),
            "train_loss_std": float(train_losses.std()),
            "test_loss_mean": float(test_losses.mean()),
            "test_loss_std": float(test_losses.std()),
            "n_train": int(len(train_losses)),
            "n_test": int(len(test_losses)),
            "shadow_samples": int(attack_samples * 2),
            "model_path": str(self.model_path) if self.model_path else None,
            "attack_mode": attack_mode,
            "collapse_detected": bool(collapse_detected),
            "collapse_reason": collapse_reason,
            "majority_baseline_accuracy": float(majority_baseline),
            "attack_reliability": "low" if collapse_detected else reliability,
            "model_loaded": bool(self.model_loaded),
            "fallback_used": not self.model_loaded,
            "gradients_used": bool(gradient_used),
        }

        component_keys.sort()
        for key in component_keys:
            results[f"train_{key}_mean"] = float(train_loss_dict[key].mean())
            results[f"train_{key}_std"] = float(train_loss_dict[key].std())
            if key in test_loss_dict:
                results[f"test_{key}_mean"] = float(test_loss_dict[key].mean())
                results[f"test_{key}_std"] = float(test_loss_dict[key].std())

        if collapse_detected:
            logger.warning("Attack reliability degraded; treat privacy risk signal with caution.")
            results["privacy_risk_level"] = "indeterminate"
        elif not self.model_loaded:
            logger.info(
                "Membership inference fallback used (no model checkpoint). Treat privacy risk estimate as unknown. AUC=%.4f",
                auc,
            )
            results["privacy_risk_level"] = "unknown"
            results["attack_reliability"] = "very_low"
            results["notes"] = (
                "Model checkpoint unavailable; using statistical fallback features only. "
                "Privacy risk estimate should be treated as informational."
            )
        elif auc > 0.6:
            logger.warning("Privacy concern: model may have memorized training data")
            results["privacy_risk_level"] = "high"
        elif auc < 0.55:
            logger.info("Good privacy: model shows little memorization")
            results["privacy_risk_level"] = "low"
        else:
            logger.info("Moderate privacy: some potential memorization")
            results["privacy_risk_level"] = "medium"

        if gradient_used:
            logger.info("MIA feature set includes gradient-derived signals.")

        return results

    # ------------------------------------------------------------- generic util
    def _load_generic_data(self, path: Path):
        if path.suffix == ".csv":
            return pd.read_csv(path)
        if path.suffix == ".npy":
            arr = np.load(path, allow_pickle=True)
            if arr.ndim == 3:
                arr = arr.reshape(-1, arr.shape[-1])
            return arr
        raise ValueError(f"Unsupported data format: {path}")

    def _prepare_attack_arrays(
        self,
        train_data: Union[np.ndarray, pd.DataFrame],
        test_data: Union[np.ndarray, pd.DataFrame],
    ) -> Tuple[np.ndarray, np.ndarray]:
        if isinstance(train_data, pd.DataFrame) and isinstance(test_data, pd.DataFrame):
            combined = pd.concat([train_data, test_data], axis=0, ignore_index=True)
            combined = combined.replace([np.inf, -np.inf], np.nan)
            combined = combined.fillna(0.0)
            train_encoded = combined.iloc[: len(train_data)].to_numpy(dtype=np.float64, copy=False)
            test_encoded = combined.iloc[len(train_data) :].to_numpy(dtype=np.float64, copy=False)
            return train_encoded, test_encoded

        def _to_numeric(data: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
            if isinstance(data, pd.DataFrame):
                numeric = data.select_dtypes(include=[np.number]).copy()
                numeric = numeric.replace([np.inf, -np.inf], np.nan).fillna(0.0)
                return numeric.to_numpy(dtype=np.float64, copy=False)
            array = np.asarray(data, dtype=np.float64)
            if array.ndim == 1:
                array = array.reshape(array.shape[0], 1)
            return np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0)

        train_array = _to_numeric(train_data)
        test_array = _to_numeric(test_data)
        return train_array, test_array

    def _compute_statistical_losses(self, data: np.ndarray) -> np.ndarray:
        n_samples = len(data)
        losses = np.zeros(n_samples)
        for i in range(n_samples):
            sample = data[i].flatten()
            mean_val = np.mean(sample)
            std_val = np.std(sample)
            range_val = np.ptp(sample)
            losses[i] = std_val + 0.1 * abs(mean_val) + 0.05 * range_val
        return losses


def run_mia_for_experiment(
    model_path: Optional[Path],
    train_data_path: Path,
    test_data_path: Path,
    n_shadow: int = 1000,
    dataset_name: Optional[str] = None,
    schedule_path: Optional[Path] = None,
    adapter_name: Optional[str] = None,
) -> Dict:
    if not train_data_path.exists():
        error_msg = f"Training data not found: {train_data_path}"
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg}

    if not test_data_path.exists():
        error_msg = f"Test data not found: {test_data_path}"
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg}

    attack = MembershipInferenceAttack(
        model_path=model_path,
        dataset_name=dataset_name,
        schedule_path=schedule_path,
        adapter_name=adapter_name,
    )

    model_loaded = attack.load_model()
    if not model_loaded:
        logger.warning("Proceeding with statistical fallback for MIA (no model loaded)")

    train_data, test_data = attack.prepare_attack_data(train_data_path, test_data_path)
    results = attack.run_attack(train_data, test_data, n_shadow)
    if attack.model_loaded:
        results.setdefault("status", "success")
    else:
        results.setdefault("status", "fallback")
        results.setdefault(
            "notes",
            "Membership inference used statistical fallback because the model checkpoint could not be loaded.",
        )
    return results
