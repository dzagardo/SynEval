# experiments/dp_runner_utils.py
"""
Helper utilities for the DP evaluation runner.
Provides shared functions for data processing, result aggregation, and reporting.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime


logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Aggregate and compute statistics across multiple experiment results."""
    
    @staticmethod
    def aggregate_group_metrics(results_paths: List[Path]) -> Dict[str, Any]:
        """
        Aggregate metrics across multiple experiments in a group.
        
        Args:
            results_paths: List of paths to results.json files
            
        Returns:
            Dictionary containing aggregated metrics
        """
        all_results = []
        for path in results_paths:
            if path.exists():
                with open(path, 'r') as f:
                    all_results.append(json.load(f))
        
        if not all_results:
            return {}
        
        aggregated = {
            "group": all_results[0].get("group"),
            "group_display_name": all_results[0].get("group_display_name"),
            "epsilons": [r.get("epsilon") for r in all_results],
            "experiments_count": len(all_results),
            "timestamp": datetime.now().isoformat()
        }
        
        # Aggregate fidelity metrics
        if any("fidelity" in r for r in all_results):
            aggregated["fidelity"] = MetricsAggregator._aggregate_dimension(
                all_results, "fidelity"
            )
        
        # Aggregate utility metrics
        if any("utility" in r for r in all_results):
            aggregated["utility"] = MetricsAggregator._aggregate_dimension(
                all_results, "utility"
            )
        
        # Aggregate privacy metrics
        if any("privacy" in r for r in all_results):
            aggregated["privacy"] = MetricsAggregator._aggregate_dimension(
                all_results, "privacy"
            )
        
        # Aggregate diversity metrics
        if any("diversity" in r for r in all_results):
            aggregated["diversity"] = MetricsAggregator._aggregate_dimension(
                all_results, "diversity"
            )
        
        # Aggregate MIA metrics
        if any("mia" in r for r in all_results):
            aggregated["mia"] = MetricsAggregator._aggregate_mia_metrics(all_results)
        
        return aggregated
    
    @staticmethod
    def _aggregate_dimension(results: List[Dict], dimension: str) -> Dict:
        """Aggregate metrics for a specific dimension."""
        dim_results = [r.get(dimension, {}) for r in results if dimension in r]
        if not dim_results:
            return {}
        
        # Get all metric keys
        all_keys = set()
        for r in dim_results:
            all_keys.update(MetricsAggregator._extract_numeric_keys(r))
        
        aggregated = {}
        for key in all_keys:
            values = []
            for r in dim_results:
                value = MetricsAggregator._get_nested_value(r, key)
                if value is not None and isinstance(value, (int, float)):
                    values.append(value)
            
            if values:
                aggregated[key] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "median": np.median(values)
                }
        
        return aggregated
    
    @staticmethod
    def _aggregate_mia_metrics(results: List[Dict]) -> Dict:
        """Aggregate MIA metrics specifically."""
        mia_results = [r.get("mia", {}) for r in results if "mia" in r and r["mia"].get("status") != "failed"]
        
        if not mia_results:
            return {"status": "no_data"}
        
        auc_values = [r.get("auc", 0.5) for r in mia_results if "auc" in r]
        
        return {
            "auc": {
                "mean": np.mean(auc_values) if auc_values else 0.5,
                "std": np.std(auc_values) if auc_values else 0.0,
                "min": np.min(auc_values) if auc_values else 0.5,
                "max": np.max(auc_values) if auc_values else 0.5,
                "values_by_epsilon": {
                    results[i].get("epsilon"): mia_results[i].get("auc", 0.5)
                    for i in range(len(results))
                    if i < len(mia_results) and "auc" in mia_results[i]
                }
            }
        }
    
    @staticmethod
    def _extract_numeric_keys(d: Dict, prefix: str = "") -> List[str]:
        """Recursively extract keys that have numeric values."""
        keys = []
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (int, float)):
                keys.append(full_key)
            elif isinstance(v, dict):
                keys.extend(MetricsAggregator._extract_numeric_keys(v, full_key))
        return keys
    
    @staticmethod
    def _get_nested_value(d: Dict, key: str) -> Optional[float]:
        """Get value from nested dictionary using dot notation."""
        parts = key.split(".")
        value = d
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value if isinstance(value, (int, float)) else None


