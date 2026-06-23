#!/usr/bin/env python3
"""
Dashboard Agent — Config-driven Salesforce report dashboard generator.
Interactive version with client-side filtering and live Salesforce connection.
Command Alkon | Digital Engagement | 2026
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
BRAND_NAVY = "#002856"
BRAND_ORANGE = "#DF4E10"
REFERENCE_HTML = r"C:\Users\daarango\Documents\Command Alkon\src\su_implementation_and_adoption_report.html"
SF_ORG_ALIAS = "prod"  # Your Salesforce org alias


# ══════════════════════════════════════════════════════════════════════════════
# ARGUMENT PARSER
# ══════════════════════════════════════════════════════════════════════════════
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML dashboards from Salesforce data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From local JSON file (default)
  python dashboard_agent.py --config configs/published_articles.json

  # Live from Salesforce (pulls fresh data)
  python dashboard_agent.py --config configs/published_articles.json --live

  # Live with custom output name
  python dashboard_agent.py --config configs/published_articles.json --live --output weekly_report.html
        """
    )
    parser.add_argument("--config", required=True, help="Path to report config JSON file")
    parser.add_argument("--live", action="store_true", help="Pull fresh data from Salesforce (requires sf CLI authenticated)")
    parser.add_argument("--discover", action="store_true", help="Show auto-detected columns from Salesforce and exit (requires --live)")
    parser.add_argument("--template", default=None, help="Template: executive (default from config)")
    parser.add_argument("--output", default=None, help="Output HTML filename (auto-generated if not provided)")
    parser.add_argument("--save-data", action="store_true", help="When using --live, also save the parsed data to JSON file")
    return parser.parse_args()


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG LOADER
# ══════════════════════════════════════════════════════════════════════════════
def load_config(config_path):
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# SALESFORCE LIVE DATA PULL
# ══════════════════════════════════════════════════════════════════════════════
def pull_salesforce_report(report_id):
    """Pull report data from Salesforce using sf CLI."""
    print(f"Pulling report {report_id} from Salesforce...")
    
    endpoint = f"/services/data/v62.0/analytics/reports/{report_id}"
    cmd = [
        "sf", "api", "request", "rest", endpoint,
        "--target-org", SF_ORG_ALIAS
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,  # Required for Windows to find sf.cmd
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"ERROR: Salesforce CLI returned error:")
            print(result.stderr)
            sys.exit(1)
        
        return json.loads(result.stdout)
    
    except subprocess.TimeoutExpired:
        print("ERROR: Salesforce request timed out after 120 seconds.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse Salesforce response as JSON: {e}")
        print(f"Response was: {result.stdout[:500]}...")
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: 'sf' command not found. Make sure Salesforce CLI is installed and in your PATH.")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# COLUMN AUTO-DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def normalize_column_name(sf_column):
    """Convert a Salesforce API column name to clean snake_case.
    
    Examples:
      Knowledge__kav.Language          -> language
      Knowledge__ka.LastPublishedDate  -> last_published_date
      Knowledge__kav.Product__c        -> product
      Knowledge__kav.LastModifiedBy.Name -> last_modified_by_name
    """
    parts = sf_column.split(".")
    # Drop the object prefix (e.g. "Knowledge__kav"), keep the rest
    if len(parts) > 1:
        name = "_".join(parts[1:])
    else:
        name = parts[0]

    # Remove Salesforce custom field suffixes (__c, __r)
    name = re.sub(r'__[crC R]$', '', name)
    name = re.sub(r'__c$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'__r$', '', name, flags=re.IGNORECASE)

    # CamelCase → snake_case
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
    name = name.lower()

    # Collapse multiple underscores, strip edges
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')

    return name


def auto_detect_columns(raw_data):
    """Build a {index: field_name} mapping from Salesforce report metadata."""
    detail_columns = raw_data.get("reportMetadata", {}).get("detailColumns", [])
    mapping = {idx: normalize_column_name(col) for idx, col in enumerate(detail_columns)}
    return mapping, detail_columns


# ══════════════════════════════════════════════════════════════════════════════
# PARSE SALESFORCE REPORT RESPONSE
# ══════════════════════════════════════════════════════════════════════════════
def parse_report_response(raw_data):
    """Parse Salesforce Analytics API response using auto-detected columns."""
    mapping, detail_columns = auto_detect_columns(raw_data)
    date_keywords = {"date", "datetime", "time"}

    rows = raw_data.get("factMap", {}).get("T!T", {}).get("rows", [])

    records = []
    for row in rows:
        cells = row.get("dataCells", [])
        record = {}
        for idx, field_name in mapping.items():
            if idx < len(cells):
                cell = cells[idx]
                # Date fields: use ISO value; all others: use display label
                is_date = any(kw in field_name for kw in date_keywords)
                record[field_name] = cell.get("value", "") if is_date else cell.get("label", "")
        records.append(record)

    return records, mapping


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADER (from file or live)
# ══════════════════════════════════════════════════════════════════════════════
def load_data(config, live=False, save_data=False):
    if live:
        report_id = config.get("report_id")
        if not report_id:
            print("ERROR: Config file must include 'report_id' to use --live mode.")
            sys.exit(1)
        
        raw_data = pull_salesforce_report(report_id)
        data, mapping = parse_report_response(raw_data)
        print(f"Pulled {len(data)} records from Salesforce.")
        print(f"Auto-detected {len(mapping)} columns: {', '.join(mapping.values())}")
        
        # Optionally save to file
        if save_data:
            output_file = config.get("input_file", "articles_clean.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved data to {output_file}")
        
        return data
    else:
        input_file = config.get("input_file", "articles_clean.json")
        print(f"Loading data from {input_file}...")
        with open(input_file, encoding="utf-8") as f:
            return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACT UNIQUE VALUES FOR DROPDOWNS
# ══════════════════════════════════════════════════════════════════════════════
def get_unique_values(data, field):
    values = set()
    for row in data:
        val = row.get(field)
        if val:
            values.add(val)
    return sorted(values)


# ══════════════════════════════════════════════════════════════════════════════
# LOGO EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════
def extract_logo():
    logo_src = ""
    for enc in ("utf-16", "utf-8"):
        try:
            with open(REFERENCE_HTML, encoding=enc) as f:
                content = f.read()
            m = re.search(r'src="(data:image/png;base64,[^"]+)"', content)
            if m:
                logo_src = m.group(1)
                break
        except Exception:
            continue
    
    if logo_src:
        return f'<img src="{logo_src}" style="height:32px;"/>'
    return '<span style="color:#fff;font-family:\'Barlow Condensed\',sans-serif;font-weight:700;font-size:20px;">COMMAND ALKON</span>'


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: EXECUTIVE (INTERACTIVE)
# ══════════════════════════════════════════════════════════════════════════════
def build_executive_template(config, data):
    logo_tag = extract_logo()
    generated_date = datetime.now().strftime("%B %d, %Y")
    report_name = config.get("name", "Dashboard")
    
    # Get chart config
    primary_chart = config.get("charts", {}).get("primary", {})
    secondary_chart = config.get("charts", {}).get("secondary", {})
    primary_field = primary_chart.get("group_by", "product")
    secondary_field = secondary_chart.get("group_by", "language")
    date_field = config.get("date_field", "published_date")
    
    # Get unique values for dropdowns
    products = get_unique_values(data, primary_field)
    languages = get_unique_values(data, secondary_field)
    
    # Serialize data for JavaScript
    data_json = json.dumps(data, ensure_ascii=False)
    products_json = json.dumps(products)
    languages_json = json.dumps(languages)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{report_name} — Interactive Dashboard</title>
<link rel="icon" type="image/x-icon" href="https://www.commandalkon.com/favicon.ico">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#F4F6F9;font-family:'Barlow',sans-serif;color:#1A1A2E}}
.lbl-grey{{color:#64748B;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}}
.stat-num{{font-family:'Barlow Condensed',sans-serif;font-size:40px;font-weight:700;color:#002856;line-height:1}}
.stat-lbl{{color:#64748B;font-size:13px;font-weight:500;margin-top:6px;text-transform:uppercase;letter-spacing:0.8px}}
.filter-label{{color:#6B8BAE;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}}
.filter-input{{padding:10px 14px;border:1px solid rgba(168,191,218,0.4);border-radius:6px;background:rgba(255,255,255,0.1);color:#fff;font-family:'Barlow',sans-serif;font-size:14px;width:100%}}
.filter-input:focus{{outline:none;border-color:#DF4E10}}
.filter-input option{{color:#1A1A2E;background:#fff}}
.btn-reset{{background:#DF4E10;color:#fff;border:none;padding:10px 20px;border-radius:6px;font-family:'Barlow',sans-serif;font-size:14px;font-weight:600;cursor:pointer;transition:background 0.2s}}
.btn-reset:hover{{background:#c44210}}
</style>
</head>
<body>

<!-- NAV -->
<nav style="position:sticky;top:0;z-index:1000;background:#002856;box-shadow:0 2px 12px rgba(0,0,0,0.25);display:flex;align-items:center;justify-content:space-between;padding:0 32px;height:56px;">
  <div style="display:flex;align-items:center;gap:10px;">
    {logo_tag}
    <span style="color:#DF4E10;font-size:18px;margin:0 6px;">|</span>
    <span style="color:#A8BFDA;font-size:15px;font-weight:600;">{report_name}</span>
  </div>
  <div style="color:#A8BFDA;font-size:13px;font-weight:500;">Generated {generated_date}</div>
</nav>

<!-- HERO -->
<header style="background:linear-gradient(135deg,#002856 0%,#003d7a 60%,#004d99 100%);padding:32px 48px;position:relative;overflow:hidden;">
  <div style="position:absolute;right:-60px;top:-60px;width:380px;height:380px;border:2px solid rgba(223,78,16,0.15);border-radius:50%;"></div>
  <div style="position:absolute;right:20px;top:20px;width:240px;height:240px;border:2px solid rgba(223,78,16,0.1);border-radius:50%;"></div>

  <div style="max-width:1100px;margin:0 auto;position:relative;">
    <div style="display:inline-block;background:rgba(223,78,16,0.15);border:1px solid rgba(223,78,16,0.4);border-radius:4px;padding:4px 14px;margin-bottom:20px;">
      <span style="color:#DF4E10;font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;">Interactive Dashboard</span>
    </div>
    <h1 style="margin:0 0 8px;color:#FFFFFF;font-family:'Barlow Condensed',sans-serif;font-size:48px;font-weight:700;line-height:1.1;letter-spacing:-0.5px;">{report_name}</h1>
    <h2 style="margin:0 0 24px;color:#A8BFDA;font-size:22px;font-weight:600;letter-spacing:0.3px;">Dashboard — {generated_date}</h2>

    <div style="display:flex;gap:40px;flex-wrap:wrap;margin-bottom:28px;">
      <div>
        <div style="color:#6B8BAE;font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:4px;">Prepared By</div>
        <div style="color:#FFFFFF;font-size:15px;font-weight:500;">Diego Arango — Digital Engagement Project Manager</div>
      </div>
      <div>
        <div style="color:#6B8BAE;font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:4px;">Data Source</div>
        <div style="color:#FFFFFF;font-size:15px;font-weight:500;">Salesforce — {report_name}</div>
      </div>
    </div>

    <!-- KPI CARDS -->
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:720px;margin-bottom:28px;">
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #DF4E10;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Total Articles</div>
        <div class="stat-num" id="kpi-total">0</div>
        <div class="stat-lbl" id="kpi-total-sub">Loading...</div>
      </div>
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #002856;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Top Product</div>
        <div class="stat-num" id="kpi-product" style="font-size:26px;line-height:1.2;">—</div>
        <div class="stat-lbl" id="kpi-product-sub">—</div>
      </div>
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #DF4E10;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Languages</div>
        <div class="stat-num" id="kpi-languages">0</div>
        <div class="stat-lbl">Active languages</div>
      </div>
    </div>

    <!-- FILTER CONTROLS -->
    <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:20px 24px;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr auto;gap:16px;align-items:end;">
        <div>
          <div class="filter-label">From Date</div>
          <input type="date" id="filter-from" class="filter-input" onchange="applyFilters()">
        </div>
        <div>
          <div class="filter-label">To Date</div>
          <input type="date" id="filter-to" class="filter-input" onchange="applyFilters()">
        </div>
        <div>
          <div class="filter-label">Product</div>
          <select id="filter-product" class="filter-input" onchange="applyFilters()">
            <option value="">All Products</option>
          </select>
        </div>
        <div>
          <div class="filter-label">Language</div>
          <select id="filter-language" class="filter-input" onchange="applyFilters()">
            <option value="">All Languages</option>
          </select>
        </div>
        <div>
          <button class="btn-reset" onclick="resetFilters()">Reset</button>
        </div>
      </div>
      <div style="margin-top:12px;color:#A8BFDA;font-size:13px;" id="filter-summary">Showing all data</div>
    </div>
  </div>
</header>

<!-- MAIN CONTENT -->
<main style="max-width:1100px;margin:0 auto;padding:32px 48px 80px;">

  <!-- SECTION HEADER -->
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;">
    <div style="background:#002856;color:#FFFFFF;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:6px 14px;border-radius:4px;">Breakdown</div>
    <div style="flex:1;height:1px;background:linear-gradient(to right,#CBD5E0,transparent);"></div>
  </div>

  <!-- CHARTS ROW -->
  <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;">

    <!-- CHART: Primary (Bar) -->
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <div style="width:3px;height:20px;background:#DF4E10;border-radius:2px;flex-shrink:0;"></div>
        <div style="font-size:11px;font-weight:700;color:#002856;text-transform:uppercase;letter-spacing:1px;">{primary_chart.get("title", "Articles by Product")}</div>
      </div>
      <canvas id="chartPrimary"></canvas>
    </div>

    <!-- CHART: Secondary (Doughnut) -->
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <div style="width:3px;height:20px;background:#DF4E10;border-radius:2px;flex-shrink:0;"></div>
        <div style="font-size:11px;font-weight:700;color:#002856;text-transform:uppercase;letter-spacing:1px;">{secondary_chart.get("title", "Articles by Language")}</div>
      </div>
      <canvas id="chartSecondary"></canvas>
    </div>

  </div>
</main>

<script>
// ══════════════════════════════════════════════════════════════════════════════
// DATA
// ══════════════════════════════════════════════════════════════════════════════
const ALL_DATA = {data_json};
const ALL_PRODUCTS = {products_json};
const ALL_LANGUAGES = {languages_json};
const DATE_FIELD = "{date_field}";
const PRIMARY_FIELD = "{primary_field}";
const SECONDARY_FIELD = "{secondary_field}";

// ══════════════════════════════════════════════════════════════════════════════
// CHART INSTANCES
// ══════════════════════════════════════════════════════════════════════════════
let chartPrimary = null;
let chartSecondary = null;

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZE
// ══════════════════════════════════════════════════════════════════════════════
function init() {{
  // Populate dropdowns
  const productSelect = document.getElementById('filter-product');
  ALL_PRODUCTS.forEach(p => {{
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    productSelect.appendChild(opt);
  }});
  
  const languageSelect = document.getElementById('filter-language');
  ALL_LANGUAGES.forEach(l => {{
    const opt = document.createElement('option');
    opt.value = l;
    opt.textContent = l;
    languageSelect.appendChild(opt);
  }});
  
  // Initial render
  applyFilters();
}}

// ══════════════════════════════════════════════════════════════════════════════
// FILTER DATA
// ══════════════════════════════════════════════════════════════════════════════
function filterData() {{
  const fromDate = document.getElementById('filter-from').value;
  const toDate = document.getElementById('filter-to').value;
  const product = document.getElementById('filter-product').value;
  const language = document.getElementById('filter-language').value;
  
  let filtered = ALL_DATA;
  
  if (fromDate) {{
    const from = new Date(fromDate);
    filtered = filtered.filter(row => {{
      const d = new Date(row[DATE_FIELD]);
      return d >= from;
    }});
  }}
  
  if (toDate) {{
    const to = new Date(toDate);
    to.setHours(23, 59, 59);
    filtered = filtered.filter(row => {{
      const d = new Date(row[DATE_FIELD]);
      return d <= to;
    }});
  }}
  
  if (product) {{
    filtered = filtered.filter(row => row[PRIMARY_FIELD] === product);
  }}
  
  if (language) {{
    filtered = filtered.filter(row => row[SECONDARY_FIELD] === language);
  }}
  
  return filtered;
}}

// ══════════════════════════════════════════════════════════════════════════════
// CALCULATE STATS
// ══════════════════════════════════════════════════════════════════════════════
function calcStats(data) {{
  const stats = {{
    total: data.length,
    byPrimary: {{}},
    bySecondary: {{}}
  }};
  
  data.forEach(row => {{
    const p = row[PRIMARY_FIELD] || 'Unknown';
    const s = row[SECONDARY_FIELD] || 'Unknown';
    stats.byPrimary[p] = (stats.byPrimary[p] || 0) + 1;
    stats.bySecondary[s] = (stats.bySecondary[s] || 0) + 1;
  }});
  
  // Sort by count descending
  stats.byPrimary = Object.fromEntries(
    Object.entries(stats.byPrimary).sort((a, b) => b[1] - a[1])
  );
  stats.bySecondary = Object.fromEntries(
    Object.entries(stats.bySecondary).sort((a, b) => b[1] - a[1])
  );
  
  // Top values
  const primaryEntries = Object.entries(stats.byPrimary);
  stats.topPrimary = primaryEntries.length > 0 ? primaryEntries[0][0] : '—';
  stats.topPrimaryCount = primaryEntries.length > 0 ? primaryEntries[0][1] : 0;
  stats.uniqueSecondary = Object.keys(stats.bySecondary).length;
  
  return stats;
}}

// ══════════════════════════════════════════════════════════════════════════════
// UPDATE KPIs
// ══════════════════════════════════════════════════════════════════════════════
function updateKPIs(stats) {{
  document.getElementById('kpi-total').textContent = stats.total.toLocaleString();
  document.getElementById('kpi-total-sub').textContent = stats.total === ALL_DATA.length ? 'All data' : 'Filtered';
  document.getElementById('kpi-product').textContent = stats.topPrimary;
  document.getElementById('kpi-product-sub').textContent = stats.topPrimaryCount + ' articles';
  document.getElementById('kpi-languages').textContent = stats.uniqueSecondary;
}}

// ══════════════════════════════════════════════════════════════════════════════
// UPDATE CHARTS
// ══════════════════════════════════════════════════════════════════════════════
function updateCharts(stats) {{
  const primaryLabels = Object.keys(stats.byPrimary);
  const primaryData = Object.values(stats.byPrimary);
  const primaryColors = primaryLabels.map((_, i) => i === 0 ? '#DF4E10' : '#002856');
  
  const secondaryLabels = Object.keys(stats.bySecondary);
  const secondaryData = Object.values(stats.bySecondary);
  const secondaryColors = ['#002856','#DF4E10','#3B6FA0','#F57A40','#1A4A7A','#C0A882','#5B8C5A','#8B5A8C','#5A8C8B','#C08260'];
  
  // Destroy existing charts
  if (chartPrimary) chartPrimary.destroy();
  if (chartSecondary) chartSecondary.destroy();
  
  // Primary chart (horizontal bar)
  const ctxP = document.getElementById('chartPrimary').getContext('2d');
  chartPrimary = new Chart(ctxP, {{
    type: 'bar',
    data: {{
      labels: primaryLabels,
      datasets: [{{
        label: 'Count',
        data: primaryData,
        backgroundColor: primaryColors,
        borderRadius: 4,
        borderSkipped: false
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.parsed.x + ' articles' }} }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#F1F5F9' }},
          ticks: {{ color: '#64748B', font: {{ family: 'Barlow', size: 12 }} }}
        }},
        y: {{
          grid: {{ display: false }},
          ticks: {{ color: '#334155', font: {{ family: 'Barlow', size: 12, weight: '600' }} }}
        }}
      }}
    }}
  }});
  
  // Secondary chart (doughnut)
  const ctxS = document.getElementById('chartSecondary').getContext('2d');
  chartSecondary = new Chart(ctxS, {{
    type: 'doughnut',
    data: {{
      labels: secondaryLabels,
      datasets: [{{
        data: secondaryData,
        backgroundColor: secondaryColors.slice(0, secondaryLabels.length),
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{
          position: 'bottom',
          labels: {{ color: '#334155', font: {{ family: 'Barlow', size: 12 }}, padding: 16 }}
        }}
      }},
      cutout: '65%'
    }}
  }});
}}

// ══════════════════════════════════════════════════════════════════════════════
// UPDATE FILTER SUMMARY
// ══════════════════════════════════════════════════════════════════════════════
function updateFilterSummary(filteredCount) {{
  const fromDate = document.getElementById('filter-from').value;
  const toDate = document.getElementById('filter-to').value;
  const product = document.getElementById('filter-product').value;
  const language = document.getElementById('filter-language').value;
  
  const parts = [];
  if (fromDate) parts.push('From: ' + fromDate);
  if (toDate) parts.push('To: ' + toDate);
  if (product) parts.push('Product: ' + product);
  if (language) parts.push('Language: ' + language);
  
  let summary = parts.length > 0 ? parts.join(' | ') : 'No filters applied';
  summary += ' — Showing ' + filteredCount.toLocaleString() + ' of ' + ALL_DATA.length.toLocaleString() + ' articles';
  
  document.getElementById('filter-summary').textContent = summary;
}}

// ══════════════════════════════════════════════════════════════════════════════
// APPLY FILTERS (main function)
// ══════════════════════════════════════════════════════════════════════════════
function applyFilters() {{
  const filtered = filterData();
  const stats = calcStats(filtered);
  updateKPIs(stats);
  updateCharts(stats);
  updateFilterSummary(filtered.length);
}}

// ══════════════════════════════════════════════════════════════════════════════
// RESET FILTERS
// ══════════════════════════════════════════════════════════════════════════════
function resetFilters() {{
  document.getElementById('filter-from').value = '';
  document.getElementById('filter-to').value = '';
  document.getElementById('filter-product').value = '';
  document.getElementById('filter-language').value = '';
  applyFilters();
}}

// ══════════════════════════════════════════════════════════════════════════════
// RUN
// ══════════════════════════════════════════════════════════════════════════════
init();
</script>
</body>
</html>'''
    
    return html


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    args = parse_args()
    
    # Load config
    config = load_config(args.config)
    print(f"Loaded config: {config.get('name', 'Unknown')}")

    # Discover mode: show auto-detected columns and exit
    if args.discover:
        if not args.live:
            print("ERROR: --discover requires --live (needs to pull from Salesforce to read metadata).")
            sys.exit(1)
        report_id = config.get("report_id")
        raw_data = pull_salesforce_report(report_id)
        mapping, detail_columns = auto_detect_columns(raw_data)
        print(f"\nAuto-detected {len(mapping)} columns for report: {config.get('name')}\n")
        print(f"  {'Index':<6} {'Salesforce Column':<45} {'Auto Field Name'}")
        print(f"  {'-'*6} {'-'*45} {'-'*30}")
        for idx, sf_col in enumerate(detail_columns):
            print(f"  {idx:<6} {sf_col:<45} {mapping[idx]}")
        print(f"\nUse these field names in your config for 'date_field' and 'charts.group_by'.")
        return

    # Load data (from file or live from Salesforce)
    data = load_data(config, live=args.live, save_data=args.save_data)
    print(f"Total records: {len(data)}")
    
    # Determine template
    template = args.template or config.get("default_template", "executive")
    
    # Build HTML
    if template == "executive":
        html = build_executive_template(config, data)
    else:
        print(f"ERROR: Template '{template}' not implemented yet.")
        return
    
    # Determine output filename
    output = args.output or f"dashboard_{template}.html"
    
    # Write file
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Interactive dashboard generated: {output}")


if __name__ == "__main__":
    main()