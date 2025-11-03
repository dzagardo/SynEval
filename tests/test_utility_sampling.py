import numpy as np
import pandas as pd

from utility import UtilityEvaluator


def _build_metadata():
    return {
        "columns": {
            "feature": {"sdtype": "numerical"},
            "target": {"sdtype": "categorical"},
        }
    }


def test_utility_handles_synthetic_larger_than_real():
    real_rows = 40
    synthetic_rows = 120

    real_data = pd.DataFrame(
        {
            "feature": np.arange(real_rows, dtype=float),
            "target": np.where(np.arange(real_rows) % 3 == 0, "A", "B"),
        }
    )
    synthetic_data = pd.DataFrame(
        {
            "feature": np.arange(synthetic_rows, dtype=float),
            "target": np.where(np.arange(synthetic_rows) % 4 == 0, "A", "B"),
        }
    )

    evaluator = UtilityEvaluator(
        synthetic_data=synthetic_data,
        original_data=real_data,
        metadata=_build_metadata(),
        input_columns=["feature"],
        output_columns=["target"],
        task_type="classification",
    )

    results = evaluator.evaluate()
    tstr = results.get("tstr_accuracy", {})

    assert "error" not in tstr, f"Unexpected TSTR error: {tstr.get('error')}"
    assert "synthetic_data_model" in tstr
    assert "real_data_model" in tstr
    assert tstr.get("training_size", 0) > 0
    assert tstr.get("test_size", 0) > 0
