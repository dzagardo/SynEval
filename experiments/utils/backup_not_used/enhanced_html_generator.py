#!/usr/bin/env python3
"""
Enhanced HTML Generator for SynEval Reports
============================================
Creates stunning, interactive dashboards with advanced visualizations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class EnhancedHTMLGenerator:
    """
    Generates beautiful, interactive HTML reports from SynEval results.
    """
    
    @staticmethod
    def get_base_styles() -> str:
        """Get the enhanced base CSS styles."""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0a0f1b;
            --bg-secondary: #101827;
            --bg-card: rgba(17, 24, 39, 0.8);
            --border: rgba(255, 255, 255, 0.06);
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --accent: #3b82f6;
            --purple: #8b5cf6;
            --cyan: #06b6d4;
            --pink: #ec4899;
            --indigo: #6366f1;
            --emerald: #10b981;
        }
        
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #ffffff;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Animated background particles */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
            z-index: -1;
        }
        
        .particle {
            position: absolute;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 70%);
            border-radius: 50%;
            animation: float 20s infinite ease-in-out;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0) translateX(0) scale(1); opacity: 0.3; }
            25% { transform: translateY(-100px) translateX(50px) scale(1.1); opacity: 0.5; }
            50% { transform: translateY(50px) translateX(-30px) scale(0.9); opacity: 0.3; }
            75% { transform: translateY(-50px) translateX(-50px) scale(1.05); opacity: 0.4; }
        }
        
        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            text-align: center;
            margin-bottom: 4rem;
            position: relative;
        }
        
        .title {
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradient-shift 3s ease-in-out infinite;
            letter-spacing: -0.03em;
        }
        
        @keyframes gradient-shift {
            0%, 100% { background-position: 0% 50%; background-size: 200% 200%; }
            50% { background-position: 100% 50%; background-size: 200% 200%; }
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }
        
        .epsilon-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 50px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--accent);
            margin-top: 1rem;
        }
        
        .score-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .score-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .score-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(15, 23, 42, 0.35);
        }
        
        .score-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent) 0%, var(--purple) 50%, var(--pink) 100%);
        }
        
        .score-circle {
            width: 150px;
            height: 150px;
            margin: 0 auto 1.5rem;
            border-radius: 50%;
            background: conic-gradient(
                from 0deg,
                var(--color) 0deg,
                var(--color) calc(var(--score) * 3.6deg),
                rgba(255, 255, 255, 0.05) calc(var(--score) * 3.6deg)
            );
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .score-inner {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: var(--bg-secondary);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .score-value {
            font-size: 2rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }
        
        .score-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 1rem;
        }
        
        .chart-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
        }
        
        .chart-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent) 0%, var(--purple) 50%, var(--pink) 100%);
        }
        
        .chart-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }
        
        .chart-wrapper {
            position: relative;
            height: 400px;
            width: 100%;
        }
        
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 2rem;
        }
        
        .metrics-table th {
            text-align: left;
            padding: 1rem;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
            border-bottom: 2px solid var(--border);
            background: var(--bg-secondary);
        }
        
        .metrics-table td {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }
        
        .metrics-table tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .risk-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .risk-low {
            background: rgba(34, 197, 94, 0.2);
            color: var(--success);
        }
        
        .risk-medium {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
        }
        
        .risk-high {
            background: rgba(239, 68, 68, 0.2);
            color: var(--danger);
        }
        
        .section-title {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 3rem 0 2rem;
            text-align: center;
            background: linear-gradient(135deg, var(--accent) 0%, var(--purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        @media (max-width: 768px) {
            .title { font-size: 2rem; }
            .subtitle { font-size: 1rem; }
            .score-cards { grid-template-columns: 1fr; }
            .chart-wrapper { height: 300px; }
        }
        """
    
    @staticmethod
    def generate_privacy_report(results_path: Path, output_path: Path, epsilon: Optional[float] = None) -> None:
        """Generate an enhanced privacy report."""
        with open(results_path, 'r') as f:
            data = json.load(f)
        
        privacy_data = data.get('privacy', {})
        
        # Extract key metrics
        exact_matches = privacy_data.get('exact_matches', {})
        mia = privacy_data.get('membership_inference', {})
        structured = privacy_data.get('structured_privacy_metrics', {})
        true_mia = privacy_data.get('true_mia', {})
        
        # Calculate overall privacy score (0-100)
        privacy_score = EnhancedHTMLGenerator._calculate_privacy_score(privacy_data)
        
        # Determine epsilon display
        epsilon_display = f"ε = {epsilon}" if epsilon else "Unknown ε"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Analysis Report</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
    <style>
    {EnhancedHTMLGenerator.get_base_styles()}
    </style>
