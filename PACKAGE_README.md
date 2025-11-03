# SynEval HTML Generation Package

## Package Contents

This package contains all files needed to fix the HTML chart generation issues.

### 📄 Contents

```
syneval_html_generation_package.tar.gz
├── experiments/
│   ├── results/
│   │   └── [12 results.json files from different experiments]
│   ├── dashboards/
│   │   ├── comprehensive_overview.html (sample dashboard)
│   │   ├── comprehensive_privacy_dashboard.html
│   │   ├── comprehensive_utility_dashboard.html
│   │   └── methodology_notes.html
│   ├── experiments_summary.json (feeds comprehensive dashboards)
│   └── utils/
│       ├── html_templates.py (HTML generation functions)
│       ├── chart_configs.py (Chart.js configuration)
│       └── dashboard_data.py (dashboard data processing)
├── orchestrate_syneval_experiment.py (main orchestrator with HTML generation)
└── experiments/results/.../step_0010000/*.html (sample individual reports)
```

---

## 🔧 How HTML Generation Works

### **Architecture**

```
results.json (SynEval output)
     ↓
orchestrate_syneval_experiment.py
     ├─→ _build_privacy_report()
     ├─→ _build_utility_report()
     └─→ _build_comprehensive_dashboards()
           ↓
     html_templates.py
           ├─→ render_experiment_report()
           ├─→ chart_block()
           ├─→ script_for_chart()
           │        ↓
           │   enhance_chart_config()
           │        ↓
           └─→ chart_configs.py
                    ├─→ create_enhanced_chart_config()
                    ├─→ enhance_dataset_styling()
                    └─→ get_chart_defaults_js()
```

### **Flow**

1. **SynEval runs** → generates `results.json` with metrics
2. **Orchestrator reads results.json** → extracts metrics
3. **Orchestrator builds HTML** using `html_templates.py`:
   - Creates chart configurations (type, data, options)
   - Passes configs to `script_for_chart()`
4. **script_for_chart()** enhances configs:
   - Calls `enhance_chart_config()`
   - Applies styling from `chart_configs.py`
5. **HTML is generated** with Chart.js code
6. **Browser renders** the charts using Chart.js library

---

## 📊 Chart Types Generated

### **Individual Reports (privacy_report.html, utility_report.html)**

1. **Doughnut Chart** - "Distinguishability Gauge"
   - Shows similarity vs separability
   - Type: `doughnut`
   - Generated in: `orchestrate_syneval_experiment.py` lines 860-875

2. **Bar Charts** - Coverage, histograms, structured metrics
   - Type: `bar`
   - Various locations in orchestrator

3. **Line Charts** - Time series, trends
   - Type: `line`

### **Comprehensive Dashboards (comprehensive_overview.html, etc.)**

1. **Radar Chart** - Cross-experiment comparison
2. **Scatter Plot** - Privacy-utility trade-off
3. **Line Chart** - RMSE progression by epsilon

---

## 🐛 Current Issues

### **Issue 1: Doughnut Charts Look Terrible**

**Location**: Individual privacy reports (`privacy_report.html`)

**Problem**:
- Chart appears "skewed" or has visual artifacts
- Borders look wrong
- Not aesthetically pleasing

