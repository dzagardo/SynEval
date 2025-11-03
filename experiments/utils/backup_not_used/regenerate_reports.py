#!/usr/bin/env python3
"""
Regenerate All Reports
======================
Regenerates all privacy and utility reports with enhanced styling,
plus creates cross-experiment dashboards.
"""

from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_html_generator import EnhancedHTMLGenerator, parse_epsilon_from_path
from cross_group_dashboard import CrossGroupDashboard


def regenerate_all_reports(results_dir: Path) -> None:
    """Regenerate all individual experiment reports."""
    print("🚀 Starting report regeneration...")
    print(f"📁 Results directory: {results_dir}")
    
    # Find all results.json files
    results_files = list(results_dir.rglob('results.json'))
    
    if not results_files:
        print("❌ No results.json files found!")
        return
    
    print(f"✨ Found {len(results_files)} experiment results")
    
    success_count = 0
    error_count = 0
    
    for results_file in results_files:
        try:
            # Extract epsilon from path
            epsilon = parse_epsilon_from_path(results_file)
            
            # Generate privacy report
            privacy_output = results_file.parent / 'privacy_report.html'
            EnhancedHTMLGenerator.generate_privacy_report(
                results_file, 
                privacy_output, 
                epsilon
            )
            
            # Generate utility report
            utility_output = results_file.parent / 'utility_report.html'
            EnhancedHTMLGenerator.generate_utility_report(
                results_file,
                utility_output,
                epsilon
            )
            
            success_count += 1
            print(f"  ✅ Generated reports for: {results_file.parent.name}")
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error processing {results_file}: {e}")
    
    print(f"\n📊 Report Generation Summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Errors: {error_count}")


def generate_dashboards(results_dir: Path, dashboards_dir: Path) -> None:
    """Generate cross-experiment dashboards."""
    print("\n🎨 Generating cross-experiment dashboards...")
    
    dashboards_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate main cross-experiment dashboard
    main_dashboard = dashboards_dir / 'cross_experiment_analysis.html'
    CrossGroupDashboard.generate_cross_experiment_dashboard(
        results_dir,
        main_dashboard
    )
    
    print(f"✨ Main dashboard: {main_dashboard}")


def main():
    """Main execution."""
    # Determine paths
    script_dir = Path(__file__).parent
    experiments_dir = script_dir.parent
    results_dir = experiments_dir / 'results'
    dashboards_dir = experiments_dir / 'dashboards'
    
    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        return
    
    # Regenerate individual reports
    regenerate_all_reports(results_dir)
    
    # Generate cross-experiment dashboards
    generate_dashboards(results_dir, dashboards_dir)
    
    print("\n🎉 All done! Your reports are ready to wow!")
    print(f"\n📍 Check out:")
    print(f"  • Individual reports in: {results_dir}")
    print(f"  • Cross-experiment dashboard: {dashboards_dir / 'cross_experiment_analysis.html'}")


if __name__ == '__main__':
    main()
