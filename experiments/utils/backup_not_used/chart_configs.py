"""
Master Chart.js Configuration Templates
========================================
Provides consistent, production-ready chart configurations matching the reference aesthetic.

This module centralizes all Chart.js styling to ensure visual consistency across all reports.
"""

from typing import Dict, List, Optional, Any
import json


# Standard color palette matching the gradient theme
COLOR_PALETTE = {
    'blue': {'solid': '#3b82f6', 'alpha': 'rgba(59, 130, 246, 0.1)'},
    'purple': {'solid': '#8b5cf6', 'alpha': 'rgba(139, 92, 246, 0.1)'},
    'pink': {'solid': '#ec4899', 'alpha': 'rgba(236, 72, 153, 0.1)'},
    'cyan': {'solid': '#06b6d4', 'alpha': 'rgba(6, 182, 212, 0.1)'},
    'emerald': {'solid': '#10b981', 'alpha': 'rgba(16, 185, 129, 0.1)'},
    'orange': {'solid': '#f97316', 'alpha': 'rgba(249, 115, 22, 0.1)'},
    'yellow': {'solid': '#f59e0b', 'alpha': 'rgba(245, 158, 11, 0.1)'},
    'red': {'solid': '#ef4444', 'alpha': 'rgba(239, 68, 68, 0.1)'},
    'green': {'solid': '#22c55e', 'alpha': 'rgba(34, 197, 94, 0.1)'},
    'indigo': {'solid': '#6366f1', 'alpha': 'rgba(99, 102, 241, 0.1)'},
}


def get_chart_defaults_js() -> str:
    """
    Get JavaScript code to set Chart.js global defaults.
    This should be included once at the top of the script section.

    Returns:
        JavaScript code string
    """
    return """
    // Set global Chart.js defaults for consistent styling
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.font.family = 'Inter, system-ui, -apple-system, sans-serif';
        Chart.defaults.font.size = 11;

        Chart.defaults.plugins.legend.position = 'bottom';
        Chart.defaults.plugins.legend.labels.padding = 15;
        Chart.defaults.plugins.legend.labels.font.size = 11;
        Chart.defaults.plugins.legend.labels.color = '#9ca3af';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.legend.labels.boxHeight = 8;

        Chart.defaults.scales.linear.grid.color = 'rgba(255, 255, 255, 0.05)';
        Chart.defaults.scales.linear.ticks.color = '#9ca3af';
        Chart.defaults.scales.category.grid.color = 'rgba(255, 255, 255, 0.05)';
        Chart.defaults.scales.category.ticks.color = '#9ca3af';
    }
    """


def get_standard_tooltip_config() -> Dict:
    """Get standard tooltip configuration."""
    return {
        'backgroundColor': 'rgba(17, 24, 39, 0.95)',
        'titleColor': '#f9fafb',
        'bodyColor': '#e5e7eb',
        'borderColor': 'rgba(255, 255, 255, 0.1)',
        'borderWidth': 1,
        'padding': 12,
        'cornerRadius': 8,
        'displayColors': True,
        'titleFont': {
            'size': 13,
            'family': 'Inter',
            'weight': '600'
        },
        'bodyFont': {
            'size': 12,
            'family': 'Inter'
        }
    }


def get_standard_x_axis_config(title: Optional[str] = None,
                                max_rotation: int = 45,
                                category: bool = True) -> Dict:
    """
    Get standard X-axis configuration.

    Args:
        title: Optional axis title
        max_rotation: Maximum label rotation in degrees (default 45)
        category: Whether this is a category axis (default True)

    Returns:
        X-axis configuration dict
    """
    config = {
        'type': 'category' if category else 'linear',
        'grid': {
            'display': True,
            'color': 'rgba(255, 255, 255, 0.05)'
        },
        'ticks': {
            'maxRotation': max_rotation,
            'minRotation': 0,
            'autoSkip': True,
            'autoSkipPadding': 10,
            'font': {
                'size': 11,
                'family': 'Inter'
            },
            'color': '#9ca3af'
        }
    }

    if title:
        config['title'] = {
            'display': True,
            'text': title,
            'font': {
                'size': 12,
                'family': 'Inter'
            },
            'color': '#9ca3af'
        }

    return config


