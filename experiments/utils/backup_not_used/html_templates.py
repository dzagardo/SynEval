#!/usr/bin/env python3
"""
HTML template renderers for SynEval dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence

from experiments.utils.chart_configs import (
    get_chart_defaults_js,
    create_enhanced_chart_config,
    COLOR_PALETTE
)

THEME_CSS = """
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
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .subtitle {
        color: var(--text-secondary);
        font-size: 1.25rem;
        margin-bottom: 0.5rem;
    }

    .grid {
        display: grid;
        gap: 2rem;
    }

    .metrics-grid {
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .metric-card {
        background: var(--bg-card);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 2rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(15, 23, 42, 0.35);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent) 0%, var(--purple) 50%, var(--pink) 100%);
    }

    .metric-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }

    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }

    .control-panel {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 2rem;
        justify-content: center;
    }

    .control-button, .control-btn {
        padding: 0.75rem 1.5rem;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
        font-size: 0.9rem;
    }

    .control-button:hover, .control-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
        color: var(--text-primary);
    }

    .control-button.active, .control-btn.active {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        border-color: transparent;
        color: #ffffff;
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

    .chart-wrapper {
        position: relative;
        height: 350px;
        width: 100%;
    }

    .chart-wrapper canvas {
        width: 100% !important;
        height: 100% !important;
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

    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1.5rem;
        font-size: 0.95rem;
    }

    th, td {
        padding: 0.85rem 1rem;
        text-align: left;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }

    th {
        color: var(--text-secondary);
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
    }

    @media (max-width: 1024px) {
        .metrics-grid {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }
    }

    @media (max-width: 768px) {
        .title { font-size: 2rem; }
        .subtitle { font-size: 1rem; }
        .chart-wrapper { height: 300px; }
        .metric-value { font-size: 1.8rem; }
    }
"""


def _wrap_html(title: str, body: str, scripts: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js" crossorigin="anonymous"></script>
    <script>
        // Fallback to alternative CDN if primary fails
        window.addEventListener('load', function() {{
            if (typeof Chart === 'undefined') {{
                console.warn('Primary Chart.js CDN failed, loading fallback...');
                var script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js';
                script.onload = function() {{
                    console.info('Chart.js loaded from fallback CDN');
                    window.dispatchEvent(new Event('chartjs-loaded'));
                }};
                script.onerror = function() {{
                    console.error('All Chart.js CDNs failed to load');
                }};
                document.head.appendChild(script);
            }}
        }});
    </script>
    <style>{THEME_CSS}</style>
</head>
<body>
    <div class="bg-animation">
        <div class="particle" style="width: 300px; height: 300px; top: 10%; left: 5%; animation-delay: 0s;"></div>
        <div class="particle" style="width: 200px; height: 200px; top: 50%; right: 10%; animation-delay: 5s;"></div>
        <div class="particle" style="width: 250px; height: 250px; bottom: 15%; left: 30%; animation-delay: 10s;"></div>
        <div class="particle" style="width: 180px; height: 180px; top: 30%; right: 25%; animation-delay: 15s;"></div>
    </div>
    <div class="container">
        {body}
    </div>
    <script>
    (function() {{
        const chartQueue = [];
        let chartsInitialized = false;

        window.__registerChartConfig = function(cb) {{
            chartQueue.push(cb);
        }};

        function initCharts() {{
            if (chartsInitialized) return;

            if (typeof Chart === 'undefined') {{
                console.error('Chart.js failed to load. Charts will not render.');
                console.error('Please check your internet connection or try refreshing the page.');
                return;
            }}

            {get_chart_defaults_js()}

            chartQueue.forEach((cb, index) => {{
                try {{
                    cb();
                }} catch (err) {{
                    console.error(`Error rendering chart ${{index}}:`, err);
                }}
            }});

            chartsInitialized = true;
        }}

        // Try on DOMContentLoaded first
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initCharts);
        }} else {{
            // DOM already loaded, try immediately
            initCharts();
        }}

        // Fallback: also try on window.load in case Chart.js loads late
        window.addEventListener('load', function() {{
            if (!chartsInitialized && typeof Chart !== 'undefined') {{
                console.info('Retrying chart initialization on window.load');
                initCharts();
            }}
        }});

        // Handle fallback CDN load
        window.addEventListener('chartjs-loaded', function() {{
            if (!chartsInitialized) {{
                console.info('Initializing charts after fallback CDN loaded');
                initCharts();
            }}
        }});
    }})();
    {scripts}
    </script>
</body>
</html>"""


def render_metric_cards(title: str, subtitle: str, metrics: Dict[str, float]) -> str:
    cards = []
    for label, value in metrics.items():
        formatted = f"{value:.2f}" if isinstance(value, (int, float)) else value
        cards.append(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{formatted}</div>
            </div>
            """
        )
    cards_html = "\n".join(cards)
    body = f"""
        <h1 class="title">{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <div class="grid metrics-grid">
            {cards_html}
        </div>
    """
    return _wrap_html(title, body)


def render_experiment_report(
    title: str,
    subtitle: str,
    summary_metrics: Dict[str, float],
    chart_blocks: List[str],
    script_blocks: List[str],
) -> str:
    import logging
    logger = logging.getLogger("html_templates")
    logger.info(f"render_experiment_report called with {len(chart_blocks)} chart_blocks, {len(script_blocks)} script_blocks")

    metric_cards = []
    for label, value in summary_metrics.items():
        if isinstance(value, (int, float)):
            formatted = f"{value:.2f}"
        else:
            formatted = str(value)
        metric_cards.append(
            f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{formatted}</div>
        </div>
        """
        )

    metrics_html = "".join(metric_cards)

    charts_html = "\n".join(chart_blocks)
    scripts = "\n".join(script_blocks)

    logger.info(f"charts_html length: {len(charts_html)}, first 200 chars: {charts_html[:200] if charts_html else 'EMPTY'}")

    body = f"""
        <h1 class="title">{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <section>
            <div class="grid metrics-grid">
                {metrics_html}
            </div>
        </section>
        {charts_html}
    """
    return _wrap_html(title, body, scripts)


def render_dashboard_page(
    title: str,
    subtitle: str,
    summary_metrics: Dict[str, float],
    controls_html: str,
    sections: List[str],
    script_blocks: List[str],
) -> str:
    metric_cards = []
    for label, value in summary_metrics.items():
        if isinstance(value, (int, float)):
            formatted = f"{value:.2f}"
        else:
            formatted = str(value)
        metric_cards.append(
            f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{formatted}</div>
        </div>
        """
        )

    metrics_html = "".join(metric_cards)
    sections_html = "".join(sections)
    scripts = "\n".join(script_blocks)

    body = f"""
        <h1 class="title">{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <section>
            <div class="grid metrics-grid">
                {metrics_html}
            </div>
        </section>
        {controls_html}
        {sections_html}
    """

    return _wrap_html(title, body, scripts)


def chart_block(canvas_id: str, heading: str, description: str = "") -> str:
    desc_html = f'<p style="color: var(--text-secondary); margin-bottom: 1.5rem;">{description}</p>' if description else ""
    return f"""
    <section style="margin-top: 3rem;">
        <h2 class="section-title">{heading}</h2>
        {desc_html}
        <div class="chart-card">
            <div class="chart-wrapper">
                <canvas id="{canvas_id}" aria-label="{heading}" role="img"></canvas>
                <div id="{canvas_id}-error" style="display:none; padding:1rem; background:rgba(239,68,68,0.1); border:1px solid #ef4444; border-radius:8px; color:#fca5a5;">
                    <strong>Chart failed to load.</strong><br>
                    <span style="font-size:0.9rem;">Check browser console for details (F12 → Console).</span>
                </div>
            </div>
        </div>
    </section>
    """


def enhance_chart_config(config: Dict) -> Dict:
    """
    Enhance a basic chart configuration with proper styling.

    Args:
        config: Basic chart configuration

    Returns:
        Enhanced configuration with proper styling
    """
    # If config is already enhanced (has detailed options), return as-is
    if config.get('options', {}).get('plugins', {}).get('tooltip', {}).get('backgroundColor'):
        return config

    # Extract basic info
    chart_type = config.get('type', 'line')
    data = config.get('data', {})

    # For doughnut/pie charts, apply minimal enhancement to preserve existing styling
    if chart_type in ['doughnut', 'pie', 'polarArea']:
        from experiments.utils.chart_configs import get_standard_tooltip_config, deep_merge

        # Only enhance tooltips and legend
        enhanced_options = {
            'plugins': {
                'tooltip': get_standard_tooltip_config(),
                'legend': {
                    'position': 'bottom',
                    'labels': {
                        'padding': 15,
                        'font': {'size': 11, 'family': 'Inter'},
                        'color': '#9ca3af',
                        'usePointStyle': True,
                        'boxWidth': 8,
                        'boxHeight': 8
                    }
                }
            }
        }

        # Preserve all existing options
        if 'options' in config:
            deep_merge(enhanced_options, config['options'])

        return {
            'type': chart_type,
            'data': data,
            'options': enhanced_options
        }

    # For regular charts (line, bar, scatter, etc.)
    # Determine axis titles from existing config
    x_title = None
    y_title = None
    if 'options' in config and 'scales' in config['options']:
        if 'x' in config['options']['scales'] and 'title' in config['options']['scales']['x']:
            x_title = config['options']['scales']['x']['title'].get('text')
        if 'y' in config['options']['scales'] and 'title' in config['options']['scales']['y']:
            y_title = config['options']['scales']['y']['title'].get('text')

    # Determine if y-axis should begin at zero
    y_begin_at_zero = True
    if 'options' in config and 'scales' in config['options']:
        if 'y' in config['options']['scales']:
            y_begin_at_zero = config['options']['scales']['y'].get('beginAtZero', True)

    # Create enhanced config
    enhanced = create_enhanced_chart_config(
        chart_type=chart_type,
        data=data,
        x_axis_title=x_title,
        y_axis_title=y_title,
        y_begin_at_zero=y_begin_at_zero
    )

    # Preserve any custom options
    if 'options' in config:
        from experiments.utils.chart_configs import deep_merge
        deep_merge(enhanced['options'], config['options'])

    return enhanced


def sanitize_chart_data(config: Dict) -> Dict:
    """Remove NaN, Infinity, and invalid values from chart config"""
    import copy
    import math

    def clean_value(val):
        """Recursively clean a value"""
        if isinstance(val, dict):
            return {k: clean_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [clean_value(v) for v in val]
        elif isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return 0  # Replace invalid with 0
            return val
        else:
            return val

    return clean_value(config)


def script_for_chart(canvas_id: str, config: Dict) -> str:
    # Enhance the configuration with proper styling
    enhanced_config = enhance_chart_config(config)
    # Sanitize data to remove NaN/Infinity values
    sanitized_config = sanitize_chart_data(enhanced_config)
    config_json = json.dumps(sanitized_config, indent=2)

    return f"""
        __registerChartConfig(function () {{
            const canvas = document.getElementById('{canvas_id}');
            const errorDiv = document.getElementById('{canvas_id}-error');

            if (!canvas) {{
                console.error('Canvas not found for chart id: {canvas_id}');
                if (errorDiv) errorDiv.style.display = 'block';
                return;
            }}
            if (typeof Chart === 'undefined') {{
                console.error('Chart.js not available when initializing {canvas_id}');
                if (errorDiv) {{
                    errorDiv.innerHTML = '<strong>Chart.js library failed to load.</strong><br><span style="font-size:0.9rem;">Check your internet connection and refresh the page.</span>';
                    errorDiv.style.display = 'block';
                }}
                return;
            }}
            const ctx = canvas.getContext('2d');
            try {{
                const chart = new Chart(ctx, {config_json});
                console.info('Rendered chart {canvas_id}', chart);
            }} catch (error) {{
                console.error('Failed to render chart {canvas_id}', error);
                if (errorDiv) {{
                    errorDiv.innerHTML = '<strong>Chart rendering error.</strong><br><span style="font-size:0.9rem;">' + error.message + '</span>';
                    errorDiv.style.display = 'block';
                }}
                canvas.style.display = 'none';
            }}
        }});
    """
