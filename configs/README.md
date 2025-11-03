# SynEval Configuration Guide

## Overview

This directory contains YAML configuration files for running SynEval experiments.

## Available Configurations

### `cross_group_dp.yaml`

Comprehensive configuration for Differential Privacy evaluation across multiple epsilon values.

**Key Features:**
- Multi-epsilon evaluation (1, 10, 100, 1000, 10000, Inf)
- Multiple experiment variants
- All SynEval metrics (fidelity, utility, privacy, diversity)
- Pre-configured experiment templates
- Dashboard generation
- Parallel execution support

## Usage

### Basic Usage

```bash
# Run all enabled experiments
python run_dp_evaluation.py --config configs/cross_group_dp.yaml

# Run specific experiment
python run_dp_evaluation.py --config configs/cross_group_dp.yaml \
                             --experiment comprehensive_evaluation

# Run with specific epsilon values
python run_dp_evaluation.py --config configs/cross_group_dp.yaml \
                             --epsilons 1,10,100

# Run with GPU acceleration
python run_dp_evaluation.py --config configs/cross_group_dp.yaml \
                             --device cuda

# Dry run (validate config without executing)
python run_dp_evaluation.py --config configs/cross_group_dp.yaml --dry-run
```

### Python API Usage

```python
import yaml
from pathlib import Path

# Load config
with open("configs/cross_group_dp.yaml") as f:
    config = yaml.safe_load(f)

# Access configuration
dp_config = config["dp_config"]
experiments = config["syneval_experiments"]

# Get epsilon values
epsilons = dp_config["epsilon_values"]
print(f"Evaluating {len(epsilons)} epsilon values: {epsilons}")

# Get experiment directories
exp_dirs = dp_config["experiment_dirs"]
print(f"Scanning {len(exp_dirs)} experiment directories")

# Iterate through experiments
for exp in experiments:
    if exp["enabled"]:
        print(f"Running: {exp['name']}")
        print(f"  Description: {exp['description']}")
        print(f"  Metrics: {exp['metrics']}")
```

## Configuration Structure

### 1. DP Configuration (`dp_config`)

```yaml
dp_config:
  experiment_dirs: [...]      # Directories to scan
  epsilon_prefix: "dp_eps"    # Directory prefix
  epsilon_values: [...]       # Epsilon values to evaluate
  data_dir: "..."             # Data directory path
  train_data: "..."           # Training data filename
  test_data: "..."            # Test data filename
  synthetic_data: "..."       # Synthetic data filename
  model_dir: "..."            # Model checkpoint directory
  model_file: "..."           # Model checkpoint filename
```

### 2. SynEval Experiments (`syneval_experiments`)

```yaml
syneval_experiments:
  - name: "experiment_name"
    description: "..."
    enabled: true

    metrics:
      fidelity: [...]
      utility: [...]
      privacy: [...]
      diversity: [...]

    utility_config:
      input_columns: [...]
      output_columns: [...]
      task_type: "regression"

    device: "auto"
    output_dir: "..."
    generate_reports: true
```

### 3. Execution Settings (`execution`)

```yaml
execution:
  parallel: false
  max_workers: 4
  continue_on_error: true
  log_level: "INFO"
  enable_cache: true
  cache_dir: "./cache"
```

### 4. Reporting Settings (`reporting`)

```yaml
reporting:
  generate_json: true
  generate_html: true
  generate_csv: true
  create_dashboards: true
  dashboard_dir: "experiments/dashboards"
```

## Path Structure

### Input Files

```
experiments/data/{variant}/dp_eps{epsilon}/{dataset}/samples/
├── stocks_ground_truth_24_train.csv
├── stocks_ground_truth_24_test.npy
└── ddpm_fake_stocks.csv

experiments/data/{variant}/dp_eps{epsilon}/{dataset}/checkpoints/
└── checkpoint-10.pt
```

### Output Files

```
experiments/results/{variant}/dp_eps{epsilon}/
├── results.json
├── metadata.json
├── privacy_report.html
└── utility_report.html

experiments/dashboards/
├── comprehensive_overview.html
├── privacy_analysis.html
├── utility_analysis.html
└── epsilon_comparison.html
```

## Available Metrics