**Root Cause** (suspected):
- Incorrect `borderColor` or `borderWidth` on doughnut segments
- Enhancement function adding inappropriate styling for circular charts
- Possible axes being added to doughnut charts (which don't support axes)

**Files to Check**:
- `orchestrate_syneval_experiment.py` lines 860-875 (doughnut config creation)
- `html_templates.py` lines 462-492 (doughnut enhancement logic)
- `chart_configs.py` lines 194-201 (doughnut dataset styling)

### **Issue 2: Dashboard Charts May Be Empty**

**Location**: Comprehensive dashboards (`comprehensive_overview.html`)

**Problem**:
- User reports not seeing charts in dashboards

**Possible Causes**:
- Dataset array is empty or has too few experiments
- Charts created with empty data: `data: { labels: [], datasets: [] }`
- JavaScript errors preventing chart updates
- `refresh()` function not being called

**Files to Check**:
- `dashboard_data.py` - How experiments_summary.json is created
- Dashboard HTML - Check `const dataset = [...]` line
- Dashboard HTML - Check if `refresh()` is called after page load

---

## 🔍 Key Files Explained

### **1. orchestrate_syneval_experiment.py**

**Main orchestration script** that:
- Reads `results.json` files
- Extracts metrics (fidelity, privacy, utility)
- Builds HTML reports by calling functions in `html_templates.py`

**Key Functions**:
- `_build_privacy_report()` - Lines 805-1004 - Creates privacy_report.html
- `_build_utility_report()` - Lines 1006-1171 - Creates utility_report.html
- `_build_comprehensive_dashboards()` - Lines 1173-1340 - Creates dashboard HTMLs
- Creates chart configs as Python dicts, passes to `script_for_chart()`

**Example** (lines 860-875):
```python
gauge_config = {
    "type": "doughnut",
    "data": {
        "labels": ["Similarity (1 - AUC)", "Separability (AUC)"],
        "datasets": [{
            "data": [max(0.0, 1 - dist_auc), dist_auc],
            "backgroundColor": ["#22c55e", "#ef4444"],
            "hoverOffset": 4,
        }],
    },
    "options": {
        "responsive": True,
        "cutout": "65%",
    },
}
```

### **2. html_templates.py**

**HTML generation utilities**:
- `THEME_CSS` (lines 11-271) - CSS styling for all reports
- `_wrap_html()` (lines 273-326) - Wraps content in HTML structure, loads Chart.js
- `chart_block()` (lines 432-443) - Creates HTML for chart canvas
- `script_for_chart()` (lines 527-549) - Generates JavaScript to render chart
- `enhance_chart_config()` (lines 444-524) - **CRITICAL** - Enhances chart configs

**Critical Logic** (lines 462-492):
```python
def enhance_chart_config(config: Dict) -> Dict:
    # Special handling for doughnut/pie charts
    if chart_type in ['doughnut', 'pie', 'polarArea']:
        # Only enhance tooltips and legend
        # DON'T add axes or mess with colors
        ...
    # For other charts, do full enhancement
    ...
```

### **3. chart_configs.py**

**Chart.js configuration templates**:
- `COLOR_PALETTE` (lines 17-28) - Standard colors for charts
- `get_chart_defaults_js()` (lines 31-56) - Global Chart.js defaults
- `enhance_dataset_styling()` (lines 175-240) - Applies colors/styling to datasets
- `create_enhanced_chart_config()` (lines 243-316) - Creates complete chart config

**Critical Logic** (lines 194-201):
```python
def enhance_dataset_styling(dataset, color_name, chart_type, ...):
    # Special handling for doughnut/pie
    if chart_type in ['doughnut', 'pie', 'polarArea']:
        # Minimal styling, preserve original colors
        if 'borderColor' not in dataset:
            dataset['borderColor'] = 'rgba(17, 24, 39, 0.8)'
        return dataset  # Early return!
```

### **4. dashboard_data.py**

**Dashboard data processing**:
- Aggregates data from multiple experiments
- Creates `experiments_summary.json`
- Feeds comprehensive dashboards

### **5. results.json**

**SynEval experiment output** with structure:
```json
{
  "fidelity": {
    "quality_score": 56.76,
    "diagnostic_score": 76.48,
    ...
  },
  "utility": {
    "real_rmse": 0.236,
    "synthetic_rmse": 422.72,
    ...
  },
  "privacy": {
    "distinguishability_auc": 1.0,
    "auc_derived_fidelity": 0.0,
    "true_mia": {
      "auc": 0.5033,
      ...
    }
  },
  "diversity": {...}
}
```

---

## 🎯 What Needs Fixing

### **Primary Issues**

1. **Doughnut charts rendering poorly**
   - Check if incorrect styling is being applied
   - Verify no axes are being added
   - Ensure colors aren't being overridden

2. **Dashboard charts potentially empty**
   - Verify experiments_summary.json has data
   - Check dataset array in dashboard HTML
   - Ensure refresh() is called

### **Suggested Approach**

1. **Extract package**: `tar -xzf syneval_html_generation_package.tar.gz`

2. **Examine sample HTML**:
   - Open `experiments/results/.../privacy_report.html`
   - Look at doughnut chart configuration in JavaScript
   - Check for problematic settings

3. **Fix enhancement logic**:
   - Modify `html_templates.py` and/or `chart_configs.py`
   - Ensure doughnut charts get minimal, appropriate styling
   - Test with different chart types

4. **Test comprehensive dashboards**:
   - Check `experiments/experiments_summary.json` has data
   - Verify dashboard HTML has populated dataset
   - Ensure charts render with data

---

## 🔄 Regenerating HTML

After fixing the code, regenerate HTML by running:

```bash
python orchestrate_syneval_experiment.py \
    --source-dir experiments/data \
    --working-dir experiments \
    --steps step_0010000 \
    --variants OUTPUT_GRID_ROW_DP_EXTREMA \
    --dp-levels dp_eps1 dp_eps10 dp_eps100
```

This will:
1. Run SynEval evaluation (or skip if results exist)
2. Read results.json files
3. Generate new HTML reports using the (hopefully fixed) code
4. Generate comprehensive dashboards

---

## 📚 Dependencies

- **Chart.js 4.4.1** - Loaded from CDN in HTML
- **Python 3.x** - For orchestrator and generation scripts
- **SynEval** - Generates the results.json files

---

## 📝 Notes for Next Agent

- The HTML generation is template-based, not a full rendering engine
- Chart configs are Python dicts converted to JSON
- The enhancement system is supposed to add consistent styling, but may be too aggressive
- Doughnut/pie charts need special handling (no axes, preserve original colors)
- Test with actual browser rendering to see visual issues
- Check browser console for JavaScript errors

---

**Package Created**: October 23, 2025, 18:00 UTC
**Package Size**: 85KB (compressed)
**Contents**: 12 results.json + 4 Python files + sample HTMLs + summary JSON