class DataValidator:
    """Validate data and experiment configurations."""
    
    @staticmethod
    def validate_data_schema(data: pd.DataFrame, expected_columns: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Validate that data has expected schema.
        
        Args:
            data: DataFrame to validate
            expected_columns: List of expected column names (optional)
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check if data is empty
        if data.empty:
            issues.append("Data is empty")
            return False, issues
        
        # Check for expected columns if provided
        if expected_columns:
            missing_cols = set(expected_columns) - set(data.columns)
            if missing_cols:
                issues.append(f"Missing columns: {missing_cols}")
        
        # Check for NaN values
        nan_cols = data.columns[data.isnull().any()].tolist()
        if nan_cols:
            issues.append(f"Columns with NaN values: {nan_cols}")
        
        # Check for infinite values in numeric columns
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if np.isinf(data[col]).any():
                issues.append(f"Column '{col}' contains infinite values")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_results_json(results: Dict) -> Tuple[bool, List[str]]:
        """
        Validate results JSON structure.
        
        Args:
            results: Results dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        required_fields = ["experiment_id", "status"]
        
        for field in required_fields:
            if field not in results:
                issues.append(f"Missing required field: {field}")
        
        if results.get("status") == "success":
            # Check for at least one evaluation dimension
            dimensions = ["fidelity", "utility", "privacy", "diversity", "mia"]
            if not any(d in results for d in dimensions):
                issues.append("No evaluation dimensions found in successful result")
        
        return len(issues) == 0, issues


class ResultFormatter:
    """Format results for display and reporting."""
    
    @staticmethod
    def format_metric_value(value: Any, precision: int = 4) -> str:
        """Format a metric value for display."""
        if isinstance(value, float):
            if value < 0.001 and value > 0:
                return f"{value:.2e}"
            else:
                return f"{value:.{precision}f}"
        elif isinstance(value, dict) and "mean" in value:
            return f"{value['mean']:.{precision}f} ± {value['std']:.{precision}f}"
        else:
            return str(value)
    
    @staticmethod
    def create_summary_table(results: Dict) -> str:
        """Create a text summary table of results."""
        lines = []
        lines.append("="*60)
        lines.append("EXPERIMENT RESULTS SUMMARY")
        lines.append("="*60)
        
        # Basic info
        lines.append(f"Experiment ID: {results.get('experiment_id', 'N/A')}")
        lines.append(f"Group: {results.get('group_display_name', 'N/A')}")
        lines.append(f"Epsilon: {results.get('epsilon', 'N/A')}")
        lines.append(f"Status: {results.get('status', 'N/A')}")
        lines.append("-"*60)
        
        # Metrics by dimension
        for dimension in ["fidelity", "utility", "privacy", "diversity"]:
            if dimension in results:
                lines.append(f"\n{dimension.upper()} METRICS:")
                dim_data = results[dimension]
                
                # Extract and format key metrics
                if isinstance(dim_data, dict):
                    for key, value in dim_data.items():
                        if not key.startswith("_"):  # Skip internal fields
                            formatted_value = ResultFormatter.format_metric_value(value)
                            lines.append(f"  {key}: {formatted_value}")
        
        # MIA results
        if "mia" in results and results["mia"].get("status") != "failed":
            lines.append("\nMIA RESULTS:")
            if "auc" in results["mia"]:
                lines.append(f"  AUC: {ResultFormatter.format_metric_value(results['mia']['auc'])}")
        
        lines.append("="*60)
        return "\n".join(lines)
    
    @staticmethod
    def create_comparison_table(group_results: List[Dict]) -> pd.DataFrame:
        """Create a comparison table across multiple experiments."""
        if not group_results:
            return pd.DataFrame()
        
        rows = []
        for result in group_results:
            row = {
                "Epsilon": result.get("epsilon", "N/A"),
                "Status": result.get("status", "N/A")
            }
            
            # Add key metrics from each dimension
            if "fidelity" in result and isinstance(result["fidelity"], dict):
                if "sdv_quality_score" in result["fidelity"]:
                    row["Fidelity (SDV)"] = result["fidelity"]["sdv_quality_score"]
                if "distinguishability_auc" in result["fidelity"]:
                    row["Distinguishability AUC"] = result["fidelity"]["distinguishability_auc"]
            
            if "utility" in result and isinstance(result["utility"], dict):
                if "tstr_accuracy" in result["utility"]:
                    row["TSTR Accuracy"] = result["utility"]["tstr_accuracy"]
            
            if "privacy" in result and isinstance(result["privacy"], dict):
                if "exact_match_percentage" in result["privacy"]:
                    row["Exact Matches (%)"] = result["privacy"]["exact_match_percentage"]
            
            if "diversity" in result and isinstance(result["diversity"], dict):
                if "coverage_percentage" in result["diversity"]:
                    row["Coverage (%)"] = result["diversity"]["coverage_percentage"]
            
            if "mia" in result and "auc" in result["mia"]:
                row["MIA AUC"] = result["mia"]["auc"]
            
            rows.append(row)
        
        return pd.DataFrame(rows)


class ExperimentTracker:
    """Track experiment progress and maintain state."""
    
    def __init__(self, output_dir: Path):
        """Initialize the experiment tracker."""
        self.output_dir = Path(output_dir)
        self.state_file = self.output_dir / "experiment_state.json"
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load existing state or create new."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "started_at": datetime.now().isoformat(),
            "completed_experiments": [],
            "failed_experiments": [],
            "in_progress": None
        }
    
    def save_state(self):
        """Save current state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def mark_started(self, experiment_id: str):
        """Mark an experiment as started."""
        self.state["in_progress"] = {
            "experiment_id": experiment_id,
            "started_at": datetime.now().isoformat()
        }
        self.save_state()
    
    def mark_completed(self, experiment_id: str, results_path: str):
        """Mark an experiment as completed."""
        self.state["completed_experiments"].append({
            "experiment_id": experiment_id,
            "completed_at": datetime.now().isoformat(),
            "results_path": results_path
        })
        self.state["in_progress"] = None
        self.save_state()
    
    def mark_failed(self, experiment_id: str, error: str):
        """Mark an experiment as failed."""
        self.state["failed_experiments"].append({
            "experiment_id": experiment_id,
            "failed_at": datetime.now().isoformat(),
            "error": error
        })
        self.state["in_progress"] = None
        self.save_state()
    
    def is_completed(self, experiment_id: str) -> bool:
        """Check if an experiment has already been completed."""
        completed_ids = [e["experiment_id"] for e in self.state["completed_experiments"]]
        return experiment_id in completed_ids
    
    def get_summary(self) -> Dict:
        """Get a summary of experiment progress."""
        return {
            "total_completed": len(self.state["completed_experiments"]),
            "total_failed": len(self.state["failed_experiments"]),
            "in_progress": self.state["in_progress"],
            "started_at": self.state["started_at"],
            "last_update": datetime.now().isoformat()
        }


# HTML Generator Interface Documentation
"""
The following functions define the interface for the HTML generator module
(experiments.utils.dp_html_generator) that needs to be implemented:

def generate_individual_report(
    results_json_path: str,
    output_dir: str,
    experiment_name: str,
    epsilon: str
) -> None:
    '''
    Generate HTML report for a single experiment.
    
    Args:
        results_json_path: Path to the results.json file
        output_dir: Directory to save the HTML report
        experiment_name: Display name for the experiment
        epsilon: Epsilon value for the experiment
    
    The function should:
    1. Load the results JSON
    2. Create privacy_report.html with privacy metrics visualization
    3. Create utility_report.html with utility metrics visualization
    4. Include charts for key metrics using Chart.js or similar
    '''
    pass


def generate_in_group_report(
    results_json_paths: List[str],
    output_dir: str,
    group_name: str
) -> None:
    '''
    Generate HTML report comparing experiments within a group.
    
    Args:
        results_json_paths: List of paths to results.json files
        output_dir: Directory to save the HTML report
        group_name: Display name for the experiment group
    
    The function should:
    1. Load all results JSONs for the group
    2. Create comparison charts across epsilon values
    3. Generate in_group_comparison.html with:
       - Privacy metrics comparison
       - Utility metrics comparison
       - Trend analysis across epsilon values
    '''
    pass


def generate_cross_group_report(
    all_results: Dict[str, Dict],
    output_dir: str
) -> None:
    '''
    Generate HTML report comparing all experiment groups.
    
    Args:
        all_results: Dictionary of all experiment results
        output_dir: Directory to save the HTML report
    
    The function should:
    1. Aggregate metrics across all groups
    2. Create cross_group_comparison.html with:
       - Comparative analysis across different DP methods
       - Best performing configurations
       - Trade-off analysis (privacy vs utility)
       - Overall recommendations
    '''
    pass
"""