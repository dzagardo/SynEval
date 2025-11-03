# experiments/utils/cross_group_dashboard_generator.py
#!/usr/bin/env python3
"""
Cross-Group Comparison Dashboard Generator
===========================================
Generates beautiful, interactive HTML dashboards comparing experiments
across different groups (e.g., Row DP vs Window DP).
"""

import json
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .privacy_scoring import compute_privacy_summary


class CrossGroupDashboardGenerator:
    """
    Generates stunning HTML dashboards for cross-group comparisons.
    Compares different DP methods across all epsilon values.
    """
    
    def __init__(self):
        """Initialize the dashboard generator."""
        self.primary_color = "#667eea"
        self.secondary_color = "#764ba2"
        self.success_color = "#28a745"
        self.warning_color = "#ffc107"
        self.danger_color = "#dc3545"
        self.info_color = "#17a2b8"
        self.group_colors = [
            "#667eea", "#f093fb", "#4facfe", "#43e97b", "#fa709a",
            "#30cfd0", "#764ba2", "#f5576c", "#00f2fe", "#38f9d7"
        ]
        
    def generate(self, all_results: Dict[str, List[Dict]], comparison_name: str = "Cross-Group DP Comparison") -> str:
        """
        Generate a complete HTML dashboard for cross-group comparison.
        
        Args:
            all_results: Dictionary mapping group names to lists of results
            comparison_name: Name for this comparison
            
        Returns:
            Complete HTML content as a string
        """
        # Process and organize data
        processed_groups = self._process_groups(all_results)
        if not processed_groups:
            return self._empty_dashboard(comparison_name)
        
        # Generate visualization components
        header_section = self._generate_header(comparison_name, len(processed_groups))
        overview_section = self._generate_overview(processed_groups)
        method_comparison = self._generate_method_comparison(processed_groups)
        epsilon_analysis = self._generate_epsilon_analysis(processed_groups)
        best_configs = self._generate_best_configurations(processed_groups)
        tradeoff_analysis = self._generate_tradeoff_analysis(processed_groups)
        recommendations = self._generate_recommendations(processed_groups)
        
        # Build complete HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{comparison_name}</title>
    
    <!-- External Libraries -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        {self._generate_styles()}
    </style>
