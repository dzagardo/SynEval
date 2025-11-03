"""Adapters for dataset-specific membership inference logic."""

from __future__ import annotations

import json
import sys
import types
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List

import numpy as np
import pandas as pd
import torch


class MIABaseAdapter(ABC):
    """Abstract adapter interface for dataset/model specific MIA logic."""

    def __init__(self, dataset_name: Optional[str] = None):
        self.dataset_name = dataset_name or ""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Public API -----------------------------------------------------------------
    def load_model(
        self,
        model_path: Optional[Path],
        schedule_path: Optional[Path],
    ) -> bool:
        """Load the underlying model. Returns True on success."""
        return False

    def load_datasets(
        self,
        train_path: Path,
        test_path: Path,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return flattened train/test arrays ready for the attack."""
        raise NotImplementedError

    @abstractmethod
    def compute_losses(
        self,
        batch: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Compute per-sample losses for the provided batch."""

    # Optional hooks -------------------------------------------------------------
    def supports_gradients(self) -> bool:
        return False

    def compute_gradients(
        self,
        batch: np.ndarray,
    ) -> Optional[Dict[str, np.ndarray]]:
        """Return per-sample gradient summaries (e.g., L2 norms)."""
        return None

    def clean_up(self) -> None:
        pass


class TabDiffAdapter(MIABaseAdapter):
    """Adapter for TabDiff tabular diffusion models (MC_TABDIFF deployment)."""

    def __init__(self, dataset_name: Optional[str] = None):
        super().__init__(dataset_name or "adult")
        self.tabdiff_model = None
        self.d_numerical = 0
        self.categories: List[int] = []
        self._attack_cache: Dict[str, Dict[str, np.ndarray]] = {}
        self.schedule_path: Optional[Path] = None

    # dependency helpers --------------------------------------------------------
    def _ensure_dependencies(self, tabdiff_root: Path) -> None:
        if str(tabdiff_root) not in sys.path:
            sys.path.append(str(tabdiff_root))
        tabdiff_dp_root = tabdiff_root / "tabdiff_dp"
        if tabdiff_dp_root.exists() and str(tabdiff_dp_root) not in sys.path:
            sys.path.append(str(tabdiff_dp_root))

        if "icecream" not in sys.modules:
            module = types.ModuleType("icecream")
            module.install = lambda *args, **kwargs: None
            sys.modules["icecream"] = module

        if "category_encoders" not in sys.modules:
            module = types.ModuleType("category_encoders")

            class LeaveOneOutEncoder:
                def __init__(self, *args, **kwargs):
                    pass

                def fit(self, X, y=None):
                    return self

                def transform(self, X):
                    return X

            module.LeaveOneOutEncoder = LeaveOneOutEncoder
            sys.modules["category_encoders"] = module

        if "tomli" not in sys.modules:
            module = types.ModuleType("tomli")
            try:
                import tomllib as _tomllib  # type: ignore[attr-defined]

                module.load = lambda fp: _tomllib.load(fp)
                module.loads = lambda s: _tomllib.loads(s)
            except Exception:
                module.load = lambda fp: {}
                module.loads = lambda s: {}
            sys.modules["tomli"] = module

        if "tomli_w" not in sys.modules:
            module = types.ModuleType("tomli_w")
            module.dump = lambda *args, **kwargs: None
            module.dumps = lambda *args, **kwargs: ""
            sys.modules["tomli_w"] = module

        if "einops" not in sys.modules:
            import torch

            def _parse(pattern: str) -> Tuple[List[str], List[str]]:
                left, right = pattern.split("->")
                left_syms = [tok for tok in left.strip().split(" ") if tok]
                right_syms = [tok for tok in right.strip().split(" ") if tok]
                return left_syms, right_syms

            def rearrange(tensor: torch.Tensor, pattern: str, **axes_lengths) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                if result.dim() != len(axis_labels):
                    raise ValueError(f"Pattern {pattern} does not match tensor rank {result.dim()}")
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                        axis_labels.insert(idx, f"__axis_{idx}")
                    else:
                        if sym not in axis_labels:
                            raise ValueError(f"Unknown axis symbol '{sym}' in pattern '{pattern}'")
                        current = axis_labels.index(sym)
                        if current != idx:
                            result = result.movedim(current, idx)
                            axis_labels.insert(idx, axis_labels.pop(current))
                return result

            def reduce(tensor: torch.Tensor, pattern: str, reduction: str) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                keep_syms = [sym for sym in right if sym != "()"]
                for sym in list(axis_labels):
                    if sym not in keep_syms:
                        axis = axis_labels.index(sym)
                        if reduction == "sum":
                            result = result.sum(dim=axis, keepdim=False)
                        elif reduction == "mean":
                            result = result.mean(dim=axis, keepdim=False)
                        else:
                            raise ValueError(f"Unsupported reduction '{reduction}'")
                        axis_labels.pop(axis)
                for idx, sym in enumerate(keep_syms):
                    current = axis_labels.index(sym)
                    if current != idx:
                        result = result.movedim(current, idx)
                        axis_labels.insert(idx, axis_labels.pop(current))
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                return result

            def repeat(tensor: torch.Tensor, pattern: str, **axes_lengths) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                if result.dim() != len(axis_labels):
                    raise ValueError(f"Pattern {pattern} does not match tensor rank {result.dim()}")
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                        axis_labels.insert(idx, f"__axis_{idx}")
                    elif sym in axis_labels:
                        current = axis_labels.index(sym)
                        if current != idx:
                            result = result.movedim(current, idx)
                            axis_labels.insert(idx, axis_labels.pop(current))
                    else:
                        size = axes_lengths.get(sym)
                        if size is None:
                            raise ValueError(f"Missing axis length for symbol '{sym}' in repeat pattern '{pattern}'")
                        result = result.unsqueeze(idx)
                        expand_sizes = list(result.shape)
                        expand_sizes[idx] = size
                        result = result.expand(*expand_sizes)
                        axis_labels.insert(idx, sym)
                return result

            module = types.ModuleType("einops")
            module.rearrange = rearrange
            module.reduce = reduce
            module.repeat = repeat
            sys.modules["einops"] = module

    # model loading -------------------------------------------------------------
    def load_model(
        self,
        model_path: Optional[Path],
        schedule_path: Optional[Path],
    ) -> bool:
        if model_path is None or not model_path.exists():
            return False

        tabdiff_root = (Path(__file__).resolve().parent.parent / ".." / "MC_TABDIFF_deployment").resolve()
        if not tabdiff_root.exists():
            return False

        self._ensure_dependencies(tabdiff_root)

        from tabdiff_dp.modules.main_modules import UniModMLP, Model as TabDiffModel  # type: ignore
        from tabdiff_dp.models.unified_ctime_diffusion import UnifiedCtimeDiffusion  # type: ignore

        config_path = model_path.parent / "config.pkl"
        if not config_path.exists():
            return False

        import pickle

        with open(config_path, "rb") as fh:
            config = pickle.load(fh)

        self.d_numerical = int(config["unimodmlp_params"]["d_numerical"])
        config_categories = list(config["unimodmlp_params"]["categories"])
        self.categories = config_categories

        backbone = UniModMLP(**config["unimodmlp_params"])
        base_model = TabDiffModel(backbone, **config["diffusion_params"]["edm_params"])

        diffusion = UnifiedCtimeDiffusion(
            num_classes=np.array(config_categories, dtype=int) - 1,
            num_numerical_features=self.d_numerical,
            denoise_fn=base_model,
            y_only_model=None,
            num_timesteps=config["diffusion_params"]["num_timesteps"],
            scheduler=config["diffusion_params"]["scheduler"],
            cat_scheduler=config["diffusion_params"]["cat_scheduler"],
            noise_dist=config["diffusion_params"]["noise_dist"],
            edm_params=config["diffusion_params"]["edm_params"],
            noise_dist_params=config["diffusion_params"]["noise_dist_params"],
            noise_schedule_params=config["diffusion_params"]["noise_schedule_params"],
            sampler_params=config["diffusion_params"]["sampler_params"],
            device=self.device,
        )

        state = torch.load(model_path, map_location=self.device)

        if isinstance(state, dict) and "denoise_fn" in state:
            diffusion._denoise_fn.load_state_dict(state["denoise_fn"], strict=True)
            if "num_schedule" in state:
                diffusion.num_schedule.load_state_dict(state["num_schedule"], strict=False)
            if "cat_schedule" in state:
                diffusion.cat_schedule.load_state_dict(state["cat_schedule"], strict=False)
        else:
            diffusion._denoise_fn.load_state_dict(state, strict=False)
            schedule_src = schedule_path or (model_path.parent / "model_8000.pt")
            if schedule_src.exists():
                sched_state = torch.load(schedule_src, map_location=self.device)
                if isinstance(sched_state, dict):
                    if "num_schedule" in sched_state:
                        diffusion.num_schedule.load_state_dict(sched_state["num_schedule"], strict=False)
                    if "cat_schedule" in sched_state:
                        diffusion.cat_schedule.load_state_dict(sched_state["cat_schedule"], strict=False)

        diffusion.to(self.device)
        diffusion.eval()

        self.tabdiff_model = diffusion
        return True

    # adult data prep -----------------------------------------------------------
    def load_datasets(
        self,
        train_path: Path,
        test_path: Path,
    ) -> Tuple[np.ndarray, np.ndarray]:
        tabdiff_root = (Path(__file__).resolve().parent.parent / ".." / "MC_TABDIFF_deployment").resolve()
        self._ensure_dependencies(tabdiff_root)

        sys.path.append(str(tabdiff_root))
        from utils_train import preprocess  # type: ignore

        X_num, X_cat, categories, d_numerical = preprocess(
            str(tabdiff_root / "data" / "adult"),
            inverse=False,
        )

        # categories returned without mask class (per dataset)
        categories = np.asarray(categories, dtype=int)

        train_num, test_num = X_num
        train_cat, test_cat = X_cat

        self.d_numerical = d_numerical
        derived_categories = (categories + 1).astype(int).tolist()
        if not self.categories or len(self.categories) != len(derived_categories):
            # include target column (income) as categorical
            self.categories = [int(c + 1) for c in categories]

        train_combined = np.hstack([train_num, train_cat]).astype(np.float32)
        test_combined = np.hstack([test_num, test_cat]).astype(np.float32)

        self._attack_cache = {
            "train": {"combined": train_combined, "num": train_num, "cat": train_cat},
            "test": {"combined": test_combined, "num": test_num, "cat": test_cat},
        }

        return train_combined, test_combined

    def compute_losses(self, batch: np.ndarray) -> Dict[str, np.ndarray]:
        if self.tabdiff_model is None:
            losses = self._statistical_losses(batch)
            return {"total_loss": losses}

        diffusion = self.tabdiff_model
        import torch

        data_tensor = torch.from_numpy(batch[:, : self.d_numerical]).to(self.device, dtype=torch.float32)
        cat_tensor = torch.from_numpy(np.rint(batch[:, self.d_numerical:]).astype(np.int64)).to(self.device)

        total_losses, c_losses, d_losses = self._compute_loss_components(
            diffusion, data_tensor, cat_tensor, detach=True
        )
        return {
            "total_loss": total_losses,
            "c_loss": c_losses,
            "d_loss": d_losses,
        }

    def supports_gradients(self) -> bool:
        return self.tabdiff_model is not None and self.d_numerical > 0

    def compute_gradients(self, batch: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        if not self.supports_gradients():
            return None

        import torch

        diffusion = self.tabdiff_model
        param_list = list(diffusion.parameters())
        param_count = len(param_list)

        total_norms = np.zeros(len(batch), dtype=np.float32)
        per_param_norms = np.zeros((len(batch), param_count), dtype=np.float32)

        for idx, sample in enumerate(batch):
            diffusion.zero_grad(set_to_none=True)

            num_slice = sample[: self.d_numerical]
            cat_slice = sample[self.d_numerical :]

            x_num = torch.from_numpy(num_slice.reshape(1, -1)).to(self.device, dtype=torch.float32)
            x_cat = torch.from_numpy(np.rint(cat_slice).astype(np.int64).reshape(1, -1)).to(self.device)

            with torch.enable_grad():
                total_loss_tensor, _, _ = self._compute_loss_components(
                    diffusion, x_num, x_cat, detach=False
                )
                sample_loss = total_loss_tensor.view(-1)[0]
                sample_loss.backward()

            param_norm_vals = []
            for p in param_list:
                grad = p.grad
                if grad is None:
                    param_norm_vals.append(0.0)
                else:
                    param_norm_vals.append(grad.detach().norm().item())

            diffusion.zero_grad(set_to_none=True)

            param_norm_vals = np.asarray(param_norm_vals, dtype=np.float32)
            per_param_norms[idx] = param_norm_vals
            total_norms[idx] = float(np.linalg.norm(param_norm_vals, ord=2))

        return {
            "total_grad_norm": total_norms,
            "grad_param_norms": per_param_norms,
        }

    # helpers ------------------------------------------------------------------
    def _statistical_losses(self, data: np.ndarray) -> np.ndarray:
        n_samples = len(data)
        losses = np.zeros(n_samples)
        for i in range(n_samples):
            sample = data[i].flatten()
            mean_val = np.mean(sample)
            std_val = np.std(sample)
            range_val = np.ptp(sample)
            if std_val > 0:
                normalized = (sample - sample.min()) / (sample.max() - sample.min() + 1e-8)
                hist, _ = np.histogram(normalized, bins=10)
                hist = hist / hist.sum() + 1e-10
                entropy = -np.sum(hist * np.log(hist))
            else:
                entropy = 0.0
            losses[i] = std_val + 0.1 * range_val + 0.5 * entropy
        rng = np.random.default_rng(42)
        noise = rng.normal(0, losses.std() * 0.01, n_samples)
        return losses + noise

    def _compute_loss_components(
        self,
        diffusion,
        x_num: "torch.Tensor",
        x_cat: "torch.Tensor",
        detach: bool = True,
    ):
        import torch

        b = x_num.shape[0]
        device = x_num.device

        if diffusion.noise_dist == "uniform_t":
            t = torch.rand(b, device=device, dtype=x_num.dtype)
            t = t[:, None]
            sigma_num = diffusion.num_schedule.total_noise(t)
            sigma_cat = diffusion.cat_schedule.total_noise(t)
            dsigma_cat = diffusion.cat_schedule.rate_noise(t)
        else:
            sigma_num = diffusion.sample_ctime_noise(x_num)
            t = diffusion.num_schedule.inverse_to_t(sigma_num)
            sigma_cat = diffusion.cat_schedule.total_noise(t)
            dsigma_cat = diffusion.cat_schedule.rate_noise(t)

        x_num_t = x_num
        if x_num.shape[1] > 0:
            noise = torch.randn_like(x_num)
            x_num_t = x_num + noise * sigma_num

        x_cat_t = x_cat
        x_cat_t_soft = x_cat
        if x_cat.shape[1] > 0:
            is_learnable = diffusion.cat_scheduler == "log_linear_per_column"
            strategy = "soft" if is_learnable else "hard"
            move_chance = -torch.expm1(-sigma_cat)
            x_cat_t, x_cat_t_soft = diffusion.q_xt(x_cat, move_chance, strategy=strategy)

        model_out_num, model_out_cat = diffusion._denoise_fn(
            x_num_t,
            x_cat_t_soft,
            t.squeeze(),
            sigma=sigma_num,
        )

        num_loss = torch.zeros(b, device=device)
        cat_loss = torch.zeros(b, device=device)

        if x_num.shape[1] > 0:
            edm_loss = diffusion._edm_loss(model_out_num, x_num, sigma_num)
            num_loss = edm_loss.sum(dim=1)

        if x_cat.shape[1] > 0:
            logits = diffusion._subs_parameterization(model_out_cat, x_cat_t)
            cat_component = diffusion._absorbed_closs(logits, x_cat, sigma_cat, dsigma_cat)
            cat_loss = cat_component.sum(dim=1)

        total_loss = num_loss + cat_loss
        if detach:
            return (
                total_loss.detach().cpu().numpy(),
                num_loss.detach().cpu().numpy(),
                cat_loss.detach().cpu().numpy(),
            )
        return total_loss, num_loss, cat_loss


class DiffusionTSAdapter(MIABaseAdapter):
    """Adapter for Diffusion_TS_DP time-series diffusion models."""

    def __init__(self, dataset_name: Optional[str] = None):
        super().__init__(dataset_name)
        self.model = None
        self.seq_length = 0
        self.feature_size = 0
        self.fast_sampling = False
        self.dataset_dir: Optional[Path] = None

    def _project_root(self) -> Optional[Path]:
        root = Path(__file__).resolve().parent.parent / ".." / "Diffusion_TS_DP"
        root = root.resolve()
        if root.exists():
            return root
        return None

    def _ensure_dependencies(self, root: Path) -> None:
        if str(root) not in sys.path:
            sys.path.append(str(root))
        models_dir = root / "Models"
        if str(models_dir) not in sys.path:
            sys.path.append(str(models_dir))

        if "einops" not in sys.modules:
            import torch
            import types

            def _parse(pattern: str) -> Tuple[List[str], List[str]]:
                left, right = pattern.split("->")
                left_syms = [tok for tok in left.strip().split(" ") if tok]
                right_syms = [tok for tok in right.strip().split(" ") if tok]
                return left_syms, right_syms

            def rearrange(tensor: torch.Tensor, pattern: str, **axes_lengths) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                if result.dim() != len(axis_labels):
                    raise ValueError(f"Pattern {pattern} does not match tensor rank {result.dim()}")
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                        axis_labels.insert(idx, f"__axis_{idx}")
                    else:
                        if sym not in axis_labels:
                            raise ValueError(f"Unknown axis symbol '{sym}' in pattern '{pattern}'")
                        current = axis_labels.index(sym)
                        if current != idx:
                            result = result.movedim(current, idx)
                            axis_labels.insert(idx, axis_labels.pop(current))
                return result

            def reduce(tensor: torch.Tensor, pattern: str, reduction: str) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                keep_syms = [sym for sym in right if sym != "()"]
                for sym in list(axis_labels):
                    if sym not in keep_syms:
                        axis = axis_labels.index(sym)
                        if reduction == "sum":
                            result = result.sum(dim=axis, keepdim=False)
                        elif reduction == "mean":
                            result = result.mean(dim=axis, keepdim=False)
                        else:
                            raise ValueError(f"Unsupported reduction '{reduction}'")
                        axis_labels.pop(axis)
                for idx, sym in enumerate(keep_syms):
                    current = axis_labels.index(sym)
                    if current != idx:
                        result = result.movedim(current, idx)
                        axis_labels.insert(idx, axis_labels.pop(current))
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                return result

            def repeat(tensor: torch.Tensor, pattern: str, **axes_lengths) -> torch.Tensor:
                left, right = _parse(pattern)
                result = tensor
                axis_labels = list(left)
                if result.dim() != len(axis_labels):
                    raise ValueError(f"Pattern {pattern} does not match tensor rank {result.dim()}")
                for idx, sym in enumerate(right):
                    if sym == "()":
                        result = result.unsqueeze(idx)
                        axis_labels.insert(idx, f"__axis_{idx}")
                    elif sym in axis_labels:
                        current = axis_labels.index(sym)
                        if current != idx:
                            result = result.movedim(current, idx)
                            axis_labels.insert(idx, axis_labels.pop(current))
                    else:
                        size = axes_lengths.get(sym)
                        if size is None:
                            raise ValueError(f"Missing axis length for symbol '{sym}' in repeat pattern '{pattern}'")
                        result = result.unsqueeze(idx)
                        expand_sizes = list(result.shape)
                        expand_sizes[idx] = size
                        result = result.expand(*expand_sizes)
                        axis_labels.insert(idx, sym)
                return result

            module = types.ModuleType("einops")
            module.rearrange = rearrange
            module.reduce = reduce
            module.repeat = repeat
            sys.modules["einops"] = module

    def load_model(
        self,
        model_path: Optional[Path],
        schedule_path: Optional[Path],
    ) -> bool:
        if model_path is None or not model_path.exists():
            return False

        project_root = self._project_root()
        if not project_root:
            return False

        self._ensure_dependencies(project_root)

        checkpoint = torch.load(model_path, map_location=self.device)
        config_path = model_path.parent.parent / "configs" / "config.yaml"
        if not config_path.exists():
            config_path = model_path.parent.parent / "config.yaml"
        if not config_path.exists():
            return False

        import yaml

        with open(config_path, "r") as fh:
            config = yaml.safe_load(fh)

        model_cfg = config.get("dp_model", config.get("model"))
        if not model_cfg:
            return False
        target = model_cfg["target"]
        params = dict(model_cfg.get("params", {}))

        module_name, cls_name = target.rsplit(".", 1)
        module = __import__(module_name, fromlist=[cls_name])
        ModelCls = getattr(module, cls_name)

        self.seq_length = params.get("seq_length")
        self.feature_size = params.get("feature_size")

        model = ModelCls(**params)
        state_dict = checkpoint.get("ema") or checkpoint.get("model") or checkpoint
        if isinstance(state_dict, dict):
            model.load_state_dict(state_dict, strict=False)
        else:
            model.load_state_dict(state_dict.state_dict(), strict=False)

        model.to(self.device)
        model.eval()
        self.model = model
        self.dataset_dir = model_path.parent.parent
        return True

    def load_datasets(
        self,
        train_path: Path,
        test_path: Path,
    ) -> Tuple[np.ndarray, np.ndarray]:
        train_array = self._load_timeseries_array(train_path)
        test_array = self._load_timeseries_array(test_path)

        self.seq_length = self.seq_length or train_array.shape[1]
        self.feature_size = self.feature_size or train_array.shape[2]

        train_flat = train_array.reshape(train_array.shape[0], -1).astype(np.float32)
        test_flat = test_array.reshape(test_array.shape[0], -1).astype(np.float32)

        self._train_full = train_array
        self._test_full = test_array
        return train_flat, test_flat

    def _load_timeseries_array(self, path: Path) -> np.ndarray:
        if path.suffix == ".npy" and path.exists():
            arr = np.load(path, allow_pickle=True)
            if arr.ndim == 2 and self.seq_length and self.feature_size:
                arr = arr.reshape(-1, self.seq_length, self.feature_size)
            return arr

        npy_alt = path.with_suffix(".npy")
        if npy_alt.exists():
            arr = np.load(npy_alt, allow_pickle=True)
            if arr.ndim == 2 and self.seq_length and self.feature_size:
                arr = arr.reshape(-1, self.seq_length, self.feature_size)
            return arr

        df = pd.read_csv(path)
        arr = df.to_numpy(dtype=np.float32)
        seq_len = self.seq_length or 24
        feat = self.feature_size or (arr.shape[1] // seq_len)
        arr = arr.reshape(-1, seq_len, feat)
        return arr

    def compute_losses(self, batch: np.ndarray) -> Dict[str, np.ndarray]:
        if self.model is None:
            total = self._statistical_losses(batch)
            return {"total_loss": total}

        import torch

        seq = self.seq_length
        feat = self.feature_size
        x = torch.from_numpy(batch.reshape(-1, seq, feat)).to(self.device, dtype=torch.float32)

        with torch.no_grad():
            if hasattr(self.model, "dp_loss"):
                total = self.model.dp_loss(x).detach().cpu().numpy()
                return {"total_loss": total}
            else:
                losses = self._forward_loss(self.model, x, detach=True)
                return {"total_loss": losses}

    def supports_gradients(self) -> bool:
        return self.model is not None

    def compute_gradients(self, batch: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        if not self.supports_gradients():
            return None

        import torch

        model = self.model
        param_list = list(model.parameters())
        param_count = len(param_list)

        seq = self.seq_length
        feat = self.feature_size

        total_norms = np.zeros(len(batch), dtype=np.float32)
        per_param_norms = np.zeros((len(batch), param_count), dtype=np.float32)

        for idx, sample in enumerate(batch):
            model.zero_grad(set_to_none=True)

            sample_tensor = torch.from_numpy(sample.reshape(1, seq, feat)).to(
                self.device, dtype=torch.float32
            )
            sample_tensor.requires_grad_(False)

            with torch.enable_grad():
                if hasattr(model, "dp_loss"):
                    losses = model.dp_loss(sample_tensor)
                else:
                    losses = self._forward_loss(model, sample_tensor, detach=False)

                sample_loss = losses.view(-1)[0]
                sample_loss.backward()

            param_norm_vals = []
            for p in param_list:
                grad = p.grad
                if grad is None:
                    param_norm_vals.append(0.0)
                else:
                    param_norm_vals.append(grad.detach().norm().item())

            model.zero_grad(set_to_none=True)

            param_norm_vals = np.asarray(param_norm_vals, dtype=np.float32)
            per_param_norms[idx] = param_norm_vals
            total_norms[idx] = float(np.linalg.norm(param_norm_vals, ord=2))

        return {
            "total_grad_norm": total_norms,
            "grad_param_norms": per_param_norms,
        }

    def _forward_loss(self, model, x: "torch.Tensor", detach: bool = True):
        import torch

        b = x.shape[0]
        device = x.device
        t = torch.randint(0, model.num_timesteps, (b,), device=device).long()
        noise = torch.randn_like(x)
        x_t = model.q_sample(x_start=x, t=t, noise=noise)
        model_out = model.output(x_t, t)
        rec_loss = model.loss_fn(model_out, x, reduction="none")
        rec_loss = rec_loss.view(b, -1).mean(dim=1)
        weight = extract_loss_weight(model, t, rec_loss.shape).to(device)
        loss = rec_loss * weight
        if detach:
            return loss.detach().cpu().numpy()
        return loss

    def _statistical_losses(self, data: np.ndarray) -> np.ndarray:
        n_samples = len(data)
        losses = np.zeros(n_samples)
        for i in range(n_samples):
            sample = data[i].flatten()
            std_val = np.std(sample)
            mean_val = np.mean(sample)
            losses[i] = std_val + 0.1 * abs(mean_val)
        return losses


def extract_loss_weight(model, t, shape):
    if hasattr(model, "loss_weight"):
        from Models.interpretable_diffusion.model_utils import extract  # type: ignore

        return extract(model.loss_weight, t, shape)
    return torch.ones(shape, device=t.device)


ADAPTER_REGISTRY = {
    "adult": TabDiffAdapter,
    "tabdiff": TabDiffAdapter,
    "tabdiff_adult": TabDiffAdapter,
    "diffusion_ts": DiffusionTSAdapter,
    "stocks": DiffusionTSAdapter,
}


def build_adapter(
    adapter_name: Optional[str],
    dataset_name: Optional[str],
) -> Optional[MIABaseAdapter]:
    if adapter_name:
        key = adapter_name.lower()
        AdapterCls = ADAPTER_REGISTRY.get(key)
        if AdapterCls:
            return AdapterCls(dataset_name)

    if dataset_name:
        key = dataset_name.lower()
        AdapterCls = ADAPTER_REGISTRY.get(key)
        if AdapterCls:
            return AdapterCls(dataset_name)

    return None