def get_standard_y_axis_config(title: Optional[str] = None,
                                begin_at_zero: bool = True,
                                format_large_numbers: bool = True) -> Dict:
    """
    Get standard Y-axis configuration.

    Args:
        title: Optional axis title
        begin_at_zero: Whether to start axis at zero
        format_large_numbers: Whether to format large numbers (K, M)

    Returns:
        Y-axis configuration dict
    """
    config = {
        'beginAtZero': begin_at_zero,
        'grid': {
            'display': True,
            'color': 'rgba(255, 255, 255, 0.05)'
        },
        'ticks': {
            'font': {
                'size': 11,
                'family': 'Inter'
            },
            'color': '#9ca3af'
        }
    }

    if title:
        config['title'] = {
            'display': True,
            'text': title,
            'font': {
                'size': 12,
                'family': 'Inter'
            },
            'color': '#9ca3af'
        }

    # Note: callback functions need to be added as raw JS strings, not in the dict
    # This will be handled in the chart config generation

    return config


def enhance_dataset_styling(dataset: Dict,
                            color_name: str = 'blue',
                            chart_type: str = 'line',
                            is_synthetic: bool = False) -> Dict:
    """
    Enhance a dataset with proper styling.

    Args:
        dataset: Dataset dictionary to enhance
        color_name: Color from COLOR_PALETTE to use
        chart_type: Type of chart ('line', 'bar', 'radar', 'doughnut', 'pie')
        is_synthetic: Whether this is synthetic data (uses dashed line)

    Returns:
        Enhanced dataset dictionary
    """
    color = COLOR_PALETTE.get(color_name, COLOR_PALETTE['blue'])

    # Doughnut/pie charts - don't override backgroundColor or borderColor if already set
    if chart_type in ['doughnut', 'pie', 'polarArea']:
        # These charts typically have backgroundColor as an array
        # Only set borderColor if not present, and use a subtle dark color for separation
        if 'borderColor' not in dataset:
            dataset['borderColor'] = 'rgba(17, 24, 39, 0.8)'  # Dark border for separation
        if 'borderWidth' not in dataset:
            dataset['borderWidth'] = 2
        return dataset

    # Regular charts (line, bar, radar, etc.)
    # Always set colors if not already set
    if 'borderColor' not in dataset:
        dataset['borderColor'] = color['solid']
    if 'backgroundColor' not in dataset and chart_type != 'bar':
        dataset['backgroundColor'] = color['alpha']
    elif chart_type == 'bar' and 'backgroundColor' not in dataset:
        dataset['backgroundColor'] = color['solid']

    # Line chart specific styling
    if chart_type == 'line':
        dataset.setdefault('borderWidth', 2.5)
        dataset.setdefault('tension', 0.4)
        dataset.setdefault('pointRadius', 4)
        dataset.setdefault('pointHoverRadius', 6)
        dataset.setdefault('pointBackgroundColor', color['solid'])
        dataset.setdefault('pointBorderColor', '#ffffff')
        dataset.setdefault('pointBorderWidth', 2)
        dataset.setdefault('fill', False)

        # Dashed line for synthetic data
        if is_synthetic:
            dataset.setdefault('borderDash', [5, 5])

    # Bar chart specific styling
    elif chart_type == 'bar':
        dataset.setdefault('borderWidth', 0)
        dataset.setdefault('borderRadius', 4)

    # Radar chart specific styling
    elif chart_type == 'radar':
        dataset.setdefault('borderWidth', 2.5)
        dataset.setdefault('pointRadius', 4)
        dataset.setdefault('pointHoverRadius', 6)
        dataset.setdefault('pointBackgroundColor', color['solid'])
        dataset.setdefault('pointBorderColor', '#ffffff')
        dataset.setdefault('pointBorderWidth', 2)

    return dataset


def create_enhanced_chart_config(chart_type: str,
                                  data: Dict,
                                  x_axis_title: Optional[str] = None,
                                  y_axis_title: Optional[str] = None,
                                  x_max_rotation: int = 45,
                                  y_begin_at_zero: bool = True,
                                  additional_options: Optional[Dict] = None) -> Dict:
    """
    Create a complete chart configuration with enhanced styling.

    Args:
        chart_type: Type of chart ('line', 'bar', 'radar', 'scatter')
        data: Chart data with labels and datasets
        x_axis_title: Optional X-axis title
        y_axis_title: Optional Y-axis title
        x_max_rotation: Maximum label rotation for X-axis
        y_begin_at_zero: Whether Y-axis starts at zero
        additional_options: Additional options to merge

    Returns:
        Complete Chart.js configuration dictionary
    """
    # Enhance datasets with styling
    for i, dataset in enumerate(data.get('datasets', [])):
        color_names = list(COLOR_PALETTE.keys())
        color_name = color_names[i % len(color_names)]

        # Check if this is synthetic data
        is_synthetic = 'synthetic' in dataset.get('label', '').lower()

        enhance_dataset_styling(dataset, color_name, chart_type, is_synthetic)

    # Build configuration
    config = {
        'type': chart_type,
        'data': data,
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'interaction': {
                'mode': 'index' if chart_type in ['line', 'bar'] else 'point',
                'intersect': False
            },
            'plugins': {
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
                },
                'tooltip': get_standard_tooltip_config()
            }
        }
    }

    # Add scales only for chart types that support them (not doughnut/pie)
    if chart_type in ['line', 'bar', 'scatter', 'bubble', 'radar']:
        config['options']['scales'] = {
            'x': get_standard_x_axis_config(x_axis_title, x_max_rotation),
            'y': get_standard_y_axis_config(y_axis_title, y_begin_at_zero)
        }

    # Merge additional options
    if additional_options:
        deep_merge(config['options'], additional_options)

    return config


