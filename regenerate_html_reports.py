#!/usr/bin/env python3
"""
Script to regenerate HTML reports for all existing experiment results.
This will re-generate privacy_report.html and utility_report.html files
using the updated html_templates.py with improved chart rendering.
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrate_syneval_experiment import SynEvalOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_all_results():
    """Find all results.json files in the experiments directory"""
    results_dir = Path('experiments/results')
    if not results_dir.exists():
        logger.error(f"Results directory not found: {results_dir}")
        return []

    results_files = list(results_dir.glob('**/results.json'))
    logger.info(f"Found {len(results_files)} results.json files")
    return results_files


def regenerate_reports_for_result(results_path: Path, orchestrator: SynEvalOrchestrator):
    """Regenerate HTML reports for a single results.json file"""
    try:
        # Load results
        with open(results_path) as f:
            results = json.load(f)

        # Extract experiment info from path
        # Path format: experiments/results/VARIANT/DP_CONFIG/STEP/results.json
        parts = results_path.parts
        if len(parts) < 6:
            logger.warning(f"Unexpected path structure: {results_path}")
            return False

        variant = parts[-4]
        dp_config = parts[-3]
        step = parts[-2]

        # Extract dataset from results
        dataset = results.get('metadata', {}).get('dataset', 'stocks')

        # Build experiment dict that matches what the orchestrator expects
        exp = {
            'variant': variant,
            'dp_config': dp_config,
            'dataset': dataset,
            'step': step
        }

        # Extract metrics from results
        metrics = results.get('syneval_metrics', {})

        # Generate reports using orchestrator's method
        orchestrator._build_privacy_report(exp, results, metrics)
        orchestrator._build_utility_report(exp, results, metrics)

        logger.info(f"✓ {variant}/{dp_config}/{step}")
        return True

    except Exception as e:
        logger.error(f"Failed to regenerate {results_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to regenerate all HTML reports"""
    logger.info("=" * 60)
    logger.info("Starting HTML Report Regeneration")
    logger.info("=" * 60)

    results_files = find_all_results()

    if not results_files:
        logger.error("No results.json files found!")
        return

    # Create a dummy orchestrator instance just to use its report methods
    # We'll create it with minimal args since we're only using the report generation methods
    try:
        orchestrator = SynEvalOrchestrator(
            source_dir='experiments/data',
            working_dir='experiments/results'
        )
    except Exception as e:
        logger.error(f"Failed to create orchestrator: {e}")
        return

    success_count = 0
    fail_count = 0

    for i, results_path in enumerate(results_files, 1):
        logger.info(f"[{i}/{len(results_files)}] {results_path.parent.name}...")

        if regenerate_reports_for_result(results_path, orchestrator):
            success_count += 1
        else:
            fail_count += 1

    logger.info("=" * 60)
    logger.info("HTML Report Regeneration Complete")
    logger.info(f"Success: {success_count}, Failed: {fail_count}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
