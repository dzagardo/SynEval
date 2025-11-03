# experiments/utils/in_group_dashboard_generator.py
#!/usr/bin/env python3
"""
In-Group Comparison Dashboard Generator
========================================
Generates beautiful, interactive HTML dashboards comparing experiments
within the same group (different epsilon values).
"""

import json
import math
from typing import Dict, List, Optional, Any
from datetime import datetime

from .privacy_scoring import compute_privacy_summary

class InGroupDashboardGenerator:
    """
    Generates stunning HTML dashboards for in-group comparisons (epsilon variations).
    Focuses on privacy-utility tradeoff visualization across epsilon values.
    """
    
    def __init__(self):
        """Initialize the dashboard generator."""
        self.primary_color = "#667eea"
        self.secondary_color = "#764ba2"
        self.success_color = "#28a745"
        self.warning_color = "#ffc107"
        self.danger_color = "#dc3545"
        self.info_color = "#17a2b8"
        
        # Epsilon color palette (gradient from high privacy to low privacy)
        self.epsilon_colors = [
            "#2ecc71",  # ε=1 (high privacy, green)
            "#27ae60",  # ε=10
            "#f39c12",  # ε=100 (medium privacy, orange)
            "#e67e22",  # ε=1000
            "#e74c3c",  # ε=10000 (low privacy, red)
            "#c0392b",  # ε=Inf (no privacy, dark red)
        ]
    
    def generate(self, group_results: List[Dict], group_name: str) -> str:
        """
        Generate a complete HTML dashboard for in-group comparison.
        
        Args:
            group_results: List of result dictionaries for different epsilon values
            group_name: Name of the experiment group
            
        Returns:
            Complete HTML content as a string
        """
        # Sort results by epsilon value
        group_results = self._sort_by_epsilon(group_results)
        
        # Extract epsilon values and prepare data
        epsilons = [self._get_epsilon_display(r.get('epsilon', 'Unknown')) for r in group_results]
        epsilon_values = [self._epsilon_to_float(r.get('epsilon', '1')) for r in group_results]
        finite_eps = [value for value in epsilon_values if math.isfinite(value)]
        max_finite = max(finite_eps) if finite_eps else 1.0
        adjusted_inf = max_finite * 1.1
        epsilon_numeric = [
            value if math.isfinite(value) else adjusted_inf
            for value in epsilon_values
        ]

        finite_eps = [value for value in epsilon_values if math.isfinite(value)]
        max_finite = max(finite_eps) if finite_eps else 1.0
        adjusted_inf = max_finite * 1.1
        epsilon_numeric = [
            value if math.isfinite(value) else adjusted_inf
            for value in epsilon_values
        ]

        finite_eps = [value for value in epsilon_values if math.isfinite(value)]
        max_finite = max(finite_eps) if finite_eps else 1.0
        adjusted_inf = max_finite * 1.1
        epsilon_numeric = [
            value if math.isfinite(value) else adjusted_inf
            for value in epsilon_values
        ]
        finite_eps = [value for value in epsilon_values if math.isfinite(value)]
        max_finite = max(finite_eps) if finite_eps else 1.0
        adjusted_inf = max_finite * 1.1
        epsilon_numeric = [
            value if math.isfinite(value) else adjusted_inf
            for value in epsilon_values
        ]
        
        # Generate visualization components
        header = self._generate_header(group_name, epsilons)
        overview = self._generate_overview_section(group_results)
        privacy_utility_tradeoff = self._generate_privacy_utility_tradeoff(group_results)
        metric_trends = self._generate_metric_trends(group_results)
        detailed_comparison = self._generate_detailed_comparison(group_results)
        recommendations = self._generate_recommendations(group_results)
        
        # Build the complete HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{group_name} - Epsilon Comparison</title>
    
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
        <div class="gradient-overlay"></div>
    </div>
    
    {header}
    
    <!-- Main Content -->
    <main class="container-fluid my-4">
        {overview}
        {privacy_utility_tradeoff}
        {metric_trends}
        {detailed_comparison}
        {recommendations}
    </main>
    
    <!-- Footer -->
    <footer class="dashboard-footer">
        <div class="container-fluid">
            <div class="row">
                <div class="col-12 text-center">
                    <p class="mb-0">
                        <i class="fas fa-layer-group me-2"></i>
                        In-Group Comparison Dashboard
                        <span class="mx-2">•</span>
                        Differential Privacy Epsilon Analysis
                        <span class="mx-2">•</span>
                        Generated {datetime.now().strftime("%B %d, %Y")}
                    </p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        {self._generate_scripts(group_results)}
    </script>