def deep_merge(base: Dict, update: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary to merge into
        update: Dictionary with updates

    Returns:
        Merged dictionary (modifies base in place)
    """
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def get_number_formatter_js() -> str:
    """
    Get JavaScript function for formatting large numbers in charts.
    This can be used in axis tick callbacks.

    Returns:
        JavaScript function string
    """
    return """
    function formatLargeNumber(value) {
        if (Math.abs(value) >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (Math.abs(value) >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toFixed(0);
    }
    """


# Preset configurations for common chart types

def get_distribution_chart_config(labels: List, real_data: List, synthetic_data: List,
                                   x_title: str = 'Quantile', y_title: str = 'Value') -> Dict:
    """
    Get configuration for distribution comparison chart (quantile plot).

    Args:
        labels: Quantile labels
        real_data: Real data values
        synthetic_data: Synthetic data values
        x_title: X-axis title
        y_title: Y-axis title

    Returns:
        Complete chart configuration
    """
    data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Real',
                'data': real_data,
                'borderColor': COLOR_PALETTE['blue']['solid'],
                'backgroundColor': 'transparent',
                'borderWidth': 2.5,
                'tension': 0.3,
                'pointRadius': 3,
                'pointHoverRadius': 5
            },
            {
                'label': 'Synthetic',
                'data': synthetic_data,
                'borderColor': COLOR_PALETTE['red']['solid'],
                'backgroundColor': 'transparent',
                'borderWidth': 2.5,
                'tension': 0.3,
                'pointRadius': 3,
                'pointHoverRadius': 5,
                'borderDash': [5, 5]
            }
        ]
    }

    return create_enhanced_chart_config(
        'line',
        data,
        x_axis_title=x_title,
        y_axis_title=y_title,
        x_max_rotation=30,  # Gentle angle for quantile labels
        additional_options={
            'scales': {
                'x': {
                    'ticks': {
                        'autoSkip': False  # Show all quantile labels
                    }
                }
            }
        }
    )


def get_coverage_chart_config(features: List, coverage_values: List) -> Dict:
    """
    Get configuration for coverage bar chart.

    Args:
        features: Feature names
        coverage_values: Coverage percentages

    Returns:
        Complete chart configuration
    """
    data = {
        'labels': features,
        'datasets': [
            {
                'label': 'Synthetic Coverage (%)',
                'data': coverage_values,
                'backgroundColor': COLOR_PALETTE['blue']['solid']
            }
        ]
    }

    return create_enhanced_chart_config(
        'bar',
        data,
        y_axis_title='Coverage (%)',
        additional_options={
            'scales': {
                'y': {
                    'max': 100
                }
            }
        }
    )


def get_correlation_heatmap_config(features: List, correlation_matrix: List[List[float]]) -> Dict:
    """
    Get configuration for correlation heatmap.
    Note: Requires Chart.js Matrix plugin.

    Args:
        features: Feature names
        correlation_matrix: 2D correlation matrix

    Returns:
        Complete chart configuration
    """
    # Flatten matrix into data points
    data_points = []
    for i, row in enumerate(correlation_matrix):
        for j, value in enumerate(row):
            data_points.append({
                'x': features[j],
                'y': features[i],
                'v': value
            })

    return {
        'type': 'matrix',
        'data': {
            'datasets': [{
                'label': 'Correlation',
                'data': data_points,
                'backgroundColor': lambda ctx: {
                    # Color based on value
                    'value': ctx.dataset.data[ctx.dataIndex].v
                },
                'borderWidth': 1,
                'borderColor': 'rgba(255, 255, 255, 0.1)',
                'width': lambda ctx: {
                    # Dynamic sizing
                    'return': '(ctx.chart.chartArea || {}).width / ' + str(len(features))
                },
                'height': lambda ctx: {
                    'return': '(ctx.chart.chartArea || {}).height / ' + str(len(features))
                }
            }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'display': False
                },
                'tooltip': get_standard_tooltip_config()
            }
        }
    }
