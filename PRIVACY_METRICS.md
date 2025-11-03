# Privacy Metrics in SynEval

SynEval now includes **two complementary privacy metrics** that measure different aspects of privacy protection in synthetic data generation:

## 1. Distinguishability AUC (Fidelity Metric)

### What It Measures
Distinguishability AUC measures how easily a classifier can distinguish between synthetic and real data samples. This is primarily a **fidelity metric**, not a privacy metric.

### Methodology
1. Train a binary classifier to predict: "Is this sample synthetic or real?"
2. Measure the AUC (Area Under the ROC Curve) of this classifier
3. Higher AUC = synthetic data is easily distinguishable from real data

### Interpretation
- **High AUC (>0.75)**: Poor fidelity - synthetic data doesn't closely resemble real data
- **Medium AUC (0.6-0.75)**: Moderate fidelity - some differences between synthetic and real
- **Low AUC (<0.6)**: Good fidelity - synthetic data closely resembles real data
- **AUC = 0.5**: Perfect fidelity - synthetic is indistinguishable from real

### Fidelity Score
The fidelity score is calculated as: `Fidelity Score = 1 - Distinguishability AUC`

**Key Point**: This measures **distribution similarity**, not privacy risk!

---

## 2. True Membership Inference Attack (MIA) AUC

### What It Measures
True MIA AUC measures whether a trained generative model has **memorized specific training samples**. This is a genuine **privacy risk metric**.

### Methodology
1. Load the trained diffusion model checkpoint
2. Compute per-sample loss/confidence for training samples (members)
3. Compute per-sample loss/confidence for test samples (non-members)
4. Train a binary classifier to distinguish members from non-members based on model confidence
5. Report the AUC of this attack

### Interpretation
- **AUC ≈ 0.5**: Good privacy - model doesn't reveal training membership
- **AUC = 0.6-0.7**: Moderate privacy risk - some memorization
- **AUC > 0.7**: High privacy risk - significant memorization of training data

### Privacy Risk Levels
- **Low risk (AUC < 0.6)**: Model has strong privacy protection
- **Moderate risk (AUC 0.6-0.7)**: Some privacy leakage, consider stronger DP
- **High risk (AUC > 0.7)**: Significant privacy vulnerability, increase epsilon or apply other privacy mechanisms

### Requirements
For MIA to run successfully, the following are needed:
- Trained model checkpoints (`.pt` files) in a `checkpoints/` directory
- Training data CSV file
- Test/validation data CSV file

If these are not available, MIA will be skipped and the report will show "N/A".

---

## Key Differences

| Aspect | Distinguishability AUC | True MIA AUC |
|--------|------------------------|--------------|
| **Measures** | Distribution similarity | Training data memorization |
| **Type** | Fidelity metric | Privacy risk metric |
| **High AUC means** | Poor fidelity | High privacy risk |
| **Low AUC means** | Good fidelity | Good privacy protection |
| **Ideal value** | 0.5 (indistinguishable) | 0.5 (no memorization) |
| **Requires** | Synthetic + real data | Model checkpoints + train/test data |

## Visual Representation in Reports

Privacy reports now include:

1. **Summary Metrics Card**:
   - Distinguishability AUC
   - AUC-Derived Fidelity Score
   - **True MIA AUC** (new!)
   - Exact Match Percentage

2. **Interpretation Section**:
   - Clear explanation of what each metric measures
   - Risk level assessment for True MIA
   - Guidance on improving privacy/fidelity

3. **Key Distinction Box**:
   A highlighted box explaining:
   - **Distinguishability AUC** = "Can we tell synthetic from real?" (fidelity)
   - **True MIA AUC** = "Does model memorize training data?" (privacy)

## Implementation Details

### Membership Inference Attack Module

Location: `experiments/utils/membership_inference.py`

Key features:
- Automatic checkpoint discovery (finds latest `.pt` file)
- Handles missing PyTorch gracefully (falls back to statistical measures)
- Supports various checkpoint formats
- Computes confidence intervals
- Logs detailed statistics

### Integration with Orchestration

