#!/usr/bin/env python3
"""
Cross-Group Experiment Dashboard Generator
===========================================
Creates dashboards showing how privacy and utility metrics change across epsilon values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import re


class CrossGroupDashboard:
    """Generates cross-experiment comparison dashboards."""
    
    @staticmethod
    def collect_experiment_data(results_dir: Path) -> Dict[str, List[Tuple[float, Dict]]]:
        """
        Collect all experiment results organized by experiment type.
        
        Returns:
            Dict mapping experiment type to list of (epsilon, results_data) tuples
        """
        experiments = defaultdict(list)
        
        # Find all results.json files
        for results_file in results_dir.rglob('results.json'):
            try:
                # Extract experiment info from path
                parts = results_file.parts
                
                # Find experiment type (e.g., OUTPUT_GRID_ROW_DP_EXTREMA)
                experiment_type = None
                epsilon = None
                step = None
                
                for i, part in enumerate(parts):
                    if 'OUTPUT_GRID' in part:
                        experiment_type = part
                    if 'dp_eps' in part:
                        match = re.search(r'dp_eps(\d+)', part)
                        if match:
                            epsilon = float(match.group(1))
                    if 'step_' in part:
                        step = part
                
                if experiment_type and epsilon is not None:
                    with open(results_file, 'r') as f:
                        data = json.load(f)
                    
                    experiments[experiment_type].append((epsilon, step, data))
            
            except Exception as e:
                print(f"Error processing {results_file}: {e}")
                continue
        
        # Sort by epsilon
        for exp_type in experiments:
            experiments[exp_type].sort(key=lambda x: x[0])
        
        return dict(experiments)
    
    @staticmethod
    def generate_cross_experiment_dashboard(results_dir: Path, output_path: Path) -> None:
        """Generate the main cross-experiment dashboard."""
        experiments = CrossGroupDashboard.collect_experiment_data(results_dir)
        
        if not experiments:
            print("No experiments found!")
            return
        
        # Extract data for charts
        chart_data = CrossGroupDashboard._prepare_chart_data(experiments)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cross-Experiment Analysis - Epsilon Impact</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
    <style>
    {CrossGroupDashboard._get_styles()}
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
            <h1 class="title">Differential Privacy: Comprehensive Analysis</h1>
            <p class="subtitle">Privacy-Utility Tradeoff Across Epsilon Values</p>
            <div class="delta-badge">δ = 3.33e-4 (Fixed)</div>
        </div>
        
        <div class="controls">
            <button class="control-btn active" onclick="toggleView('all')">All Experiments</button>
            <button class="control-btn" onclick="toggleView('row')">Row-Level DP</button>
            <button class="control-btn" onclick="toggleView('window')">Window-Level DP</button>
        </div>
        
        <h2 class="section-title">Privacy Metrics vs Epsilon</h2>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">Privacy Score</h3>
                <div class="chart-wrapper">
                    <canvas id="privacyScoreChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">Distinguishability AUC</h3>
                <div class="chart-wrapper">
                    <canvas id="aucChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">True MIA AUC</h3>
                <div class="chart-wrapper">
                    <canvas id="trueMiaChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">Exact Match Percentage</h3>
                <div class="chart-wrapper">
                    <canvas id="exactMatchChart"></canvas>
                </div>
            </div>
        </div>
        
        <h2 class="section-title">Utility Metrics vs Epsilon</h2>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">Quality Score</h3>
                <div class="chart-wrapper">
                    <canvas id="qualityChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">Diagnostic Score</h3>
                <div class="chart-wrapper">
                    <canvas id="diagnosticChart"></canvas>
                </div>
            </div>
        </div>
        
        <h2 class="section-title">Privacy-Utility Tradeoff</h2>
        
        <div class="chart-card" style="grid-column: 1 / -1;">
            <h3 class="chart-title">Privacy Score vs Utility Score</h3>
            <div class="chart-wrapper" style="height: 500px;">
                <canvas id="tradeoffChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
    const chartData = {json.dumps(chart_data)};
    let allCharts = {{}};
    
    {CrossGroupDashboard._get_chart_js()}
    </script>
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"✨ Cross-experiment dashboard generated: {output_path}")
    
    @staticmethod
    def _prepare_chart_data(experiments: Dict[str, List[Tuple]]) -> Dict:
        """Prepare data for charts."""
        chart_data = {}
        
        for exp_type, results in experiments.items():
            if not results:
                continue
            
            epsilons = []
            privacy_scores = []
            auc_values = []
            true_mia_aucs = []
            exact_matches = []
            quality_scores = []
            diagnostic_scores = []
            
            for epsilon, step, data in results:
                epsilons.append(epsilon)
                
                # Privacy metrics
                privacy_data = data.get('privacy', {})
                
                # Calculate privacy score
                privacy_score = CrossGroupDashboard._calculate_privacy_score(privacy_data)
                privacy_scores.append(privacy_score)
                
                # AUC
                mia = privacy_data.get('membership_inference', {})
                auc_values.append(mia.get('distinguishability_auc', 0))
                
                # True MIA
                true_mia = privacy_data.get('true_mia', {})
                true_mia_aucs.append(true_mia.get('auc', 0))
                
                # Exact matches
                exact_match = privacy_data.get('exact_matches', {})
                exact_matches.append(exact_match.get('exact_match_percentage', 0))
                
                # Utility metrics
                fidelity = data.get('fidelity', {})
                quality = fidelity.get('quality', {})
                diagnostic = fidelity.get('diagnostic', {})
                
                quality_scores.append(quality.get('Overall', {}).get('score', 0) * 100)
                diagnostic_scores.append(diagnostic.get('Overall', {}).get('score', 0) * 100)
            
            chart_data[exp_type] = {
                'epsilons': epsilons,
                'privacy_scores': privacy_scores,
                'auc_values': auc_values,
                'true_mia_aucs': true_mia_aucs,
                'exact_matches': exact_matches,
                'quality_scores': quality_scores,
                'diagnostic_scores': diagnostic_scores
            }
        
        return chart_data
    
    @staticmethod
    def _calculate_privacy_score(privacy_data: Dict) -> float:
        """Calculate overall privacy score."""
        score = 0.0
        
        exact_match_pct = privacy_data.get('exact_matches', {}).get('exact_match_percentage', 0)
        score += (1 - exact_match_pct / 100) * 25
        
        mia_auc = privacy_data.get('membership_inference', {}).get('distinguishability_auc', 0.5)
        score += (1 - abs(mia_auc - 0.5) * 2) * 40
        
        true_mia_auc = privacy_data.get('true_mia', {}).get('auc', 0.5)
        score += (1 - abs(true_mia_auc - 0.5) * 2) * 35
        
        return max(0, min(100, score))
    
    @staticmethod
    def _get_styles() -> str:
        """Get CSS styles for the dashboard."""
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
        
        .delta-badge {
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
        
        .controls {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 3rem;
            flex-wrap: wrap;
        }
        
        .control-btn {
            padding: 0.75rem 1.5rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
            font-size: 0.9rem;
            font-family: 'Inter', sans-serif;
        }
        
        .control-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
            color: var(--text-primary);
        }
        
        .control-btn.active {
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            border-color: transparent;
            color: #ffffff;
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
        
        .charts-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .chart-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
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
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
        }
        
        .chart-wrapper {
            position: relative;
            height: 350px;
            width: 100%;
        }
        
        @media (max-width: 1024px) {
            .charts-container {
                grid-template-columns: 1fr;
            }
        }
        
        @media (max-width: 768px) {
            .title { font-size: 2rem; }
            .subtitle { font-size: 1rem; }
            .chart-wrapper { height: 300px; }
        }
        """
    
    @staticmethod
    def _get_chart_js() -> str:
        """Get JavaScript for chart rendering."""
        return """
        // Color palette
        const colors = {
            row: { color: '#3b82f6', alpha: 'rgba(59, 130, 246, 0.2)' },
            window: { color: '#8b5cf6', alpha: 'rgba(139, 92, 246, 0.2)' },
            long: { color: '#ec4899', alpha: 'rgba(236, 72, 153, 0.2)' }
        };
        
        function getExpColor(expType) {
            if (expType.includes('ROW')) return colors.row;
            if (expType.includes('WINDOW')) return colors.window;
            return colors.long;
        }
        
        function createLineChart(canvasId, dataKey, yLabel, yMin, yMax) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            const datasets = [];
            
            for (const [expType, data] of Object.entries(chartData)) {
                const expColor = getExpColor(expType);
                datasets.push({
                    label: expType.replace('OUTPUT_GRID_', '').replace('_', ' '),
                    data: data.epsilons.map((eps, i) => ({
                        x: eps,
                        y: data[dataKey][i]
                    })),
                    borderColor: expColor.color,
                    backgroundColor: expColor.alpha,
                    borderWidth: 2.5,
                    tension: 0.3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: expColor.color,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    fill: false
                });
            }
            
            return new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: { size: 11, family: 'Inter' },
                                color: '#9ca3af',
                                usePointStyle: true,
                                boxWidth: 8,
                                boxHeight: 8
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleColor: '#f9fafb',
                            bodyColor: '#e5e7eb',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                title: function(context) {
                                    return 'ε = ' + context[0].parsed.x;
                                },
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += context.parsed.y.toFixed(2);
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'logarithmic',
                            title: {
                                display: true,
                                text: 'Privacy Budget (ε)',
                                font: { size: 12, family: 'Inter' },
                                color: '#9ca3af'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af',
                                callback: function(value) {
                                    return value;
                                }
                            }
                        },
                        y: {
                            beginAtZero: yMin === 0,
                            min: yMin,
                            max: yMax,
                            title: {
                                display: true,
                                text: yLabel,
                                font: { size: 12, family: 'Inter' },
                                color: '#9ca3af'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af'
                            }
                        }
                    }
                }
            });
        }
        
        function toggleView(filter) {
            // Update button states
            document.querySelectorAll('.control-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update chart visibility
            Object.values(allCharts).forEach(chart => {
                chart.data.datasets.forEach((dataset, index) => {
                    let visible = true;
                    if (filter === 'row') {
                        visible = dataset.label.includes('ROW');
                    } else if (filter === 'window') {
                        visible = dataset.label.includes('WINDOW');
                    }
                    chart.setDatasetVisibility(index, visible);
                });
                chart.update();
            });
        }
        
        // Initialize charts
        document.addEventListener('DOMContentLoaded', function() {
            allCharts.privacy = createLineChart('privacyScoreChart', 'privacy_scores', 'Privacy Score', 0, 100);
            allCharts.auc = createLineChart('aucChart', 'auc_values', 'AUC', 0, 1);
            allCharts.trueMia = createLineChart('trueMiaChart', 'true_mia_aucs', 'True MIA AUC', 0, 1);
            allCharts.exactMatch = createLineChart('exactMatchChart', 'exact_matches', 'Exact Match %', 0, null);
            allCharts.quality = createLineChart('qualityChart', 'quality_scores', 'Quality Score', 0, 100);
            allCharts.diagnostic = createLineChart('diagnosticChart', 'diagnostic_scores', 'Diagnostic Score', 0, 100);
            
            // Tradeoff scatter plot
            const tradeoffCtx = document.getElementById('tradeoffChart').getContext('2d');
            const tradeoffDatasets = [];
            
            for (const [expType, data] of Object.entries(chartData)) {
                const expColor = getExpColor(expType);
                tradeoffDatasets.push({
                    label: expType.replace('OUTPUT_GRID_', '').replace('_', ' '),
                    data: data.epsilons.map((eps, i) => ({
                        x: data.privacy_scores[i],
                        y: data.quality_scores[i],
                        epsilon: eps
                    })),
                    backgroundColor: expColor.alpha,
                    borderColor: expColor.color,
                    borderWidth: 2,
                    pointRadius: 8,
                    pointHoverRadius: 10
                });
            }
            
            allCharts.tradeoff = new Chart(tradeoffCtx, {
                type: 'scatter',
                data: { datasets: tradeoffDatasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: { size: 11, family: 'Inter' },
                                color: '#9ca3af',
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleColor: '#f9fafb',
                            bodyColor: '#e5e7eb',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                                label: function(context) {
                                    return [
                                        context.dataset.label,
                                        'ε: ' + context.raw.epsilon,
                                        'Privacy: ' + context.parsed.x.toFixed(1),
                                        'Utility: ' + context.parsed.y.toFixed(1)
                                    ];
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Privacy Score',
                                font: { size: 12, family: 'Inter' },
                                color: '#9ca3af'
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#9ca3af' }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Utility Score',
                                font: { size: 12, family: 'Inter' },
                                color: '#9ca3af'
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#9ca3af' }
                        }
                    }
                }
            });
        });
        """


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python cross_group_dashboard.py <results_dir> <output_path>")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    CrossGroupDashboard.generate_cross_experiment_dashboard(results_dir, output_path)