### Fidelity Metrics
- `quality` - SDV Quality Score (0-100, higher = better)
- `diagnostic` - SDV Diagnostic Score (0-100, higher = better)

### Utility Metrics
- `tstr_accuracy` - Train on Synthetic, Test on Real
- `correlation_analysis` - Feature relationship preservation

### Privacy Metrics
- `membership_inference` - Distinguishability AUC (0.5 = perfect privacy)
- `exact_matches` - Identity disclosure (0% = perfect)
- `distance_to_closest_records` - DCR (overfitting detection)
- `nearest_neighbor_distance_ratio` - NNDR (memorization detection)

### Diversity Metrics
- `tabular_diversity` - Overall variety
- `entropy_metrics` - Information content (ratio ~1.0 = good)

## Pre-configured Experiments

### 1. Comprehensive Evaluation
Runs all available metrics for complete assessment.

### 2. Privacy-Focused
Detailed privacy analysis including MIA.

### 3. Utility-Focused
Machine learning utility assessment with TSTR.

### 4. Fidelity & Diversity
Statistical quality and variety assessment.

### 5. Smoke Test
Fast validation with essential metrics only.

### 6. Custom Template
Blank template for custom metric combinations.

## Epsilon Values

| Epsilon | Privacy Level | Use Case |
|---------|---------------|----------|
| 1 | Strong | Production systems |
| 10 | Moderate | General use |
| 100 | Relaxed | Research |
| 1000 | Weak | Ablation studies |
| 10000 | Very Weak | Ablation studies |
| Inf | No DP | Baseline comparison |

**Trade-off:** Lower epsilon = stronger privacy = potentially lower utility

## Advanced Configuration

### Path Templates

Use variable substitution for dynamic paths:
- `{variant}` - Experiment variant name
- `{epsilon}` - Epsilon value
- `{epsilon_dir}` - Epsilon directory (e.g., "dp_eps1")
- `{dataset}` - Dataset name

Example:
```yaml
path_templates:
  data_path: "{experiment_dir}/{epsilon_dir}/{data_dir}"
  results_path: "{output_dir}/results.json"
```

### Filters

Filter which experiments to run:
```yaml
filters:
  epsilon_min: 1
  epsilon_max: 100
  variants: ["OUTPUT_GRID_WINDOW_DP_EXTREMA_LONG"]
  exclude_variants: []
```

### Validation

Validate data before running:
```yaml
validation:
  check_data_exists: true
  check_model_exists: true
  validate_metadata: true
  min_samples: 100
```

## Troubleshooting

### Config Validation

```python
import yaml
from pathlib import Path

def validate_config(config_path):
    """Validate YAML config syntax."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("✓ Config is valid YAML")

        # Check required sections
        required = ["dp_config", "syneval_experiments"]
        for section in required:
            if section not in config:
                print(f"✗ Missing section: {section}")
            else:
                print(f"✓ Found section: {section}")

        return config
    except yaml.YAMLError as e:
        print(f"✗ YAML parsing error: {e}")
        return None

config = validate_config("configs/cross_group_dp.yaml")
```

### Check File Paths

```python
def check_paths(config):
    """Verify all experiment paths exist."""
    dp_config = config["dp_config"]

    for exp_dir in dp_config["experiment_dirs"]:
        path = Path(exp_dir)
        if not path.exists():
            print(f"✗ Directory not found: {exp_dir}")
        else:
            print(f"✓ Found: {exp_dir}")

            # Check epsilon subdirectories
            for eps in dp_config["epsilon_values"]:
                eps_str = str(eps) if eps != "Inf" else "Inf"
                eps_dir = path / f"{dp_config['epsilon_prefix']}{eps_str}"
                if eps_dir.exists():
                    print(f"  ✓ {eps_dir.name}")
                else:
                    print(f"  ✗ {eps_dir.name} (not found)")

check_paths(config)
```

## References

- **Metric Documentation:** `docs/codebase_bundle.txt`
- **Main Orchestrator:** `orchestrate_syneval_experiment.py`
- **SynEval API:** `run.py`

## Support

For questions or issues:
1. Check `docs/codebase_bundle.txt` for metric explanations
2. Review example usage in config file comments
3. Validate config with `--dry-run` flag
4. Enable debug logging: `log_level: "DEBUG"`
