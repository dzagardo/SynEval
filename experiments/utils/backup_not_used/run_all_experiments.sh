#!/bin/bash
# Run SynEval for ALL experiments across all variants and epsilon values

echo "=========================================="
echo "Running Comprehensive SynEval Evaluation"
echo "=========================================="
echo ""

# All experiment variants
VARIANTS=(
    "OUTPUT_GRID_ROW_DP_EXTREMA"
    "OUTPUT_GRID_ROW_DP_EXTREMA_LONG"
    "OUTPUT_GRID_ROW_TRUE_EXTREMA"
    "OUTPUT_GRID_ROW_TRUE_EXTREMA_2_5_NORM_64_BATCH"
    "OUTPUT_GRID_ROW_TRUE_EXTREMA_LONG"
    "OUTPUT_GRID_WINDOW_DP_EXTREMA"
    "OUTPUT_GRID_WINDOW_DP_EXTREMA_LONG"
    "OUTPUT_GRID_WINDOW_TRUE_EXTREMA"
    "OUTPUT_GRID_WINDOW_TRUE_EXTREMA_2_5_NORM_64_BATCH"
    "OUTPUT_GRID_WINDOW_TRUE_EXTREMA_LONG"
)

# Determine which step to use based on variant name
for variant in "${VARIANTS[@]}"; do
    echo "----------------------------------------"
    echo "Processing variant: $variant"
    echo "----------------------------------------"

    # LONG variants use step_0020000, others use step_0010000
    if [[ $variant == *"_LONG" ]]; then
        STEP="step_0020000"
    else
        STEP="step_0010000"
    fi

    echo "Using step: $STEP"
    echo ""

    # Run orchestrator for this variant
    python orchestrate_syneval_experiment.py \
        --source-dir experiments/data \
        --working-dir experiments \
        --steps $STEP \
        --variants $variant \
        --skip-copy

    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "✅ Successfully completed: $variant"
    else
        echo "❌ Error processing: $variant (exit code: $exit_code)"
    fi
    echo ""
done

echo "=========================================="
echo "All variants processed!"
echo "=========================================="
echo ""
echo "Now regenerating HTML reports..."

# Regenerate all HTML reports
cd experiments/utils
python3 regenerate_reports.py

echo ""
echo "=========================================="
echo "Complete! All experiments evaluated and reports generated."
echo "=========================================="