</head>
<body>
    <div class="bg-animation">
        <div class="particle" style="width: 300px; height: 300px; top: 10%; left: 5%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 200px; height: 200px; top: 50%; right: 10%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 250px; height: 250px; bottom: 15%; left: 30%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 180px; height: 180px; top: 30%; right: 25%; animation-delay: 15s;"></div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1 class="title">Privacy Analysis</h1>
            <p class="subtitle">Differential Privacy Evaluation</p>
            <div class="epsilon-badge">{epsilon_display}</div>
        </div>
        
        <div class="score-cards">
            <div class="score-card">
                <div class="score-circle" style="--score: {privacy_score}; --color: var(--purple);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--purple);">{privacy_score:.1f}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">/ 100</div>
                    </div>
                </div>
                <div class="score-label">Privacy Score</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {(1 - exact_matches.get('exact_match_percentage', 0) / 100) * 100}; --color: var(--success);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--success);">{exact_matches.get('exact_match_percentage', 0):.2f}%</div>
                    </div>
                </div>
                <div class="score-label">Exact Matches</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {(1 - mia.get('distinguishability_auc', 0.5)) * 200}; --color: var(--cyan);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--cyan);">{mia.get('distinguishability_auc', 0):.3f}</div>
                    </div>
                </div>
                <div class="score-label">Distinguishability AUC</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {(1 - true_mia.get('auc', 0.5)) * 200}; --color: var(--pink);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--pink);">{true_mia.get('auc', 0):.3f}</div>
                    </div>
                </div>
                <div class="score-label">True MIA AUC</div>
            </div>
        </div>
        
        <h2 class="section-title">Privacy Metrics Overview</h2>
        
        <div class="chart-card">
            <h3 class="chart-title">Membership Inference Attack</h3>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Interpretation</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Distinguishability AUC</td>
                        <td>{mia.get('distinguishability_auc', 0):.4f}</td>
                        <td><span class="risk-badge {EnhancedHTMLGenerator._get_auc_risk_class(mia.get('distinguishability_auc', 0))}">{EnhancedHTMLGenerator._get_auc_risk_level(mia.get('distinguishability_auc', 0))}</span></td>
                    </tr>
                    <tr>
                        <td>Fidelity Score</td>
                        <td>{mia.get('fidelity_score', 0):.4f}</td>
                        <td>Higher is better</td>
                    </tr>
                    <tr>
                        <td>Synthetic Confidence</td>
                        <td>{mia.get('synthetic_confidence', 0):.4f}</td>
                        <td>Model confidence on synthetic data</td>
                    </tr>
                    <tr>
                        <td>Original Confidence</td>
                        <td>{mia.get('original_confidence', 0):.6e}</td>
                        <td>Model confidence on original data</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="chart-card">
            <h3 class="chart-title">Structured Privacy Metrics</h3>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Description</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {EnhancedHTMLGenerator._generate_structured_metrics_rows(structured)}
                </tbody>
            </table>
        </div>
        
        <div class="chart-card">
            <h3 class="chart-title">True MIA Analysis</h3>
            <div class="chart-wrapper">
                <canvas id="trueMiaChart"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <h3 class="chart-title">Exact Match Analysis</h3>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Exact Match Percentage</td>
                        <td>{exact_matches.get('exact_match_percentage', 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td>Risk Level</td>
                        <td><span class="risk-badge risk-{exact_matches.get('risk_level', 'unknown')}">{exact_matches.get('risk_level', 'unknown').upper()}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        // True MIA Chart
        const trueMiaData = {json.dumps(true_mia)};
        const ctx = document.getElementById('trueMiaChart').getContext('2d');
        
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: ['AUC', 'Accuracy', 'CI 95% Lower', 'CI 95% Upper'],
                datasets: [{{
                    label: 'True MIA Metrics',
                    data: [
                        trueMiaData.auc || 0,
                        trueMiaData.accuracy || 0,
                        trueMiaData.ci_95_lower || 0,
                        trueMiaData.ci_95_upper || 0
                    ],
                    backgroundColor: [
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(59, 130, 246, 0.7)',
                        'rgba(236, 72, 153, 0.7)',
                        'rgba(6, 182, 212, 0.7)'
                    ],
                    borderColor: [
                        'rgba(139, 92, 246, 1)',
                        'rgba(59, 130, 246, 1)',
                        'rgba(236, 72, 153, 1)',
                        'rgba(6, 182, 212, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#e5e7eb',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1,
                        grid: {{
                            color: 'rgba(255, 255, 255, 0.05)'
                        }},
                        ticks: {{
                            color: '#9ca3af'
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false
                        }},
                        ticks: {{
                            color: '#9ca3af'
                        }}
                    }}
                }}
            }}
        }});
    }});
    </script>
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    @staticmethod
    def _calculate_privacy_score(privacy_data: Dict) -> float:
        """Calculate an overall privacy score (0-100)."""
        score = 0.0
        
        # Exact matches (25 points)
        exact_match_pct = privacy_data.get('exact_matches', {}).get('exact_match_percentage', 0)
        score += (1 - exact_match_pct / 100) * 25
        
        # MIA AUC (40 points) - closer to 0.5 is better
        mia_auc = privacy_data.get('membership_inference', {}).get('distinguishability_auc', 0.5)
        score += (1 - abs(mia_auc - 0.5) * 2) * 40
        
        # True MIA AUC (35 points) - closer to 0.5 is better
        true_mia_auc = privacy_data.get('true_mia', {}).get('auc', 0.5)
        score += (1 - abs(true_mia_auc - 0.5) * 2) * 35
        
        return max(0, min(100, score))
    
    @staticmethod
    def _get_auc_risk_level(auc: float) -> str:
        """Get risk level based on AUC value."""
        if abs(auc - 0.5) < 0.1:
            return "Low"
        elif abs(auc - 0.5) < 0.3:
            return "Medium"
        else:
            return "High"
    
    @staticmethod
    def _get_auc_risk_class(auc: float) -> str:
        """Get CSS class based on AUC risk level."""
        level = EnhancedHTMLGenerator._get_auc_risk_level(auc)
        return f"risk-{level.lower()}"
    
    @staticmethod
    def _generate_structured_metrics_rows(structured: Dict) -> str:
        """Generate HTML rows for structured privacy metrics."""
        rows = []
        for metric_name, metric_data in structured.items():
            if isinstance(metric_data, dict):
                method = metric_data.get('method', metric_name)
                desc = metric_data.get('desc', '')
                passed = metric_data.get('passed', False)
                
                status_class = "risk-low" if passed else "risk-high"
                status_text = "PASSED" if passed else "FAILED"
                
                rows.append(f"""
                <tr>
                    <td>{method}</td>
                    <td>{desc}</td>
                    <td><span class="risk-badge {status_class}">{status_text}</span></td>
                </tr>
                """)
        
        return "\n".join(rows) if rows else "<tr><td colspan='3'>No structured metrics available</td></tr>"
    
    @staticmethod
    def generate_utility_report(results_path: Path, output_path: Path, epsilon: Optional[float] = None) -> None:
        """Generate an enhanced utility report."""
        with open(results_path, 'r') as f:
            data = json.load(f)
        
        # Extract utility metrics (if available)
        fidelity_data = data.get('fidelity', {})
        quality = fidelity_data.get('quality', {})
        diagnostic = fidelity_data.get('diagnostic', {})
        
        # Calculate overall utility score
        utility_score = quality.get('Overall', {}).get('score', 0) * 100
        diagnostic_score = diagnostic.get('Overall', {}).get('score', 0) * 100
        
        # Get column-level metrics
        column_shapes = quality.get('Column Shapes', 0) * 100
        column_pairs = quality.get('Column Pair Trends', 0) * 100
        
        # Determine epsilon display
        epsilon_display = f"ε = {epsilon}" if epsilon else "Unknown ε"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Utility Analysis Report</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
    <style>
    {EnhancedHTMLGenerator.get_base_styles()}
    </style>