</head>
<body>
    <!-- Animated Background -->
    <div class="animated-bg">
        <div class="wave"></div>
        <div class="wave"></div>
        <div class="wave"></div>
    </div>
    
    <!-- Header -->
    {header_section}
    
    <!-- Main Content -->
    <main class="container-fluid my-4">
        <!-- Overview Section -->
        {overview_section}
        
        <!-- Method Comparison -->
        <section class="analysis-section">
            <h2 class="section-title">
                <i class="fas fa-code-branch me-3"></i>
                Method Comparison Across All Epsilons
            </h2>
            {method_comparison}
        </section>
        
        <!-- Epsilon-specific Analysis -->
        <section class="analysis-section">
            <h2 class="section-title">
                <i class="fas fa-sliders-h me-3"></i>
                Epsilon-Specific Performance
            </h2>
            {epsilon_analysis}
        </section>
        
        <!-- Best Configurations -->
        <section class="analysis-section">
            <h2 class="section-title">
                <i class="fas fa-trophy me-3"></i>
                Best Configurations
            </h2>
            {best_configs}
        </section>
        
        <!-- Tradeoff Analysis -->
        <section class="analysis-section">
            <h2 class="section-title">
                <i class="fas fa-balance-scale-right me-3"></i>
                Privacy-Utility Tradeoff Analysis
            </h2>
            {tradeoff_analysis}
        </section>
        
        <!-- Recommendations -->
        <section class="analysis-section">
            <h2 class="section-title">
                <i class="fas fa-lightbulb me-3"></i>
                Insights & Recommendations
            </h2>
            {recommendations}
        </section>
    </main>
    
    <!-- Footer -->
    <footer class="dashboard-footer">
        <div class="container-fluid">
            <div class="row">
                <div class="col-12 text-center">
                    <p class="mb-0">
                        <i class="fas fa-layer-group me-2"></i>
                        {comparison_name}
                        <span class="mx-2">•</span>
                        Generated {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                    </p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        {self._generate_scripts(processed_groups)}
    </script>
</body>
</html>
"""
        return html
    
    def _empty_dashboard(self, comparison_name: str) -> str:
        """Render a minimal dashboard when no successful experiments exist."""
        styles = self._generate_styles()
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{comparison_name}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        {styles}
        body {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }}
        .empty-state {{
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 600px;
            width: 100%;
        }}
        .empty-state h1 {{
            font-size: 1.75rem;
            margin-bottom: 1rem;
            color: #2d3436;
        }}
        .empty-state p {{
            color: #495057;
            margin-bottom: 0;
        }}
    </style>
</head>
<body>
    <div class="empty-state">
        <h1><i class="fas fa-info-circle me-2 text-info"></i>No Successful Experiments</h1>
        <p>Unable to generate the cross-group comparison because no experiments completed successfully across the selected groups.</p>
        <p class="mt-3 text-muted">Generated {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
    </div>
</body>
</html>
"""
    
    def _generate_styles(self) -> str:
        """Generate CSS styles for the dashboard."""
        return """
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #17a2b8;
            --dark: #2d3436;
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-tertiary: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --gradient-success: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f4f6f9;
            min-height: 100vh;
            position: relative;
        }
        
        /* Animated Wave Background */
        .animated-bg {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -1;
            overflow: hidden;
        }
        
        .wave {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 100px;
            background: url('data:image/svg+xml;utf8,<svg viewBox="0 0 1200 120" xmlns="http://www.w3.org/2000/svg"><path d="M321.39,56.44c58-10.79,114.16-30.13,172-41.86,82.39-16.72,168.19-17.73,250.45-.39C823.78,31,906.67,72,985.66,92.83c70.05,18.48,146.53,26.09,214.34,3V0H0V27.35A600.21,600.21,0,0,0,321.39,56.44Z" fill="%23667eea" opacity="0.3"/></svg>') repeat-x;
            animation: wave 10s cubic-bezier(0.36, 0.45, 0.63, 0.53) infinite;
        }
        
        .wave:nth-of-type(2) {
            bottom: 10px;
            opacity: 0.5;
            animation: wave 7s cubic-bezier(0.36, 0.45, 0.63, 0.53) -0.125s infinite;
        }
        
        .wave:nth-of-type(3) {
            bottom: 20px;
            opacity: 0.2;
            animation: wave 12s cubic-bezier(0.36, 0.45, 0.63, 0.53) 0.25s infinite;
        }
        
        @keyframes wave {
            0% { transform: translateX(0); }
            100% { transform: translateX(-1200px); }
        }
        
        /* Header */
        .dashboard-header {
            background: var(--gradient-primary);
            color: white;
            padding: 4rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            position: relative;
        }
        
        .dashboard-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);
        }
        
        .group-count-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            padding: 0.75rem 1.5rem;
            border-radius: 30px;
            font-weight: 600;
            margin-top: 1rem;
        }
        
        /* Analysis Sections */
        .analysis-section {
            background: white;
            border-radius: 20px;
            padding: 3rem;
            margin-bottom: 2rem;
            box-shadow: 0 5px 30px rgba(0, 0, 0, 0.08);
        }
        
        .section-title {
            font-size: 1.875rem;
            font-weight: 700;
            margin-bottom: 2rem;
            color: var(--dark);
            display: flex;
            align-items: center;
        }
        
        .section-title i {
            color: var(--primary);
        }
        
        /* Overview Grid */
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .group-card {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .group-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }
        
        .group-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: var(--gradient-primary);
        }
        
        .group-card.best::before {
            background: var(--gradient-success);
        }
        
        .group-name {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--dark);
        }
        
        .group-stats {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .stat-label {
            color: #6c757d;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .stat-value {
            font-weight: 700;
            font-size: 1.125rem;
        }
        
        /* Method Comparison Charts */
        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
        }
        
        .chart-header {
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #f0f2f5;
        }
        
        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--dark);
        }
        
        .chart-subtitle {
            color: #6c757d;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
        
        /* Best Configuration Cards */
        .best-config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }
        
        .best-config-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border-radius: 15px;
            padding: 1.5rem;
            text-align: center;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        
        .best-config-card:hover {
            border-color: var(--primary);
            transform: scale(1.02);
        }
        
        .trophy-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .gold { color: #FFD700; }
        .silver { color: #C0C0C0; }
        .bronze { color: #CD7F32; }
        
        .config-metric {
            font-size: 0.875rem;
            color: #6c757d;
            margin-bottom: 0.5rem;
        }
        
        .config-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .config-details {
            margin-top: 1rem;
            font-size: 0.875rem;
            color: #495057;
        }
        
        /* Comparison Tables */
        .comparison-matrix {
            overflow-x: auto;
        }
        
        .matrix-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .matrix-table thead {
            background: var(--gradient-primary);
            color: white;
        }
        
        .matrix-table th {
            padding: 1rem;
            font-weight: 600;
            text-align: center;
            border: none;
        }
        
        .matrix-table td {
            padding: 1rem;
            text-align: center;
            background: white;
            border: 1px solid #e9ecef;
        }
        
        .matrix-table tbody tr:hover {
            background: rgba(102, 126, 234, 0.05);
        }
        
        /* Score Cells */
        .score-cell {
            font-weight: 600;
            padding: 0.5rem;
            border-radius: 8px;
        }
        
        .score-excellent {
            background: rgba(40, 167, 69, 0.1);
            color: var(--success);
        }
        
        .score-good {
            background: rgba(23, 162, 184, 0.1);
            color: var(--info);
        }
        
        .score-fair {
            background: rgba(255, 193, 7, 0.1);
            color: var(--warning);
        }
        
        .score-poor {
            background: rgba(220, 53, 69, 0.1);
            color: var(--danger);
        }
        
        .score-missing {
            background: rgba(108, 117, 125, 0.1);
            color: #6c757d;
            font-style: italic;
        }
        
        /* Epsilon Tabs */
        .epsilon-tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        
        .epsilon-tab {
            padding: 0.75rem 1.5rem;
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 30px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .epsilon-tab:hover {
            background: rgba(102, 126, 234, 0.1);
            border-color: var(--primary);
        }
        
        .epsilon-tab.active {
            background: var(--gradient-primary);
            color: white;
            border-color: transparent;
        }
        
        /* Insights & Recommendations */
        .insight-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
            border-left: 4px solid var(--primary);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        .insight-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .insight-icon {
            width: 40px;
            height: 40px;
            background: var(--gradient-primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        .insight-title {
            font-weight: 700;
            color: var(--dark);
            font-size: 1.125rem;
        }
        
        .insight-content {
            color: #495057;
            line-height: 1.6;
        }
        
        /* Legend */
        .legend-container {
            display: flex;
            gap: 2rem;
            justify-content: center;
            margin: 2rem 0;
            flex-wrap: wrap;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .legend-color {
            width: 30px;
            height: 15px;
            border-radius: 3px;
        }
        
        /* Footer */
        .dashboard-footer {
            background: var(--dark);
            color: white;
            padding: 2rem 0;
            margin-top: 4rem;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .overview-grid {
                grid-template-columns: 1fr;
            }
            
            .best-config-grid {
                grid-template-columns: 1fr;
            }
            
            .epsilon-tabs {
                justify-content: center;
            }
        }
        
        /* Animations */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in {
            animation: fadeIn 0.6s ease-out forwards;
        }
        """
    
    def _generate_header(self, comparison_name: str, num_groups: int) -> str:
        """Generate the header section."""
        return f"""
        <header class="dashboard-header">
            <div class="container-fluid">
                <div class="text-center">
                    <h1 class="display-4 mb-3">
                        <i class="fas fa-layer-group me-3"></i>
                        {comparison_name}
                    </h1>
                    <p class="lead mb-3">
                        Comprehensive Cross-Group Performance Analysis
                    </p>
                    <div class="group-count-badge">
                        <i class="fas fa-project-diagram"></i>
                        <span>{num_groups} Methods Compared</span>
                    </div>
                </div>
            </div>
        </header>
        """
    
    def _generate_overview(self, processed_groups: Dict) -> str:
        """Generate overview section with group summaries."""
        if not processed_groups:
            return """
            <div class="alert alert-warning mt-3">
                <i class="fas fa-info-circle me-2"></i>
                No successful experiments were found for cross-group comparison.
            </div>
            """
        
        html = '<div class="overview-grid">'
        
        best_overall_group = self._find_best_overall_group(processed_groups)
        
        for group_name, group_data in processed_groups.items():
            is_best = best_overall_group is not None and group_name == best_overall_group
            card_class = "group-card best" if is_best else "group-card"
            avg_scores = group_data['average_scores']
            fidelity_color, fidelity_display = self._score_color_and_display(avg_scores.get('fidelity'))
            utility_color, utility_display = self._score_color_and_display(avg_scores.get('utility'))
            privacy_color, privacy_display = self._score_color_and_display(avg_scores.get('privacy'))
            overall_color, overall_display = self._score_color_and_display(avg_scores.get('overall'))
            experiment_count = len(group_data.get('results', []))

            html += f"""
            <div class="{card_class}">
                <div class="group-name">
                    {group_name}
                    {' <i class="fas fa-crown text-warning ms-2"></i>' if is_best else ''}
                </div>
                <div class="group-stats">
                    <div class="stat-row">
                        <span class="stat-label">Experiments</span>
                        <span class="stat-value">{experiment_count}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Avg Fidelity</span>
                        <span class="stat-value" style="color: {fidelity_color}">
                            {fidelity_display}
                        </span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Avg Utility</span>
                        <span class="stat-value" style="color: {utility_color}">
                            {utility_display}
                        </span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Avg Privacy</span>
                        <span class="stat-value" style="color: {privacy_color}">
                            {privacy_display}
                        </span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Overall Score</span>
                        <span class="stat-value" style="color: {overall_color}">
                            <strong>{overall_display}</strong>
                        </span>
                    </div>
                </div>
            </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_method_comparison(self, processed_groups: Dict) -> str:
        """Generate method comparison visualizations."""
        html = '<div class="row">'
        
        # Overall comparison chart
        html += """
        <div class="col-12">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Overall Performance Comparison</div>
                    <div class="chart-subtitle">Average scores across all epsilon values</div>
                </div>
                <div id="overall-comparison-chart" style="height: 400px;"></div>
            </div>
        </div>
        """
        
        # Detailed metric comparison
        html += """
        <div class="col-lg-6">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Privacy vs Utility Scatter</div>
                    <div class="chart-subtitle">Each point represents a configuration</div>
                </div>
                <div id="privacy-utility-scatter" style="height: 400px;"></div>
            </div>
        </div>
        """
        
        html += """
        <div class="col-lg-6">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Fidelity vs Diversity Scatter</div>
                    <div class="chart-subtitle">Trade-offs between data quality metrics</div>
                </div>
                <div id="fidelity-diversity-scatter" style="height: 400px;"></div>
            </div>
        </div>
        """
        
        html += '</div>'
        
        # Comparison matrix table
        html += self._generate_comparison_matrix(processed_groups)
        
        return html
    
    def _generate_epsilon_analysis(self, processed_groups: Dict) -> str:
        """Generate epsilon-specific analysis."""
        # Get all unique epsilons
        all_epsilons = set()
        for group_data in processed_groups.values():
            for result in group_data['results']:
                all_epsilons.add(result.get('epsilon', 'Unknown'))
        
        sorted_epsilons = sorted(all_epsilons, key=lambda x: float('inf') if x in ['Inf', 'Unknown'] else float(x))
        
        # Generate epsilon tabs
        html = '<div class="epsilon-tabs">'
        for i, epsilon in enumerate(sorted_epsilons):
            active_class = 'active' if i == 0 else ''
            html += f'<div class="epsilon-tab {active_class}" data-epsilon="{epsilon}">ε = {epsilon}</div>'
        html += '</div>'
        
        # Charts for epsilon-specific comparison
        html += '<div id="epsilon-specific-charts">'
        html += '<div class="row">'
        html += """
        <div class="col-lg-12">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Performance at Selected Epsilon</div>
                    <div class="chart-subtitle">Comparing all methods at the same privacy budget</div>
                </div>
                <div id="epsilon-performance-chart" style="height: 400px;"></div>
            </div>
        </div>
        """
        html += '</div>'
        html += '</div>'
        
        return html
    
    def _generate_best_configurations(self, processed_groups: Dict) -> str:
        """Generate best configurations section."""
        # Find best configurations across all groups
        best_configs = self._find_best_configurations(processed_groups)
        
        html = '<div class="best-config-grid">'
        
        # Best Overall
        if best_configs['overall']:
            config = best_configs['overall']
            html += f"""
            <div class="best-config-card">
                <div class="trophy-icon gold">
                    <i class="fas fa-trophy"></i>
                </div>
                <div class="config-metric">Best Overall</div>
                <div class="config-value">{config['score']:.1f}%</div>
                <div class="config-details">
                    <strong>{config['group']}</strong><br>
                    ε = {config['epsilon']}
                </div>
            </div>
            """
        
        # Best Privacy
        if best_configs['privacy']:
            config = best_configs['privacy']
            html += f"""
            <div class="best-config-card">
                <div class="trophy-icon silver">
                    <i class="fas fa-shield-alt"></i>
                </div>
                <div class="config-metric">Best Privacy</div>
                <div class="config-value">{config['score']:.1f}%</div>
                <div class="config-details">
                    <strong>{config['group']}</strong><br>
                    ε = {config['epsilon']}
                </div>
            </div>
            """
        
        # Best Utility
        if best_configs['utility']:
            config = best_configs['utility']
            html += f"""
            <div class="best-config-card">
                <div class="trophy-icon bronze">
                    <i class="fas fa-cogs"></i>
                </div>
                <div class="config-metric">Best Utility</div>
                <div class="config-value">{config['score']:.1f}%</div>
                <div class="config-details">
                    <strong>{config['group']}</strong><br>
                    ε = {config['epsilon']}
                </div>
            </div>
            """
        
        # Best Fidelity
        if best_configs['fidelity']:
            config = best_configs['fidelity']
            html += f"""
            <div class="best-config-card">
                <div class="trophy-icon bronze">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="config-metric">Best Fidelity</div>
                <div class="config-value">{config['score']:.1f}%</div>
                <div class="config-details">
                    <strong>{config['group']}</strong><br>
                    ε = {config['epsilon']}
                </div>
            </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_comparison_matrix(self, processed_groups: Dict) -> str:
        """Generate comparison matrix table."""
        html = '<div class="comparison-matrix mt-4">'
        html += '<table class="matrix-table">'
        html += '<thead>'
        html += '<tr>'
        html += '<th>Method</th>'
        html += '<th>Epsilon</th>'
        html += '<th>Fidelity</th>'
        html += '<th>Utility</th>'
        html += '<th>Privacy</th>'
        html += '<th>Diversity</th>'
        html += '<th>Overall</th>'
        html += '</tr>'
        html += '</thead>'
        html += '<tbody>'
        
        for group_name, group_data in processed_groups.items():
            for result in group_data.get('results', []):
                epsilon = result.get('epsilon', 'Unknown')
                scores = self._calculate_scores(result)
                fidelity_class, fidelity_display = self._score_cell(scores['fidelity'])
                utility_class, utility_display = self._score_cell(scores['utility'])
                privacy_class, privacy_display = self._score_cell(scores['privacy'])
                diversity_class, diversity_display = self._score_cell(scores['diversity'])
                overall_class, overall_display = self._score_cell(scores['overall'])

                html += '<tr>'
                html += f'<td><strong>{group_name}</strong></td>'
                html += f'<td>{epsilon}</td>'
                html += f'<td class="{fidelity_class}">{fidelity_display}</td>'
                html += f'<td class="{utility_class}">{utility_display}</td>'
                html += f'<td class="{privacy_class}">{privacy_display}</td>'
                html += f'<td class="{diversity_class}">{diversity_display}</td>'
                html += f'<td class="{overall_class}"><strong>{overall_display}</strong></td>'
                html += '</tr>'
        
        html += '</tbody>'
        html += '</table>'
        html += '</div>'
        
        return html
    
    def _generate_tradeoff_analysis(self, processed_groups: Dict) -> str:
        """Generate privacy-utility tradeoff analysis."""
        html = '<div class="row">'
        
        # Pareto frontier chart
        html += """
        <div class="col-lg-12">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Privacy-Utility Pareto Frontier</div>
                    <div class="chart-subtitle">Optimal configurations across all methods</div>
                </div>
                <div id="pareto-frontier-chart" style="height: 500px;"></div>
            </div>
        </div>
        """
        
        # Method-specific tradeoff curves
        html += """
        <div class="col-lg-12">
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-title">Method-Specific Tradeoff Curves</div>
                    <div class="chart-subtitle">How each method handles the privacy-utility balance</div>
                </div>
                <div id="method-tradeoff-curves" style="height: 500px;"></div>
            </div>
        </div>
        """
        
        html += '</div>'
        return html
    
    def _generate_recommendations(self, processed_groups: Dict) -> str:
        """Generate insights and recommendations."""
        insights = self._analyze_groups(processed_groups)
        
        html = ''
        for insight in insights:
            html += f"""
            <div class="insight-card">
                <div class="insight-header">
                    <div class="insight-icon">
                        <i class="fas fa-{insight['icon']}"></i>
                    </div>
                    <div class="insight-title">{insight['title']}</div>
                </div>
                <div class="insight-content">
                    {insight['content']}
                </div>
            </div>
            """
        
        return html
    
    def _generate_scripts(self, processed_groups: Dict) -> str:
        """Generate JavaScript for all visualizations."""
        # Prepare data for charts
        group_names = list(processed_groups.keys())
        colors = self.group_colors[:len(group_names)]
        
        # Overall comparison data
        avg_fidelity = [processed_groups[g]['average_scores']['fidelity'] for g in group_names]
        avg_utility = [processed_groups[g]['average_scores']['utility'] for g in group_names]
        avg_privacy = [processed_groups[g]['average_scores']['privacy'] for g in group_names]
        avg_diversity = [processed_groups[g]['average_scores']['diversity'] for g in group_names]
        avg_overall = [processed_groups[g]['average_scores']['overall'] for g in group_names]

        avg_fidelity_json = json.dumps(avg_fidelity)
        avg_utility_json = json.dumps(avg_utility)
        avg_privacy_json = json.dumps(avg_privacy)
        avg_diversity_json = json.dumps(avg_diversity)
        avg_overall_json = json.dumps(avg_overall)
        
        return f"""
        document.addEventListener('DOMContentLoaded', function() {{
            const groupColors = {colors};
            const groupNames = {group_names};
            
            // Overall Comparison Chart
            var overallData = [
                {{
                    x: groupNames,
                    y: {avg_fidelity_json},
                    name: 'Fidelity',
                    type: 'bar',
                    marker: {{color: 'rgba(102, 126, 234, 0.8)'}}
                }},
                {{
                    x: groupNames,
                    y: {avg_utility_json},
                    name: 'Utility',
                    type: 'bar',
                    marker: {{color: 'rgba(23, 162, 184, 0.8)'}}
                }},
                {{
                    x: groupNames,
                    y: {avg_privacy_json},
                    name: 'Privacy',
                    type: 'bar',
                    marker: {{color: 'rgba(40, 167, 69, 0.8)'}}
                }},
                {{
                    x: groupNames,
                    y: {avg_diversity_json},
                    name: 'Diversity',
                    type: 'bar',
                    marker: {{color: 'rgba(255, 193, 7, 0.8)'}}
                }},
                {{
                    x: groupNames,
                    y: {avg_overall_json},
                    name: 'Overall',
                    type: 'bar',
                    marker: {{color: 'rgba(220, 53, 69, 0.8)'}}
                }}
            ];
            
            var overallLayout = {{
                barmode: 'group',
                yaxis: {{title: 'Score (%)', range: [0, 105]}},
                xaxis: {{title: 'Method'}},
                hovermode: 'x unified',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}}
            }};
            
            Plotly.newPlot('overall-comparison-chart', overallData, overallLayout, {{responsive: true}});
            
            // Scatter Plots
            {self._generate_scatter_plots(processed_groups)}
            
            // Epsilon-specific charts
            {self._generate_epsilon_charts(processed_groups)}
            
            // Pareto Frontier
            {self._generate_pareto_frontier(processed_groups)}
            
            // Method Tradeoff Curves
            {self._generate_tradeoff_curves(processed_groups)}
            
            // Epsilon tab interactions
            document.querySelectorAll('.epsilon-tab').forEach(tab => {{
                tab.addEventListener('click', function() {{
                    document.querySelectorAll('.epsilon-tab').forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    const selectedEpsilon = this.dataset.epsilon;
                    updateEpsilonChart(selectedEpsilon);
                }});
            }});
            
            // Initial epsilon chart
            const firstEpsilon = document.querySelector('.epsilon-tab.active').dataset.epsilon;
            updateEpsilonChart(firstEpsilon);
            
            function updateEpsilonChart(epsilon) {{
                {self._generate_epsilon_update_function(processed_groups)}
            }}
            
            // Animation on scroll
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        entry.target.classList.add('fade-in');
                    }}
                }});
            }}, {{threshold: 0.1}});
            
            document.querySelectorAll('.chart-container').forEach(el => {{
                observer.observe(el);
            }});
        }});
        """
    
    def _generate_scatter_plots(self, processed_groups: Dict) -> str:
        """Generate scatter plot data."""
        script = """
        // Privacy vs Utility Scatter
        var privacyUtilityData = [];
        """
        
        for i, (group_name, group_data) in enumerate(processed_groups.items()):
            privacy_scores = []
            utility_scores = []
            epsilons = []
            
            for result in group_data['results']:
                scores = self._calculate_scores(result)
                if self._is_number(scores['privacy']) and self._is_number(scores['utility']):
                    privacy_scores.append(float(scores['privacy']))
                    utility_scores.append(float(scores['utility']))
                    epsilons.append(result.get('epsilon', 'Unknown'))
            
            script += f"""
            privacyUtilityData.push({{
                x: {json.dumps(privacy_scores)},
                y: {json.dumps(utility_scores)},
                mode: 'markers+lines',
                type: 'scatter',
                name: '{group_name}',
                text: {json.dumps(epsilons)},
                marker: {{
                    size: 10,
                    color: groupColors[{i}]
                }},
                line: {{
                    color: groupColors[{i}],
                    width: 2
                }}
            }});
            """
        
        script += """
        var scatterLayout = {
            xaxis: {title: 'Privacy Score (%)'},
            yaxis: {title: 'Utility Score (%)'},
            hovermode: 'closest',
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'rgba(0,0,0,0.02)',
            font: {family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}
        };
        
        Plotly.newPlot('privacy-utility-scatter', privacyUtilityData, scatterLayout, {responsive: true});
        """
        
        # Similar for fidelity-diversity scatter
        script += """
        // Fidelity vs Diversity Scatter
        var fidelityDiversityData = [];
        """
        
        for i, (group_name, group_data) in enumerate(processed_groups.items()):
            fidelity_scores = []
            diversity_scores = []
            
            for result in group_data['results']:
                scores = self._calculate_scores(result)
                if self._is_number(scores['fidelity']) and self._is_number(scores['diversity']):
                    fidelity_scores.append(float(scores['fidelity']))
                    diversity_scores.append(float(scores['diversity']))
            
            script += f"""
            fidelityDiversityData.push({{
                x: {json.dumps(fidelity_scores)},
                y: {json.dumps(diversity_scores)},
                mode: 'markers+lines',
                type: 'scatter',
                name: '{group_name}',
                marker: {{
                    size: 10,
                    color: groupColors[{i}]
                }},
                line: {{
                    color: groupColors[{i}],
                    width: 2
                }}
            }});
            """
        
        script += """
        var fidelityDiversityLayout = {
            xaxis: {title: 'Fidelity Score (%)'},
            yaxis: {title: 'Diversity Score (%)'},
            hovermode: 'closest',
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'rgba(0,0,0,0.02)',
            font: {family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}
        };
        
        Plotly.newPlot('fidelity-diversity-scatter', fidelityDiversityData, fidelityDiversityLayout, {responsive: true});
        """
        
        return script
    
    def _generate_epsilon_charts(self, processed_groups: Dict) -> str:
        """Generate epsilon-specific chart data."""
        # Collect all unique epsilons
        all_epsilons = set()
        for group_data in processed_groups.values():
            for result in group_data['results']:
                all_epsilons.add(result.get('epsilon', 'Unknown'))
        
        script = """
        const epsilonData = {};
        """
        
        for epsilon in all_epsilons:
            epsilon_groups = []
            epsilon_scores = {'fidelity': [], 'utility': [], 'privacy': [], 'diversity': [], 'overall': []}
            
            for group_name, group_data in processed_groups.items():
                for result in group_data['results']:
                    if result.get('epsilon') == epsilon:
                        epsilon_groups.append(group_name)
                        scores = self._calculate_scores(result)
                        for metric in epsilon_scores:
                            value = scores[metric]
                            epsilon_scores[metric].append(float(value) if self._is_number(value) else None)
                        break
            
            script += f"""
            epsilonData['{epsilon}'] = {{
                groups: {json.dumps(epsilon_groups)},
                fidelity: {json.dumps(epsilon_scores['fidelity'])},
                utility: {json.dumps(epsilon_scores['utility'])},
                privacy: {json.dumps(epsilon_scores['privacy'])},
                diversity: {json.dumps(epsilon_scores['diversity'])},
                overall: {json.dumps(epsilon_scores['overall'])}
            }};
            """
        
        return script
    
    def _generate_epsilon_update_function(self, processed_groups: Dict) -> str:
        """Generate function to update epsilon-specific chart."""
        return """
        const data = epsilonData[epsilon];
        if (!data) return;
        
        var traces = [
            {
                x: data.groups,
                y: data.fidelity,
                name: 'Fidelity',
                type: 'bar',
                marker: {color: 'rgba(102, 126, 234, 0.8)'}
            },
            {
                x: data.groups,
                y: data.utility,
                name: 'Utility',
                type: 'bar',
                marker: {color: 'rgba(23, 162, 184, 0.8)'}
            },
            {
                x: data.groups,
                y: data.privacy,
                name: 'Privacy',
                type: 'bar',
                marker: {color: 'rgba(40, 167, 69, 0.8)'}
            },
            {
                x: data.groups,
                y: data.diversity,
                name: 'Diversity',
                type: 'bar',
                marker: {color: 'rgba(255, 193, 7, 0.8)'}
            }
        ];
        
        var layout = {
            title: `Performance at ε = ${epsilon}`,
            barmode: 'group',
            yaxis: {title: 'Score (%)', range: [0, 105]},
            xaxis: {title: 'Method'},
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'rgba(0,0,0,0.02)',
            font: {family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}
        };
        
        Plotly.newPlot('epsilon-performance-chart', traces, layout, {responsive: true});
        """
    
    def _generate_pareto_frontier(self, processed_groups: Dict) -> str:
        """Generate Pareto frontier visualization."""
        # Calculate Pareto optimal points
        all_points = []
        for group_name, group_data in processed_groups.items():
            for result in group_data['results']:
                scores = self._calculate_scores(result)
                if self._is_number(scores['privacy']) and self._is_number(scores['utility']):
                    all_points.append({
                        'group': group_name,
                        'epsilon': result.get('epsilon', 'Unknown'),
                        'privacy': float(scores['privacy']),
                        'utility': float(scores['utility'])
                    })
        
        # Find Pareto optimal points
        pareto_points = self._find_pareto_optimal(all_points)
        
        script = """
        // Pareto Frontier Chart
        var paretoData = [];
        
        // All points
        """
        
        for i, (group_name, group_data) in enumerate(processed_groups.items()):
            privacy_scores = []
            utility_scores = []
            texts = []
            
            for result in group_data['results']:
                scores = self._calculate_scores(result)
                if self._is_number(scores['privacy']) and self._is_number(scores['utility']):
                    privacy_scores.append(float(scores['privacy']))
                    utility_scores.append(float(scores['utility']))
                    texts.append(f"ε={result.get('epsilon', 'Unknown')}")
            
            script += f"""
            paretoData.push({{
                x: {json.dumps(privacy_scores)},
                y: {json.dumps(utility_scores)},
                mode: 'markers',
                type: 'scatter',
                name: '{group_name}',
                text: {json.dumps(texts)},
                marker: {{
                    size: 10,
                    color: groupColors[{i}],
                    opacity: 0.6
                }}
            }});
            """
        
        # Add Pareto frontier line
        if pareto_points:
            pareto_x = [p['privacy'] for p in pareto_points]
            pareto_y = [p['utility'] for p in pareto_points]
            pareto_text = [f"{p['group']} (ε={p['epsilon']})" for p in pareto_points]
            
            script += f"""
            paretoData.push({{
                x: {json.dumps(pareto_x)},
                y: {json.dumps(pareto_y)},
                mode: 'markers+lines',
                type: 'scatter',
                name: 'Pareto Frontier',
                text: {json.dumps(pareto_text)},
                marker: {{
                    size: 15,
                    color: 'red',
                    symbol: 'star'
                }},
                line: {{
                    color: 'red',
                    width: 2,
                    dash: 'dash'
                }}
            }});
            """
        
        script += """
        var paretoLayout = {
            title: 'Pareto Optimal Configurations',
            xaxis: {title: 'Privacy Score (%)', range: [0, 105]},
            yaxis: {title: 'Utility Score (%)', range: [0, 105]},
            hovermode: 'closest',
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'rgba(0,0,0,0.02)',
            font: {family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}
        };
        
        Plotly.newPlot('pareto-frontier-chart', paretoData, paretoLayout, {responsive: true});
        """
        
        return script
    
    def _generate_tradeoff_curves(self, processed_groups: Dict) -> str:
        """Generate method-specific tradeoff curves."""
        script = """
        // Method Tradeoff Curves
        var tradeoffData = [];
        """
        
        for i, (group_name, group_data) in enumerate(processed_groups.items()):
            # Sort by epsilon for smooth curve
            sorted_results = sorted(group_data['results'], 
                                  key=lambda r: float('inf') if r.get('epsilon') == 'Inf' else float(r.get('epsilon', 0)))
            
            privacy_scores = []
            utility_scores = []
            
            for result in sorted_results:
                scores = self._calculate_scores(result)
                if self._is_number(scores['privacy']) and self._is_number(scores['utility']):
                    privacy_scores.append(float(scores['privacy']))
                    utility_scores.append(float(scores['utility']))

            if not privacy_scores:
                continue
            
            script += f"""
            tradeoffData.push({{
                x: {json.dumps(privacy_scores)},
                y: {json.dumps(utility_scores)},
                mode: 'lines+markers',
                type: 'scatter',
                name: '{group_name}',
                line: {{
                    color: groupColors[{i}],
                    width: 3
                }},
                marker: {{
                    size: 8,
                    color: groupColors[{i}]
                }}
            }});
            """
        
        script += """
        var tradeoffLayout = {
            title: 'Privacy-Utility Tradeoff Curves by Method',
            xaxis: {title: 'Privacy Score (%)', range: [0, 105]},
            yaxis: {title: 'Utility Score (%)', range: [0, 105]},
            hovermode: 'x unified',
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'rgba(0,0,0,0.02)',
            font: {family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}
        };
        
        Plotly.newPlot('method-tradeoff-curves', tradeoffData, tradeoffLayout, {responsive: true});
        """
        
        return script
    
    # Helper methods
    def _process_groups(self, all_results: Dict[str, List[Dict]]) -> Dict:
        """Process and organize group data."""
        processed = {}
        
        for group_name, results in all_results.items():
            valid_results = [r for r in results if r.get('status') == 'success']
            if not valid_results:
                continue
            # Calculate average scores for the group
            all_scores = {'fidelity': [], 'utility': [], 'privacy': [], 'diversity': [], 'overall': []}
            
            for result in valid_results:
                scores = self._calculate_scores(result)
                for metric in all_scores:
                    value = scores.get(metric)
                    if value is not None:
                        all_scores[metric].append(value)
            
            avg_scores = {metric: (sum(vals)/len(vals) if vals else None)
                         for metric, vals in all_scores.items()}
            
            processed[group_name] = {
                'results': valid_results,
                'average_scores': avg_scores,
                'all_scores': all_scores
            }
        
        return processed
    
    def _calculate_scores(self, result: Dict) -> Dict:
        """Calculate all metric scores for a result."""
        if result.get('status') != 'success':
            return {
                'fidelity': None,
                'utility': None,
                'privacy': None,
                'diversity': None,
                'overall': None,
                'utility_label': None,
            }
        fidelity = self._safe_get(result, 'fidelity.quality.Overall.score', 0) * 100
        utility_summary = self._utility_summary(result)
        utility = utility_summary.get("score")
        privacy = self._privacy_score_value(result)
        diversity = self._safe_get(result, 'diversity.tabular_diversity.entropy_metrics.dataset_entropy.entropy_ratio', 0) * 100
        components = [fidelity, diversity]
        if utility is not None:
            components.append(utility)
        if privacy is not None:
            components.append(privacy)
        overall = sum(components) / len(components) if components else 0
        
        return {
            'fidelity': fidelity,
            'utility': utility,
            'privacy': privacy,
            'diversity': diversity,
            'overall': overall,
            'utility_label': utility_summary.get("label"),
        }
    
    def _find_best_overall_group(self, processed_groups: Dict) -> str:
        """Find the group with best overall average score."""
        best_group = None
        best_score = -1
        
        for group_name, group_data in processed_groups.items():
            overall = group_data['average_scores']['overall']
            if self._is_number(overall) and overall > best_score:
                best_score = overall
                best_group = group_name
        
        return best_group
    
    def _find_best_configurations(self, processed_groups: Dict) -> Dict:
        """Find best configurations across all groups."""
        best = {'overall': None, 'privacy': None, 'utility': None, 'fidelity': None}
        
        for group_name, group_data in processed_groups.items():
            for result in group_data.get('results', []):
                scores = self._calculate_scores(result)
                epsilon = result.get('epsilon', 'Unknown')
                
                # Check overall
                if not best['overall'] or scores['overall'] > best['overall']['score']:
                    best['overall'] = {
                        'group': group_name,
                        'epsilon': epsilon,
                        'score': scores['overall']
                    }
                
                # Check privacy
                if scores['privacy'] is not None and (not best['privacy'] or best['privacy']['score'] is None or scores['privacy'] > best['privacy']['score']):
                    best['privacy'] = {
                        'group': group_name,
                        'epsilon': epsilon,
                        'score': scores['privacy']
                    }
                
                # Check utility
                if scores['utility'] is not None and (not best['utility'] or scores['utility'] > best['utility']['score']):
                    best['utility'] = {
                        'group': group_name,
                        'epsilon': epsilon,
                        'score': scores['utility']
                    }
                
                # Check fidelity
                if not best['fidelity'] or scores['fidelity'] > best['fidelity']['score']:
                    best['fidelity'] = {
                        'group': group_name,
                        'epsilon': epsilon,
                        'score': scores['fidelity']
                    }
        
        return best
    
    def _find_pareto_optimal(self, points: List[Dict]) -> List[Dict]:
        """Find Pareto optimal points."""
        pareto_points = []
        
        for point in points:
            is_pareto = True
            for other in points:
                if (other['privacy'] >= point['privacy'] and 
                    other['utility'] > point['utility']) or \
                   (other['privacy'] > point['privacy'] and 
                    other['utility'] >= point['utility']):
                    is_pareto = False
                    break
            
            if is_pareto:
                pareto_points.append(point)
        
        # Sort by privacy score for better line plotting
        pareto_points.sort(key=lambda p: p['privacy'])
        
        return pareto_points
    
    def _analyze_groups(self, processed_groups: Dict) -> List[Dict]:
        """Analyze groups and generate insights."""
        insights = []
        
        # Best overall method
        best_group = self._find_best_overall_group(processed_groups)
        if best_group is not None:
            best_score = processed_groups[best_group]['average_scores']['overall']
            if self._is_number(best_score):
                insights.append({
                    'icon': 'trophy',
                    'title': 'Best Overall Method',
                    'content': f'<strong>{best_group}</strong> achieves the best overall performance with an average score of {float(best_score):.1f}% across all epsilon values. This method provides the most balanced trade-off between all metrics.'
                })
        
        
        # Privacy-utility tradeoff analysis
        best_tradeoff = self._analyze_tradeoff(processed_groups)
        insights.append({
            'icon': 'balance-scale',
            'title': 'Optimal Privacy-Utility Balance',
            'content': best_tradeoff
        })
        
        # Method-specific strengths
        strengths = self._analyze_strengths(processed_groups)
        insights.append({
            'icon': 'chart-bar',
            'title': 'Method Strengths',
            'content': strengths
        })
        
        # Recommendations
        recommendation = self._generate_recommendation(processed_groups)
        insights.append({
            'icon': 'lightbulb',
            'title': 'Recommendation',
            'content': recommendation
        })
        
        return insights
    
    def _analyze_tradeoff(self, processed_groups: Dict) -> str:
        """Analyze privacy-utility tradeoff."""
        # Find configuration with best balance
        best_balance = None
        best_balance_score = -1
        
        for group_name, group_data in processed_groups.items():
            for result in group_data['results']:
                scores = self._calculate_scores(result)
                if scores['privacy'] is None or scores['utility'] is None:
                    continue
                # Balance score: high privacy and utility, minimal difference
                balance = (scores['privacy'] + scores['utility']) / 2 - abs(scores['privacy'] - scores['utility']) / 10
                
                if balance > best_balance_score:
                    best_balance_score = balance
                    best_balance = {
                        'group': group_name,
                        'epsilon': result.get('epsilon', 'Unknown'),
                        'privacy': scores['privacy'],
                        'utility': scores['utility']
                    }
        
        if best_balance:
            return f"The optimal privacy-utility balance is achieved by <strong>{best_balance['group']}</strong> at ε={best_balance['epsilon']}, with {best_balance['privacy']:.1f}% privacy and {best_balance['utility']:.1f}% utility."
        
        return "Unable to determine optimal balance configuration."
    
    def _analyze_strengths(self, processed_groups: Dict) -> str:
        """Analyze strengths of each method."""
        strengths = []
        
        for group_name, group_data in processed_groups.items():
            avg_scores = group_data['average_scores']
            valid_metrics = [(k, v) for k, v in avg_scores.items() if k != 'overall' and v is not None]
            if not valid_metrics:
                continue
            best_metric = max(valid_metrics, key=lambda x: x[1])
            strengths.append(f"<strong>{group_name}</strong>: Excels at {best_metric[0]} ({float(best_metric[1]):.1f}%)")
        
        return '<br>'.join(strengths) if strengths else "All methods show balanced performance across metrics."
    
    def _generate_recommendation(self, processed_groups: Dict) -> str:
        """Generate final recommendation."""
        best_configs = self._find_best_configurations(processed_groups)
        
        if best_configs['overall']:
            config = best_configs['overall']
            return f"""
            For most use cases, we recommend <strong>{config['group']}</strong> with ε={config['epsilon']}, 
            which achieves the best overall score of {config['score']:.1f}%. 
            This configuration provides a good balance across all evaluation metrics.
            For specific requirements (maximum privacy, highest utility, etc.), 
            refer to the best configurations section above.
            """
        
        return "Review the detailed comparisons above to select the configuration that best matches your specific requirements."
    
    def _safe_get(self, data: Dict, path: str, default: Any = None) -> Any:
        """Safely get nested dictionary values."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value if value is not None else default

    def _is_number(self, value: Any) -> bool:
        """Return True when value is numeric (and not NaN)."""
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return False
            return True
        return False

    def _extract_tstr_metrics(self, result: Dict) -> Dict[str, float]:
        """Extract numeric TSTR metrics from the legacy utility payload."""
        utility = (result or {}).get('utility') or {}
        tstr = utility.get('tstr_accuracy') or {}
        synthetic = tstr.get('synthetic_data_model') or {}
        metrics: Dict[str, float] = {}

        if isinstance(synthetic, dict):
            for key in ("r2", "rmse", "mae", "accuracy", "f1_macro", "precision_macro", "recall_macro"):
                value = synthetic.get(key)
                if self._is_number(value):
                    metrics[key] = float(value)

            macro_avg = synthetic.get("macro avg")
            if isinstance(macro_avg, dict):
                mapping = {
                    "precision": "precision_macro",
                    "recall": "recall_macro",
                    "f1-score": "f1_macro",
                }
                for source, target in mapping.items():
                    value = macro_avg.get(source)
                    if self._is_number(value):
                        metrics.setdefault(target, float(value))

            weighted_avg = synthetic.get("weighted avg")
            if isinstance(weighted_avg, dict):
                value = weighted_avg.get("f1-score")
                if self._is_number(value):
                    metrics.setdefault("f1_weighted", float(value))

        return metrics

    def _utility_summary(self, result: Dict) -> Dict[str, Any]:
        """Produce a unified view of the primary utility metric."""
        metrics = self._extract_tstr_metrics(result)
        summary: Dict[str, Any] = {
            "label": "Utility",
            "raw": None,
            "normalized": None,
            "score": None,
            "display": "N/A",
            "primary_key": None,
            "metrics": metrics,
        }

        if "r2" in metrics:
            raw = float(metrics["r2"])
            clamped = max(-1.0, min(1.0, raw))
            normalized = max(0.0, clamped)
            score = (clamped + 1.0) * 50.0
            summary.update({
                "label": "R²",
                "raw": raw,
                "normalized": normalized,
                "score": score,
                "display": f"{raw:.4f}",
                "primary_key": "r2",
            })
            return summary

        for label, key in (("Accuracy", "accuracy"), ("F1 Macro", "f1_macro"), ("Precision Macro", "precision_macro"), ("Recall Macro", "recall_macro")):
            if key in metrics:
                raw = float(metrics[key])
                normalized = max(0.0, min(1.0, raw))
                score = normalized * 100.0
                summary.update({
                    "label": label,
                    "raw": raw,
                    "normalized": normalized,
                    "score": score,
                    "display": f"{score:.2f}%",
                    "primary_key": key,
                })
                return summary

        return summary

    def _privacy_score_value(self, result: Dict) -> Optional[float]:
        """Compute privacy score from structured privacy metrics."""
        summary = compute_privacy_summary(result or {})
        return summary.get('score')

    def _score_color_and_display(self, value: Optional[float]) -> Tuple[str, str]:
        """Return a (color, display_text) tuple for percentage values."""
        if self._is_number(value):
            numeric = float(value)
            return self._get_score_color(numeric), f"{numeric:.1f}%"
        return "#6c757d", "N/A"

    def _score_cell(self, score: Optional[float]) -> Tuple[str, str]:
        """Return (css_class, display_text) for matrix cells."""
        if self._is_number(score):
            numeric = float(score)
            return self._get_score_class(numeric), f"{numeric:.1f}%"
        return "score-cell score-missing", "N/A"

    def _get_score_color(self, score: Optional[float]) -> str:
        """Get color based on score value."""
        if not self._is_number(score):
            return "#6c757d"
        score = float(score)
        if score >= 70:
            return self.success_color
        elif score >= 50:
            return self.warning_color
        else:
            return self.danger_color
    
    def _get_score_class(self, score: Optional[float]) -> str:
        """Get CSS class based on score value."""
        if not self._is_number(score):
            return "score-cell score-missing"
        score = float(score)
        if score >= 80:
            return "score-cell score-excellent"
        elif score >= 60:
            return "score-cell score-good"
        elif score >= 40:
            return "score-cell score-fair"
        else:
            return "score-cell score-poor"


if __name__ == "__main__":
    print("Cross-Group Dashboard Generator ready for use!")
