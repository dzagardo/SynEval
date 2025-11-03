# Quick Start: New Privacy Features

## What's New?

SynEval now evaluates privacy using **two complementary metrics**:

| Metric | What it Measures | Good Value | Bad Value |
|--------|-----------------|------------|-----------|
| **Distinguishability AUC** | Fidelity (how realistic synthetic data is) | Low (<0.6) | High (>0.75) |
| **True MIA AUC** | Privacy Risk (model memorization) | Low (<0.6) | High (>0.7) |

## Quick Interpretation

### Reading Your Privacy Report

When you see these metrics in your HTML report:

```
Distinguishability AUC: 0.62
True MIA AUC: 0.55
```

**Interpretation:**
- ✅ **Good Privacy**: MIA AUC of 0.55 means low privacy risk
- ✅ **Decent Fidelity**: Distinguishability of 0.62 means reasonable quality
- 🎯 **Overall**: Acceptable privacy-utility tradeoff

### Quick Decision Guide

**If True MIA AUC > 0.7** (High Privacy Risk):
1. Use stronger differential privacy (lower epsilon)
2. Add more noise during training
3. Increase training dataset size
4. Review model checkpoints for memorization

**If Distinguishability AUC > 0.75** (Poor Fidelity):
1. Train for more epochs
2. Reduce DP noise (higher epsilon)
3. Tune model hyperparameters
4. Check data preprocessing

## Running Evaluations

### Standard Usage (Automatic MIA)

```bash
python orchestrate_syneval_experiment.py \
    --source-dir /path/to/experiments \
    --working-dir ./experiments
```

**MIA runs automatically if:**
- ✅ Experiment has `checkpoints/` directory with `.pt` files
- ✅ Training data is available
- ✅ Test/validation data is available

### Viewing Results

**HTML Reports**: `experiments/results/{experiment}/privacy_report.html`

**JSON Results**: `experiments/results/{experiment}/results.json`

Look for:
```json
{
  "privacy": {
    "membership_inference": {
      "distinguishability_auc": 0.62
    },
    "true_mia": {
      "auc": 0.55,
      "ci_95_lower": 0.48,
      "ci_95_upper": 0.62
    }
  }
}
```

## Visual Guide

### Privacy Report Screenshot Reference

Your privacy reports now include:

1. **📊 Summary Metrics (Top)**
   ```
   ┌─────────────────────────┐
   │ Distinguishability: 0.62│
   │ Fidelity Score: 38%     │
   │ True MIA AUC: 0.55      │  ← NEW!
   │ Exact Matches: 0.2%     │
   └─────────────────────────┘
   ```

2. **📝 Interpretation Section**
   - Clear explanation of both metrics
   - Privacy risk assessment
   - Highlighted "Key Distinction" box

3. **📈 Visualizations**
   - Separability gauge
   - Coverage charts
   - Distance distributions

## Troubleshooting

### "True MIA could not be computed"

**Reason**: Missing checkpoints or data files

**Solution**:
1. Check `checkpoints/` directory exists
2. Verify `.pt` checkpoint files are present
3. Confirm train/test data files are available
4. Check logs for specific error messages

### MIA AUC always ≈ 0.5

**Possible Causes**:
- Fallback mode (no PyTorch)
- Checkpoint loading issues
- Data preprocessing problems

**Solution**:
1. Check PyTorch installation: `python -c "import torch; print(torch.__version__)"`
2. Review logs for warnings
3. Verify checkpoint file format

## Advanced Usage

### Manual MIA Execution

```python
from pathlib import Path
from experiments.utils.membership_inference import run_mia_for_experiment

results = run_mia_for_experiment(
    experiment_dir=Path("./my_experiment"),
    train_data_path=Path("./data/train.csv"),
    test_data_path=Path("./data/test.csv")
)

print(f"MIA AUC: {results['auc']:.3f}")
print(f"95% CI: [{results['ci_95_lower']:.3f}, {results['ci_95_upper']:.3f}]")
print(f"Privacy Risk: {'High' if results['auc'] > 0.7 else 'Moderate' if results['auc'] > 0.6 else 'Low'}")
```

### Directory Scanner

```python
from pathlib import Path
from experiments.utils.directory_scanner import ExperimentScanner

scanner = ExperimentScanner(Path("./experiments/data"))

# Discover all experiments
all_experiments = scanner.scan()

# Filter by epsilon
dp1_experiments = scanner.scan(epsilon_filter=["dp_eps1"])

# Group by experiment name
grouped = scanner.group_by_experiment(all_experiments)

for exp_name, specs in grouped.items():
    print(f"{exp_name}: {len(specs)} configurations")
```

## Best Practices

### 1. Always Review Both Metrics

Don't rely on just one metric:
- Distinguishability AUC alone doesn't tell you about privacy risk
- True MIA AUC alone doesn't tell you about data quality

### 2. Consider Your Use Case

**High Privacy Requirements** (medical, financial data):
- Target: MIA AUC < 0.55
- Accept: Higher distinguishability (lower fidelity)

**High Fidelity Requirements** (research, analytics):
- Target: Distinguishability AUC < 0.6
- Monitor: MIA AUC stays reasonable (<0.7)

### 3. Iterate Based on Results

```
Initial: Dist=0.75, MIA=0.52
→ Poor fidelity, good privacy
→ Action: Increase epsilon, train longer

Next: Dist=0.65, MIA=0.58
→ Better fidelity, still good privacy
→ Action: Continue tuning

Final: Dist=0.58, MIA=0.56
→ Good fidelity, good privacy
→ Result: Production-ready! ✅
```

## Key Differences Reminder

**Distinguishability AUC**:
- Compares synthetic vs real distributions
- High = poor fidelity
- Measures: "Can we tell them apart?"

**True MIA AUC**:
- Tests model's training membership knowledge
- High = privacy risk
- Measures: "Does model remember training data?"

## Need More Help?

📖 **Detailed Documentation**: See `PRIVACY_METRICS.md`

🔧 **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

💻 **General Usage**: See `README.md`

---

**Pro Tip**: The sweet spot is when **both AUC values are close to 0.5** - this means synthetic data is indistinguishable from real (good fidelity) AND the model doesn't leak training information (good privacy).