</body>
</html>
"""
        return html
    
    def _generate_styles(self) -> str:
        """Generate comprehensive CSS styles."""
        return """
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #17a2b8;
            --dark: #2d3436;
            --light: #f8f9fa;
            --gradient-primary: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            --gradient-epsilon: linear-gradient(135deg, #2ecc71 0%, #e74c3c 100%);
            --shadow-sm: 0 2px 10px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 20px rgba(0,0,0,0.12);
            --shadow-lg: 0 10px 40px rgba(0,0,0,0.15);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Animated Background */
        .animated-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: linear-gradient(270deg, #667eea, #764ba2, #f093fb, #f5576c);
            background-size: 800% 800%;
            animation: gradientShift 20s ease infinite;
            opacity: 0.1;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .gradient-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 30% 50%, transparent 0%, rgba(255,255,255,0.3) 100%);
        }
        
        /* Header Styles */
        .dashboard-header {
            background: var(--gradient-primary);
            color: white;
            padding: 3rem 0;
            box-shadow: var(--shadow-lg);
            position: relative;
            overflow: hidden;
        }
        
        .dashboard-header::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 100px;
            background: linear-gradient(to top, rgba(255,255,255,0.1), transparent);
        }
        
        .epsilon-badges {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 1.5rem;
        }
        
        .epsilon-badge {
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 600;
            border: 2px solid rgba(255,255,255,0.3);
            transition: var(--transition);
        }
        
        .epsilon-badge:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        /* Section Styles */
        .section-container {
            background: white;
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow-md);
            position: relative;
            overflow: hidden;
        }
        
        .section-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            background: var(--gradient-primary);
        }
        
        .section-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--dark);
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
        }
        
        .section-title i {
            margin-right: 1rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Metric Cards */
        .comparison-card {
            background: linear-gradient(135deg, white 0%, #f8f9fa 100%);
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
            position: relative;
            margin-bottom: 1.5rem;
            border: 1px solid #e9ecef;
        }
        
        .comparison-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary);
        }
        
        .epsilon-indicator {
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.875rem;
            font-weight: 700;
            background: var(--gradient-epsilon);
            color: white;
        }
        
        /* Tradeoff Visualization */
        .tradeoff-container {
            min-height: 500px;
            position: relative;
            background: linear-gradient(135deg, #f8f9fa 0%, white 100%);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: var(--shadow-sm);
        }
        
        .tradeoff-legend {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: var(--shadow-sm);
        }
        
        /* Trend Charts */
        .trend-chart {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: var(--shadow-sm);
            margin-bottom: 1.5rem;
            min-height: 400px;
        }
        
        .trend-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .trend-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--dark);
        }
        
        .trend-info {
            color: #6c757d;
            font-size: 0.875rem;
        }
        
        /* Comparison Table */
        .comparison-table {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }
        
        .comparison-table thead {
            background: var(--gradient-primary);
            color: white;
        }
        
        .comparison-table th {
            padding: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.875rem;
            letter-spacing: 0.5px;
            border: none;
        }
        
        .comparison-table td {
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.95rem;
        }
        
        .comparison-table tbody tr:hover {
            background: rgba(102, 126, 234, 0.05);
            transition: var(--transition);
        }
        
        /* Metric Value Cells */
        .metric-cell {
            font-weight: 600;
            position: relative;
        }
        
        .metric-cell.best {
            color: var(--success);
        }
        
        .metric-cell.worst {
            color: var(--danger);
        }
        
        .metric-cell.median {
            color: var(--warning);
        }
        
        .trend-indicator {
            display: inline-block;
            margin-left: 0.5rem;
            font-size: 0.875rem;
        }
        
        .trend-up {
            color: var(--success);
        }
        
        .trend-down {
            color: var(--danger);
        }
        
        /* Recommendation Cards */
        .recommendation-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border-left: 4px solid var(--primary);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .recommendation-title {
            font-weight: 600;
            color: var(--dark);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .recommendation-text {
            color: #495057;
            line-height: 1.6;
        }
        
        .optimal-epsilon {
            display: inline-block;
            background: var(--gradient-primary);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 600;
            margin: 0.5rem 0;
        }
        
        /* Interactive Elements */
        .interactive-hover {
            transition: var(--transition);
            cursor: pointer;
        }
        
        .interactive-hover:hover {
            transform: scale(1.05);
        }
        
        /* Progress Indicators */
        .progress-ring {
            transform: rotate(-90deg);
        }
        
        .progress-ring-circle {
            stroke-dasharray: 377;
            stroke-dashoffset: 377;
            animation: progressAnimation 1s ease-out forwards;
        }
        
        @keyframes progressAnimation {
            to {
                stroke-dashoffset: calc(377 - (377 * var(--progress)) / 100);
            }
        }
        
        /* Tooltips */
        .custom-tooltip {
            position: absolute;
            background: var(--dark);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.875rem;
            pointer-events: none;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .custom-tooltip.show {
            opacity: 1;
        }
        
        /* Footer */
        .dashboard-footer {
            background: var(--dark);
            color: white;
            padding: 2rem 0;
            margin-top: 4rem;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .section-container {
                padding: 1.5rem;
            }
            
            .section-title {
                font-size: 1.25rem;
            }
            
            .epsilon-badges {
                justify-content: center;
            }
            
            .tradeoff-legend {
                gap: 1rem;
            }
        }
        
        /* Loading Animation */
        .chart-loading {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 400px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        """
    
    def _generate_header(self, group_name: str, epsilons: List[str]) -> str:
        """Generate the header section."""
        return f"""
        <header class="dashboard-header">
            <div class="container-fluid">
                <div class="row">
                    <div class="col-lg-12">
                        <h1 class="display-4 mb-3">
                            <i class="fas fa-layer-group me-3"></i>
                            {group_name}
                        </h1>
                        <p class="lead mb-3">
                            Differential Privacy Analysis Across Epsilon Values
                        </p>
                        <div class="epsilon-badges">
                            {' '.join([f'<span class="epsilon-badge">ε = {eps}</span>' for eps in epsilons])}
                        </div>
                    </div>
                </div>
            </div>
        </header>
        """
    
    def _generate_overview_section(self, group_results: List[Dict]) -> str:
        """Generate the overview section with key insights."""
        utility_candidates = []
        for result in group_results:
            summary = self._utility_summary(result)
            if summary.get("score") is not None:
                utility_candidates.append((result, summary))

        if utility_candidates:
            best_utility, best_utility_summary = max(utility_candidates, key=lambda item: item[1]["score"])
        else:
            best_utility = None
            best_utility_summary = None

        privacy_candidates = []
        for result in group_results:
            summary = self._summarize_privacy_metrics(result)
            score = summary.get("score")
            if self._is_number(score):
                privacy_candidates.append((result, summary))
        if privacy_candidates:
            best_privacy, best_privacy_summary = max(privacy_candidates, key=lambda item: item[1]["score"])
        else:
            best_privacy = None
            best_privacy_summary = None

        best_privacy_eps = best_privacy.get('epsilon', 'Unknown') if best_privacy else 'N/A'
        best_utility_eps = best_utility.get('epsilon', 'Unknown') if best_utility else 'N/A'

        # Calculate average metrics across all epsilons
        avg_fidelity = sum(self._safe_get(r, 'fidelity.quality.Overall.score', 0) for r in group_results) / len(group_results) * 100
        privacy_values = [summary["score"] for _, summary in privacy_candidates]
        avg_privacy = (sum(privacy_values) / len(privacy_values)) if privacy_values else None
        
        html = """
        <section class="section-container">
            <h2 class="section-title">
                <i class="fas fa-chart-pie"></i>
                Overview & Key Insights
            </h2>
            <div class="row">
        """
        
        # Best Privacy Configuration
        if best_privacy and best_privacy_summary:
            score_value = best_privacy_summary.get("score", 0.0)
            level = best_privacy_summary.get("level", "Unknown")
            notes = best_privacy_summary.get("notes") or []
            headline = notes[0] if notes and score_value < 80 else "Best structured privacy protection"
            html += f"""
            <div class="col-md-4">
                <div class="comparison-card">
                    <h4 class="mb-3">🔒 Highest Privacy</h4>
                    <div class="display-4 text-primary mb-2">ε = {best_privacy_eps}</div>
                    <p class="text-muted mb-0">
                        Privacy Score: {score_value:.1f}%
                    </p>
                    <p class="text-muted mb-0">
                        Level: {level}
                    </p>
                    <p class="text-muted">{headline}</p>
                </div>
            </div>
        """
        else:
            html += """
            <div class=\"col-md-4\">
                <div class=\"comparison-card\">
                    <h4 class=\"mb-3\">🔒 Highest Privacy</h4>
                    <div class=\"display-6 text-muted mb-2\">N/A</div>
                    <p class=\"text-muted\">Structured privacy metrics unavailable.</p>
                </div>
            </div>
        """
        
        # Best Utility Configuration
        if best_utility and best_utility_summary:
            metric_label = best_utility_summary.get("label", "Utility")
            metric_display = best_utility_summary.get("display", "N/A")
            html += f"""
            <div class="col-md-4">
                <div class="comparison-card">
                    <h4 class="mb-3">⚡ Highest Utility</h4>
                    <div class="display-4 text-success mb-2">ε = {best_utility_eps}</div>
                    <p class="text-muted mb-0">
                        {metric_label}: {metric_display}
                    </p>
                    <p class="text-muted">
                        Best model performance on synthetic data
                    </p>
                </div>
            </div>
        """
        else:
            html += """
            <div class=\"col-md-4\">
                <div class=\"comparison-card\">
                    <h4 class=\"mb-3\">⚡ Highest Utility</h4>
                    <div class=\"display-6 text-muted mb-2\">N/A</div>
                    <p class=\"text-muted\">Utility metrics unavailable.</p>
                </div>
            </div>
        """
        
        # Recommendation
        optimal_epsilon = self._find_optimal_epsilon(group_results)
        html += f"""
            <div class="col-md-4">
                <div class="comparison-card">
                    <h4 class="mb-3">🎯 Recommended</h4>
                    <div class="display-4 text-info mb-2">ε = {optimal_epsilon}</div>
                    <p class="text-muted mb-0">
                        Balanced tradeoff
                    </p>
                    <p class="text-muted">
                        Optimal privacy-utility balance
                    </p>
                </div>
            </div>
        """
        
        html += """
            </div>
        </section>
        """
        return html
    
    def _generate_privacy_utility_tradeoff(self, group_results: List[Dict]) -> str:
        """Generate the privacy-utility tradeoff visualization."""
        return f"""
        <section class="section-container">
            <h2 class="section-title">
                <i class="fas fa-balance-scale"></i>
                Privacy-Utility Tradeoff
            </h2>
            <div class="tradeoff-container">
                <div id="privacy-utility-scatter" class="chart-loading">
                    <div class="spinner"></div>
                </div>
                <div class="tradeoff-legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: {self.success_color};"></div>
                        <span>High Privacy (Low ε)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: {self.warning_color};"></div>
                        <span>Balanced</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: {self.danger_color};"></div>
                        <span>High Utility (High ε)</span>
                    </div>
                </div>
            </div>
        </section>
        """
    
    def _generate_metric_trends(self, group_results: List[Dict]) -> str:
        """Generate metric trend visualizations."""
        html = """
        <section class="section-container">
            <h2 class="section-title">
                <i class="fas fa-chart-line"></i>
                Metric Trends Across Epsilon
            </h2>
            <div class="row">
        """
        
        # Fidelity Trend
        html += """
            <div class="col-lg-6">
                <div class="trend-chart">
                    <div class="trend-header">
                        <h4 class="trend-title">Fidelity Score Trend</h4>
                        <span class="trend-info">Quality & Diagnostic Scores</span>
                    </div>
                    <div id="fidelity-trend-chart"></div>
                </div>
            </div>
        """
        
        # Privacy Trend
        html += """
            <div class="col-lg-6">
                <div class="trend-chart">
                    <div class="trend-header">
                        <h4 class="trend-title">Privacy Protection Trend</h4>
                        <span class="trend-info">MIA Resistance (1 - AUC)</span>
                    </div>
                    <div id="privacy-trend-chart"></div>
                </div>
            </div>
        """
        
        # Utility Trend
        html += """
            <div class="col-lg-6">
                <div class="trend-chart">
                    <div class="trend-header">
                        <h4 class="trend-title">Utility Performance Trend</h4>
                        <span class="trend-info">TSTR Model Performance</span>
                    </div>
                    <div id="utility-trend-chart"></div>
                </div>
            </div>
        """
        
        # Diversity Trend
        html += """
            <div class="col-lg-6">
                <div class="trend-chart">
                    <div class="trend-header">
                        <h4 class="trend-title">Diversity Trend</h4>
                        <span class="trend-info">Entropy & Coverage</span>
                    </div>
                    <div id="diversity-trend-chart"></div>
                </div>
            </div>
        """
        
        html += """
            </div>
        </section>
        """
        return html
    
    def _generate_detailed_comparison(self, group_results: List[Dict]) -> str:
        """Generate detailed comparison table."""
        html = """
        <section class="section-container">
            <h2 class="section-title">
                <i class="fas fa-table"></i>
                Detailed Metrics Comparison
            </h2>
            <div class="table-responsive">
                <table class="table comparison-table">
                    <thead>
                        <tr>
                            <th>Epsilon (ε)</th>
                            <th>Fidelity Score</th>
                            <th>Utility Score</th>
                            <th>Privacy Score</th>
                            <th>Diversity</th>
                            <th>Exact Matches</th>
                            <th>Overall Score</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Calculate best/worst for each metric
        fidelity_scores = [self._safe_get(r, 'fidelity.quality.Overall.score', 0) for r in group_results]
        utility_summaries = [self._utility_summary(r) for r in group_results]
        utility_score_values = [s.get("score") for s in utility_summaries if self._is_number(s.get("score"))]
        privacy_summaries = [self._summarize_privacy_metrics(r) for r in group_results]
        privacy_scores = []
        for summary in privacy_summaries:
            score = summary.get("score")
            if self._is_number(score):
                privacy_scores.append(score / 100.0)
            else:
                privacy_scores.append(None)

        best_fidelity = max(fidelity_scores) if fidelity_scores else 0
        best_utility = max(utility_score_values) if utility_score_values else None
        best_privacy = max([p for p in privacy_scores if p is not None], default=None)
        
        for result, utility_summary, privacy_summary in zip(group_results, utility_summaries, privacy_summaries):
            epsilon = result.get('epsilon', 'Unknown')
            fidelity = self._safe_get(result, 'fidelity.quality.Overall.score', 0)
            privacy_score = privacy_summary.get("score")
            diversity = self._safe_get(result, 'diversity.tabular_diversity.entropy_metrics.dataset_entropy.entropy_ratio', 0)
            exact_matches = self._safe_get(result, 'privacy.exact_matches.exact_match_percentage', 0)
            utility_display = utility_summary.get("display", "N/A")
            utility_score = utility_summary.get("score")
            utility_normalized = utility_summary.get("normalized")

            if self._is_number(privacy_score):
                privacy_display = f"{privacy_score:.1f}%"
                privacy_value = (privacy_score / 100.0)
            else:
                privacy_display = "N/A"
                privacy_value = None
            
            components = [fidelity, diversity]
            if self._is_number(utility_normalized):
                components.append(float(utility_normalized))
            if privacy_value is not None:
                components.append(privacy_value)
            overall = sum(components) / len(components) if components else 0
            
            # Determine cell classes
            fidelity_class = "best" if fidelity == best_fidelity else ""
            utility_class = ""
            if best_utility is not None and self._is_number(utility_score) and abs(utility_score - best_utility) < 1e-6:
                utility_class = "best"
            privacy_class = ""
            if best_privacy is not None and privacy_value is not None and abs(privacy_value - best_privacy) < 1e-6:
                privacy_class = "best"
            
            html += f"""
                <tr>
                    <td><strong>ε = {self._get_epsilon_display(epsilon)}</strong></td>
                    <td class="metric-cell {fidelity_class}">{fidelity*100:.1f}%</td>
                    <td class="metric-cell {utility_class}">{utility_display}</td>
                    <td class="metric-cell {privacy_class}">{privacy_display}</td>
                    <td class="metric-cell">{diversity:.3f}</td>
                    <td class="metric-cell">{exact_matches:.2f}%</td>
                    <td class="metric-cell"><strong>{overall*100:.1f}%</strong></td>
                </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
            <div class="mt-3">
                <p class="text-muted">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Note:</strong> Green highlights indicate best performance for that metric.
                    The overall score is a weighted average of all metrics.
                </p>
            </div>
        </section>
        """
        return html
    
    def _generate_recommendations(self, group_results: List[Dict]) -> str:
        """Generate recommendations based on analysis."""
        optimal_epsilon = self._find_optimal_epsilon(group_results)

        privacy_summaries = [self._summarize_privacy_metrics(r) for r in group_results]
        privacy_scores = [
            (summary.get('score') / 100.0) if self._is_number(summary.get('score')) else None
            for summary in privacy_summaries
        ]
        utility_pairs = [(result, self._utility_summary(result)) for result in group_results]
        utility_candidates = [
            (result, summary)
            for result, summary in utility_pairs
            if summary.get("score") is not None
        ]
        best_utility_result = None
        best_utility_summary = None
        if utility_candidates:
            best_utility_result, best_utility_summary = max(utility_candidates, key=lambda item: item[1]["score"])

        # Find privacy threshold (where privacy drops significantly)
        privacy_threshold = None
        for i in range(1, len(privacy_scores)):
            if privacy_scores[i] is not None and privacy_scores[i-1] is not None:
                if privacy_scores[i] < 0.45 <= privacy_scores[i-1]:
                    privacy_threshold = group_results[i].get('epsilon')
                    break

        html = f"""
        <section class="section-container">
            <h2 class="section-title">
                <i class="fas fa-lightbulb"></i>
                Recommendations & Insights
            </h2>
            
            <div class="recommendation-card">
                <h4 class="recommendation-title">
                    <i class="fas fa-star text-warning"></i>
                    Optimal Configuration
                </h4>
                <div class="recommendation-text">
                    Based on the privacy-utility tradeoff analysis:
                    <span class="optimal-epsilon">Recommended: ε = {optimal_epsilon}</span>
                    <p class="mt-2">
                        This epsilon value provides the best balance between privacy protection and model utility
                        for your specific use case.
                    </p>
                </div>
            </div>
        """

        # Privacy-focused recommendation
        if privacy_threshold:
            html += f"""
            <div class="recommendation-card">
                <h4 class="recommendation-title">
                    <i class="fas fa-shield-alt text-primary"></i>
                    Privacy Consideration
                </h4>
                <div class="recommendation-text">
                    Privacy protection degrades significantly beyond <strong>ε = {privacy_threshold}</strong>.
                    If privacy is critical, consider staying below this threshold.
                </div>
            </div>
            """

        # Utility-focused recommendation
        if best_utility_result and best_utility_summary and self._is_number(best_utility_summary.get("normalized")) and best_utility_summary["normalized"] > 0.5:
            metric_label = best_utility_summary.get("label", "Utility")
            threshold_display = "0.5" if metric_label == "R²" else "50%"
            metric_display = best_utility_summary.get("display", "N/A")
            html += f"""
            <div class="recommendation-card">
                <h4 class="recommendation-title">
                    <i class="fas fa-rocket text-success"></i>
                    Utility Optimization
                </h4>
                <div class="recommendation-text">
                    Good utility performance ({metric_label} > {threshold_display}) is achieved at <strong>ε = {best_utility_result.get('epsilon')}</strong> (current {metric_label.lower()}: {metric_display}).
                    This configuration is suitable for applications where model performance is prioritized.
                </div>
            </div>
            """

        # Trend analysis
        if len(group_results) >= 3:
            trend = self._analyze_trend(group_results)
            html += f"""
            <div class="recommendation-card">
                <h4 class="recommendation-title">
                    <i class="fas fa-chart-line text-info"></i>
                    Trend Analysis
                </h4>
                <div class="recommendation-text">
                    {trend}
                </div>
            </div>
            """

        html += """
        </section>
        """
        return html

    def _generate_scripts(self, group_results: List[Dict]) -> str:
        """Generate JavaScript for all visualizations."""
        # Prepare data for visualizations
        epsilons = [self._get_epsilon_display(r.get('epsilon', 'Unknown')) for r in group_results]
        epsilon_values = [self._epsilon_to_float(r.get('epsilon', '1')) for r in group_results]
        finite_eps = [value for value in epsilon_values if math.isfinite(value)]
        max_finite = max(finite_eps) if finite_eps else 1.0
        adjusted_inf = max_finite * 1.1
        epsilon_numeric = [
            value if math.isfinite(value) else adjusted_inf
            for value in epsilon_values
        ]

        # Extract metrics
        fidelity_scores = [self._safe_get(r, 'fidelity.quality.Overall.score', 0) * 100 for r in group_results]
        diagnostic_scores = [self._safe_get(r, 'fidelity.diagnostic.Overall.score', 0) * 100 for r in group_results]
        utility_summaries = [self._utility_summary(r) for r in group_results]
        utility_scores_percent = [
            float(summary.get('score')) if self._is_number(summary.get('score')) else None
            for summary in utility_summaries
        ]
        utility_label = next((summary.get('label') for summary in utility_summaries if summary.get('label')), 'Utility')
        utility_hover_text = [summary.get('display', 'N/A') for summary in utility_summaries]
        privacy_summaries = [self._summarize_privacy_metrics(r) for r in group_results]
        privacy_scores_percent = [
            float(summary.get('score')) if self._is_number(summary.get('score')) else None
            for summary in privacy_summaries
        ]
        privacy_annotations = [
            (summary.get('notes')[0] if summary.get('notes') else summary.get('level', 'Privacy summary'))
            for summary in privacy_summaries
        ]
        utility_axis_title = f"{utility_label} Score (%)" if utility_label != 'R²' else 'Utility (R² Score)'
        valid_utility_scores = [score for score in utility_scores_percent if self._is_number(score)]
        utility_max = max(valid_utility_scores) if valid_utility_scores else 0
        diversity_scores = [
            self._safe_get(r, 'diversity.tabular_diversity.entropy_metrics.dataset_entropy.entropy_ratio', 0) * 100
            for r in group_results
        ]
        hover_pairs = json.dumps([[utility_hover_text[i], privacy_annotations[i]] for i in range(len(group_results))])
        
        # JSON-encode data to avoid invalid JS (e.g., Infinity -> Infinity)
        epsilons_json = json.dumps(epsilons)
        epsilon_values_json = json.dumps(epsilon_numeric)
        fidelity_scores_json = json.dumps(fidelity_scores)
        diagnostic_scores_json = json.dumps(diagnostic_scores)
        utility_scores_json = json.dumps([score if score is not None else None for score in utility_scores_percent])
        utility_colors_json = json.dumps([score if score is not None else 0 for score in utility_scores_percent])
        privacy_scores_json = json.dumps([score if score is not None else None for score in privacy_scores_percent])
        diversity_scores_json = json.dumps(diversity_scores)
        utility_hover_json = json.dumps(utility_hover_text)
        privacy_colors_json = json.dumps(self._get_epsilon_colors(epsilon_values))
        
        return f"""
        document.addEventListener('DOMContentLoaded', function() {{
            // Remove loading spinners
            document.querySelectorAll('.chart-loading').forEach(el => {{
                el.innerHTML = '';
                el.classList.remove('chart-loading');
            }});
            
            // Privacy-Utility Tradeoff Scatter Plot
            var tradeoffData = [{{
                x: {utility_scores_json},
                y: {privacy_scores_json},
                mode: 'markers+lines',
                type: 'scatter',
                name: 'Privacy-Utility Tradeoff',
                text: {epsilons_json},
                customdata: {hover_pairs},
                hovertemplate: '<b>ε = %{{text}}</b><br>' +
                               '{utility_label}: %{{customdata[0]}}<br>' +
                               'Privacy: %{{y:.2f}}%<br>' +
                               '%{{customdata[1]}}<br>' +
                               '<extra></extra>',
                marker: {{
                    size: 15,
                    color: {epsilon_values_json},
                    colorscale: [
                        [0, '#2ecc71'],
                        [0.5, '#f39c12'],
                        [1, '#e74c3c']
                    ],
                    showscale: true,
                    colorbar: {{
                        title: 'Epsilon (ε)',
                        thickness: 15
                    }},
                    line: {{
                        color: 'white',
                        width: 2
                    }}
                }},
                line: {{
                    color: 'rgba(102, 126, 234, 0.3)',
                    width: 2,
                    dash: 'dash'
                }}
            }}];
            
            // Add optimal region
            var optimalRegion = {{
                x: [60, 100, 100, 60],
                y: [60, 60, 100, 100],
                mode: 'lines',
                fill: 'toself',
                fillcolor: 'rgba(40, 167, 69, 0.1)',
                line: {{
                    color: 'rgba(40, 167, 69, 0.3)',
                    width: 0
                }},
                showlegend: false,
                hoverinfo: 'skip'
            }};
            
            var tradeoffLayout = {{
                title: {{
                    text: 'Privacy-Utility Tradeoff Analysis',
                    font: {{size: 18}}
                }},
                xaxis: {{
                    title: '{utility_axis_title}',
                    range: [0, {utility_max + 5}],
                    showgrid: true,
                    gridcolor: '#e9ecef',
                    zeroline: true,
                    zerolinecolor: '#6c757d'
                }},
                yaxis: {{
                    title: 'Privacy Score (%)',
                    range: [0, 105],
                    showgrid: true,
                    gridcolor: '#e9ecef'
                }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}},
                hovermode: 'closest',
                annotations: [{{
                    x: 0.5,
                    y: 80,
                    text: 'Optimal Region',
                    showarrow: false,
                    font: {{
                        color: 'rgba(40, 167, 69, 0.7)',
                        size: 14
                    }}
                }}]
            }};
            
            Plotly.newPlot('privacy-utility-scatter', [optimalRegion, ...tradeoffData], tradeoffLayout, {{responsive: true}});
            
            // Fidelity Trend Chart
            var fidelityData = [
                {{
                    x: {epsilons_json},
                    y: {fidelity_scores_json},
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Quality Score',
                    line: {{
                        color: '#667eea',
                        width: 3
                    }},
                    marker: {{
                        size: 10,
                        color: '#667eea',
                        line: {{
                            color: 'white',
                            width: 2
                        }}
                    }}
                }},
                {{
                    x: {epsilons_json},
                    y: {diagnostic_scores_json},
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Diagnostic Score',
                    line: {{
                        color: '#764ba2',
                        width: 3,
                        dash: 'dash'
                    }},
                    marker: {{
                        size: 10,
                        color: '#764ba2',
                        line: {{
                            color: 'white',
                            width: 2
                        }}
                    }}
                }}
            ];
            
            var trendLayout = {{
                xaxis: {{
                    title: 'Epsilon (ε)',
                    type: 'category'
                }},
                yaxis: {{
                    title: 'Score (%)',
                    range: [0, 105]
                }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}},
                showlegend: true,
                legend: {{
                    x: 0.02,
                    y: 0.98
                }},
                hovermode: 'x unified'
            }};
            
            Plotly.newPlot('fidelity-trend-chart', fidelityData, trendLayout, {{responsive: true}});
            
            // Privacy Trend Chart
            var privacyData = [{{
                x: {epsilons_json},
                y: {privacy_scores_json},
                type: 'scatter',
                mode: 'lines+markers',
                fill: 'tozeroy',
                fillcolor: 'rgba(40, 167, 69, 0.1)',
                line: {{
                    color: '#28a745',
                    width: 3
                }},
                marker: {{
                    size: 10,
                    color: {privacy_colors_json},
                    line: {{
                        color: 'white',
                        width: 2
                    }}
                }},
                hovertemplate: 'ε = %{{x}}<br>Privacy: %{{y:.2f}}%<extra></extra>'
            }}];
            
            var privacyLayout = {{
                xaxis: {{
                    title: 'Epsilon (ε)',
                    type: 'category'
                }},
                yaxis: {{
                    title: 'Privacy Score (%)',
                    range: [0, 105]
                }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}},
                showlegend: false,
                hovermode: 'x unified'
            }};
            
            Plotly.newPlot('privacy-trend-chart', privacyData, privacyLayout, {{responsive: true}});
            
            // Utility Trend Chart
            var utilityData = [
                {{
                    x: {epsilons_json},
                    y: {utility_scores_json},
                    type: 'bar',
                    marker: {{
                        color: {utility_colors_json},
                        colorscale: [
                            [0, '#dc3545'],
                            [0.5, '#ffc107'],
                            [1, '#28a745']
                        ],
                        cmin: {utility_max if valid_utility_scores else 0},
                        cmax: {utility_max},
                        showscale: false,
                        line: {{
                            color: 'white',
                            width: 2
                        }}
                    }},
                    customdata: {utility_hover_json},
                    hovertemplate: 'ε = %{{x}}<br>{utility_label}: %{{customdata}}<extra></extra>'
                }}
            ];
            
            var utilityLayout = {{
                xaxis: {{
                    title: 'Epsilon (ε)',
                    type: 'category'
                }},
                yaxis: {{
                    title: '{utility_axis_title}',
                    zeroline: true,
                    zerolinecolor: '#dc3545',
                    zerolinewidth: 2
                }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}},
                showlegend: false
            }};
            
            Plotly.newPlot('utility-trend-chart', utilityData, utilityLayout, {{responsive: true}});
            
            // Diversity Trend Chart
            var diversityData = [
                {{
                    x: {epsilons_json},
                    y: {diversity_scores_json},
                    type: 'scatter',
                    mode: 'lines+markers',
                    fill: 'tonexty',
                    fillcolor: 'rgba(23, 162, 184, 0.1)',
                    line: {{
                        color: '#17a2b8',
                        width: 3,
                        shape: 'spline'
                    }},
                    marker: {{
                        size: 10,
                        color: '#17a2b8',
                        line: {{
                            color: 'white',
                            width: 2
                        }}
                    }},
                    hovertemplate: 'ε = %{{x}}<br>Diversity: %{{y:.2f}}%<extra></extra>'
                }}
            ];
            
            var diversityLayout = {{
                xaxis: {{
                    title: 'Epsilon (ε)',
                    type: 'category'
                }},
                yaxis: {{
                    title: 'Diversity Score (%)',
                    range: [0, Math.max(...{diversity_scores_json}) + 10]
                }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(0,0,0,0.02)',
                font: {{family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto'}},
                showlegend: false
            }};
            
            Plotly.newPlot('diversity-trend-chart', diversityData, diversityLayout, {{responsive: true}});
            
            // Add interactive hover effects
            document.querySelectorAll('.comparison-card').forEach(card => {{
                card.addEventListener('mouseenter', function() {{
                    this.style.transform = 'translateY(-10px)';
                }});
                card.addEventListener('mouseleave', function() {{
                    this.style.transform = 'translateY(0)';
                }});
            }});
            
            // Animate numbers on load
            function animateValue(element, start, end, duration) {{
                const range = end - start;
                const minTimer = 50;
                let stepTime = Math.abs(Math.floor(duration / range));
                stepTime = Math.max(stepTime, minTimer);
                const startTime = new Date().getTime();
                const endTime = startTime + duration;
                let timer;
                
                function run() {{
                    const now = new Date().getTime();
                    const remaining = Math.max((endTime - now) / duration, 0);
                    const value = Math.round(end - (remaining * range));
                    element.textContent = value + '%';
                    
                    if (value == end) {{
                        clearInterval(timer);
                    }}
                }}
                
                timer = setInterval(run, stepTime);
                run();
            }}
            
            // Animate metric values
            document.querySelectorAll('.metric-cell').forEach(cell => {{
                const value = parseFloat(cell.textContent);
                if (!isNaN(value) && cell.textContent.includes('%')) {{
                    animateValue(cell, 0, value, 1000);
                }}
            }});
        }});
        """
    
    # Helper methods
    def _sort_by_epsilon(self, results: List[Dict]) -> List[Dict]:
        """Sort results by epsilon value."""
        def epsilon_sort_key(result):
            eps = result.get('epsilon', 'Inf')
            return self._epsilon_to_float(eps)
        return sorted(results, key=epsilon_sort_key)
    
    def _epsilon_to_float(self, epsilon: str) -> float:
        """Convert epsilon string to float for sorting."""
        if epsilon in ['Inf', 'inf', 'None', None]:
            return float('inf')
        try:
            return float(epsilon)
        except:
            return float('inf')
    
    def _get_epsilon_display(self, epsilon: str) -> str:
        """Get display string for epsilon."""
        if epsilon in ['Inf', 'inf']:
            return '∞'
        return str(epsilon)
    
    def _get_epsilon_colors(self, epsilon_values: List[float]) -> List[str]:
        """Get colors for epsilon values."""
        colors = []
        for eps in epsilon_values:
            if eps <= 1:
                colors.append('#2ecc71')
            elif eps <= 10:
                colors.append('#27ae60')
            elif eps <= 100:
                colors.append('#f39c12')
            elif eps <= 1000:
                colors.append('#e67e22')
            elif eps <= 10000:
                colors.append('#e74c3c')
            else:
                colors.append('#c0392b')
        return colors
    
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
        """Return True when value is numeric and not NaN."""
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return False
            return True
        return False

    def _extract_tstr_metrics(self, result: Dict) -> Dict[str, float]:
        """Extract numeric metrics from the utility results."""
        utility = (result or {}).get("utility") or {}
        tstr = utility.get("tstr_accuracy") or {}
        synthetic = tstr.get("synthetic_data_model") or {}
        metrics: Dict[str, float] = {}

        if isinstance(synthetic, dict):
            for key in ("r2", "rmse", "mae", "accuracy", "f1_macro", "precision_macro", "recall_macro"):
                value = synthetic.get(key)
                if self._is_number(value):
                    metrics[key] = float(value)

            classification_report = synthetic.get("classification_report")
            if isinstance(classification_report, dict):
                accuracy = classification_report.get("accuracy")
                if self._is_number(accuracy):
                    metrics.setdefault("accuracy", float(accuracy))
                macro_avg = classification_report.get("macro avg")
                if isinstance(macro_avg, dict):
                    for source, target in (
                        ("f1-score", "f1_macro"),
                        ("precision", "precision_macro"),
                        ("recall", "recall_macro"),
                    ):
                        value = macro_avg.get(source)
                        if self._is_number(value):
                            metrics.setdefault(target, float(value))

        return metrics

    def _summarize_privacy_metrics(self, result: Dict) -> Dict[str, Any]:
        """Return the shared structured privacy summary."""
        return compute_privacy_summary(result or {})

    def _utility_summary(self, result: Dict) -> Dict[str, Any]:
        """Summarize the utility metric for display and scoring."""
        metrics = self._extract_tstr_metrics(result)
        summary: Dict[str, Any] = {
            "label": "Utility",
            "raw": None,
            "normalized": None,
            "score": None,
            "display": "N/A",
            "metrics": metrics,
            "primary_key": None,
        }

        if "r2" in metrics:
            raw = float(metrics["r2"])
            clamped = max(-1.0, min(1.0, raw))
            normalized = max(0.0, clamped)
            summary.update({
                "label": "R²",
                "raw": raw,
                "normalized": normalized,
                "score": (clamped + 1.0) * 50.0,
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

    def _find_optimal_epsilon(self, results: List[Dict]) -> str:
        """Find the optimal epsilon value based on balanced metrics."""
        best_score = -1
        best_epsilon = "Unknown"
        
        for result in results:
            epsilon = result.get('epsilon', 'Unknown')
            
            # Calculate weighted score
            fidelity = self._safe_get(result, 'fidelity.quality.Overall.score', 0)
            utility_summary = self._utility_summary(result)
            utility_norm = utility_summary.get('normalized')
            utility = float(utility_norm) if self._is_number(utility_norm) else 0.0
            privacy_summary = self._summarize_privacy_metrics(result)
            privacy_score = privacy_summary.get('score')
            privacy = (privacy_score / 100.0) if isinstance(privacy_score, (int, float)) else 1.0
            diversity = self._safe_get(result, 'diversity.tabular_diversity.entropy_metrics.dataset_entropy.entropy_ratio', 0)
            
            # Weight privacy more heavily for lower epsilons
            epsilon_val = self._epsilon_to_float(epsilon)
            if epsilon_val <= 10:
                privacy_weight = 2.0
            elif epsilon_val <= 100:
                privacy_weight = 1.5
            else:
                privacy_weight = 1.0
            
            score = (fidelity + utility + privacy * privacy_weight + diversity) / (3 + privacy_weight)
            
            if score > best_score:
                best_score = score
                best_epsilon = self._get_epsilon_display(epsilon)
        
        return best_epsilon
    
    def _get_trend_icon(self, epsilon_val: float) -> str:
        """Get trend icon based on epsilon value."""
        if epsilon_val <= 10:
            return '<i class="fas fa-shield-alt text-success"></i>'
        elif epsilon_val <= 100:
            return '<i class="fas fa-balance-scale text-warning"></i>'
        else:
            return '<i class="fas fa-unlock text-danger"></i>'
    
    def _analyze_trend(self, results: List[Dict]) -> str:
        """Analyze overall trends in the results."""
        # Calculate correlations
        epsilons = [self._epsilon_to_float(r.get('epsilon', '1')) for r in results]
        privacy_summaries = [self._summarize_privacy_metrics(r) for r in results]
        privacy_scores = [summary.get('score')/100.0 if isinstance(summary.get('score'), (int, float)) else None for summary in privacy_summaries]
        utility_summaries = [self._utility_summary(r) for r in results]
        utility_label = next((summary.get('label') for summary in utility_summaries if summary.get('label')), 'Utility')
        utility_scores = [summary.get('score') for summary in utility_summaries if self._is_number(summary.get('score'))]
        
        # Find where privacy drops most
        max_privacy_drop = 0
        drop_epsilon = None
        for i in range(1, len(privacy_scores)):
            drop = privacy_scores[i-1] - privacy_scores[i]
            if drop > max_privacy_drop:
                max_privacy_drop = drop
                drop_epsilon = results[i].get('epsilon')
        
        # Build trend description
        trend_desc = f"""
        <strong>Key Observations:</strong>
        <ul>
            <li>Privacy protection decreases by approximately {max_privacy_drop*100:.1f}% 
                at ε = {drop_epsilon} compared to the previous setting.</li>
        """
        
        # Check if utility improves significantly
        utility_improvement = (max(utility_scores) - min(utility_scores)) if utility_scores else 0
        if utility_improvement > 1:
            trend_desc += f"""
            <li>Utility improves by {utility_improvement:.2f} percentage points ({utility_label}) across the epsilon range,
                showing a clear privacy-utility tradeoff.</li>
            """
        
        # Check diversity trend
        diversity_scores = [self._safe_get(r, 'diversity.tabular_diversity.entropy_metrics.dataset_entropy.entropy_ratio', 0) 
                          for r in results]
        diversity_range = max(diversity_scores) - min(diversity_scores)
        if diversity_range > 0.1:
            trend_desc += f"""
            <li>Data diversity varies by {diversity_range*100:.1f}% across epsilon values, 
                indicating impact on synthetic data characteristics.</li>
            """
        
        trend_desc += "</ul>"
        return trend_desc


if __name__ == "__main__":
    # Test the generator with sample data
    import sys
    
    print("In-Group Dashboard Generator - Test Mode")
    print("=" * 50)
    
    # Create sample data for multiple epsilon values
    sample_results = []
    for epsilon in ["1", "10", "100", "1000", "10000", "Inf"]:
        result = {
            "experiment_id": f"test_exp_{epsilon}",
            "epsilon": epsilon,
            "fidelity": {
                "diagnostic": {"Overall": {"score": 0.75 + float(epsilon == "Inf") * 0.1}},
                "quality": {"Overall": {"score": 0.65 + float(epsilon == "Inf") * 0.15}}
            },
            "utility": {
                "tstr_accuracy": {
                    "synthetic_data_model": {
                        "r2": -0.5 + min(float(epsilon) if epsilon != "Inf" else 100000, 1000) / 1000
                    }
                }
            },
            "privacy": {
                "exact_matches": {"exact_match_percentage": min(float(epsilon) if epsilon != "Inf" else 100000, 100) / 100}
            },
            "diversity": {
                "tabular_diversity": {
                    "entropy_metrics": {
                        "dataset_entropy": {"entropy_ratio": 0.5 + min(float(epsilon) if epsilon != "Inf" else 100000, 100) / 200}
                    }
                }
            },
            "mia": {"auc": 0.5 + min(float(epsilon) if epsilon != "Inf" else 100000, 10000) / 20000}
        }
        sample_results.append(result)
    
    # Generate dashboard
    generator = InGroupDashboardGenerator()
    html = generator.generate(
        group_results=sample_results,
        group_name="Test Experiment - Epsilon Comparison"
    )
    
    # Save to file
    output_file = "in_group_dashboard_test.html"
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Dashboard generated: {output_file}")
    print(f"   File size: {len(html) / 1024:.1f} KB")
    print(f"   Epsilon values: {', '.join([r['epsilon'] for r in sample_results])}")