</head>
<body>
    <div class="bg-animation">
        <div class="particle" style="width: 300px; height: 300px; top: 10%; left: 5%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 200px; height: 200px; top: 50%; right: 10%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 250px; height: 250px; bottom: 15%; left: 30%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 180px; height: 180px; top: 30%; right: 25%; animation-delay: 15s;"></div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1 class="title">Utility Analysis</h1>
            <p class="subtitle">Data Quality & Fidelity Evaluation</p>
            <div class="epsilon-badge">{epsilon_display}</div>
        </div>
        
        <div class="score-cards">
            <div class="score-card">
                <div class="score-circle" style="--score: {utility_score}; --color: var(--accent);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--accent);">{utility_score:.1f}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">/ 100</div>
                    </div>
                </div>
                <div class="score-label">Quality Score</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {diagnostic_score}; --color: var(--emerald);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--emerald);">{diagnostic_score:.1f}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">/ 100</div>
                    </div>
                </div>
                <div class="score-label">Diagnostic Score</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {column_shapes}; --color: var(--purple);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--purple);">{column_shapes:.1f}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">/ 100</div>
                    </div>
                </div>
                <div class="score-label">Column Shapes</div>
            </div>
            
            <div class="score-card">
                <div class="score-circle" style="--score: {column_pairs}; --color: var(--pink);">
                    <div class="score-inner">
                        <div class="score-value" style="color: var(--pink);">{column_pairs:.1f}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">/ 100</div>
                    </div>
                </div>
                <div class="score-label">Column Pair Trends</div>
            </div>
        </div>
        
        <h2 class="section-title">Fidelity Metrics</h2>
        
        <div class="chart-card">
            <h3 class="chart-title">Quality Metrics Breakdown</h3>
            <div class="chart-wrapper">
                <canvas id="qualityChart"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <h3 class="chart-title">Diagnostic Metrics</h3>
            <div class="chart-wrapper">
                <canvas id="diagnosticChart"></canvas>
            </div>
        </div>
        
        {EnhancedHTMLGenerator._generate_numerical_stats_section(fidelity_data.get('numerical_statistics', {}))}
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        // Quality Metrics Chart
        const qualityCtx = document.getElementById('qualityChart').getContext('2d');
        new Chart(qualityCtx, {{
            type: 'bar',
            data: {{
                labels: ['Column Shapes', 'Column Pair Trends', 'Overall'],
                datasets: [{{
                    label: 'Quality Score (%)',
                    data: [{column_shapes:.2f}, {column_pairs:.2f}, {utility_score:.2f}],
                    backgroundColor: [
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(236, 72, 153, 0.7)',
                        'rgba(59, 130, 246, 0.7)'
                    ],
                    borderColor: [
                        'rgba(139, 92, 246, 1)',
                        'rgba(236, 72, 153, 1)',
                        'rgba(59, 130, 246, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#e5e7eb',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                        ticks: {{ 
                            color: '#9ca3af',
                            callback: function(value) {{ return value + '%'; }}
                        }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#9ca3af' }}
                    }}
                }}
            }}
        }});
        
        // Diagnostic Metrics Chart
        const diagnosticCtx = document.getElementById('diagnosticChart').getContext('2d');
        const diagnosticData = {json.dumps(diagnostic)};
        new Chart(diagnosticCtx, {{
            type: 'radar',
            data: {{
                labels: Object.keys(diagnosticData).filter(k => k !== 'Overall'),
                datasets: [{{
                    label: 'Diagnostic Scores',
                    data: Object.keys(diagnosticData)
                        .filter(k => k !== 'Overall')
                        .map(k => (diagnosticData[k] || 0) * 100),
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ 
                        position: 'bottom',
                        labels: {{
                            color: '#9ca3af',
                            font: {{ size: 12 }}
                        }}
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#e5e7eb',
                        padding: 12
                    }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                        angleLines: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                        pointLabels: {{ 
                            color: '#9ca3af',
                            font: {{ size: 11 }}
                        }},
                        ticks: {{
                            color: '#9ca3af',
                            callback: function(value) {{ return value + '%'; }}
                        }}
                    }}
                }}
            }}
        }});
    }});
    </script>
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    @staticmethod
    def _generate_numerical_stats_section(numerical_stats: Dict) -> str:
        """Generate the numerical statistics section."""
        if not numerical_stats:
            return ""
        
        rows = []
        for column_name, stats in numerical_stats.items():
            if column_name in ['categorical_metrics', 'entropy_metrics']:
                continue
            
            if isinstance(stats, dict) and 'overall_fidelity_score' in stats:
                fidelity_score = stats['overall_fidelity_score'] * 100
                interpretation = stats.get('fidelity_interpretation', '')
                
                rows.append(f"""
                <tr>
                    <td>{column_name}</td>
                    <td>{fidelity_score:.2f}%</td>
                    <td>{interpretation}</td>
                </tr>
                """)
        
        if not rows:
            return ""
        
        return f"""
        <div class="chart-card">
            <h3 class="chart-title">Numerical Statistics Fidelity</h3>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Column</th>
                        <th>Fidelity Score</th>
                        <th>Interpretation</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """


def parse_epsilon_from_path(path: Path) -> Optional[float]:
    """Extract epsilon value from file path."""
    path_str = str(path)
    match = re.search(r'dp_eps(\d+)', path_str)
    if match:
        return float(match.group(1))
    return None