The MIA is automatically run after each successful SynEval evaluation:

1. After `run.py` completes successfully
2. The orchestrator looks for checkpoints in the experiment directory
3. Finds training and test data files
4. Runs the MIA attack
5. Adds results to `results.json` under `privacy.true_mia`

### Directory Scanner

Location: `experiments/utils/directory_scanner.py`

The new flexible directory scanner allows the orchestrator to handle various directory structures:

- Auto-detects epsilon levels (dp_eps1, dp_eps10, dp_epsInf, etc.)
- Handles nested or flat structures
- Supports multiple dataset naming conventions
- Finds data files with flexible patterns
- Groups experiments by name, epsilon, or step

## Example Output

### results.json
```json
{
  "privacy": {
    "membership_inference": {
      "distinguishability_auc": 0.72,
      "fidelity_score": 0.28
    },
    "true_mia": {
      "auc": 0.58,
      "accuracy": 0.62,
      "ci_95_lower": 0.52,
      "ci_95_upper": 0.64,
      "train_loss_mean": 0.023,
      "train_loss_std": 0.008,
      "test_loss_mean": 0.019,
      "test_loss_std": 0.007,
      "n_train": 1000,
      "n_test": 1000,
      "checkpoint_path": "/path/to/checkpoint.pt"
    }
  }
}
```

### Privacy Report Interpretation

For the example above:
- **Distinguishability AUC of 0.72**: Indicates moderate-to-poor fidelity. Synthetic data is fairly distinguishable from real data.
- **Fidelity Score of 0.28 (28%)**: The synthetic data captures about 28% of the real data's characteristics.
- **True MIA AUC of 0.58**: Indicates **low privacy risk**. The model shows minimal memorization of training data, which is good for privacy.

This scenario demonstrates that:
1. The model has good privacy protection (MIA AUC near 0.5)
2. But the synthetic data quality could be improved (high distinguishability)
3. Consider tuning the model to improve fidelity while maintaining privacy

## Best Practices

### For Privacy Protection
- Aim for True MIA AUC < 0.6
- If MIA AUC > 0.7, consider:
  - Using stronger differential privacy (lower epsilon)
  - Adding more noise during training
  - Using larger training datasets
  - Post-processing to reduce memorization

### For Fidelity
- Aim for Distinguishability AUC < 0.65
- If Distinguishability AUC > 0.75, consider:
  - Training for more epochs
  - Adjusting model architecture
  - Tuning hyperparameters
  - Using less aggressive privacy mechanisms

### The Privacy-Utility Tradeoff
- Lower epsilon → Better privacy (lower MIA AUC) but potentially worse fidelity
- Higher epsilon → Better fidelity (lower Distinguishability AUC) but higher privacy risk
- The goal is to find the sweet spot where both metrics are acceptable for your use case

## Troubleshooting

### "True MIA could not be computed"

This message appears when:
1. **No checkpoints found**: Ensure `.pt` checkpoint files exist in `checkpoints/` directory
2. **No training data**: MIA needs the original training dataset
3. **No test data**: MIA needs a holdout/test dataset to compare against
4. **PyTorch issues**: Check that PyTorch is installed correctly (though fallback mode exists)

### MIA returns AUC ≈ 0.5 for all experiments

This might indicate:
- The fallback mode is being used (no PyTorch)
- Model checkpoints are not loading correctly
- Data preprocessing issues
- Check logs for warnings/errors

### Distinguishability AUC is very high

This is normal for:
- Early training steps
- Very strong differential privacy (low epsilon)
- Mismatched data preprocessing
- Poor model hyperparameters

## References

### Membership Inference Attacks
- Shokri et al., "Membership Inference Attacks Against Machine Learning Models" (2017)
- Carlini et al., "Membership Inference Attacks From First Principles" (2022)

### Differential Privacy
- Dwork & Roth, "The Algorithmic Foundations of Differential Privacy" (2014)

### Synthetic Data Evaluation
- Xu et al., "SynEval: A Comprehensive Evaluation Framework for Synthetic Data" (2024)
