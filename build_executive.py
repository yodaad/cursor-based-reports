import json
import re
from datetime import datetime

# ── Load data ──────────────────────────────────────────────────
with open("articles_clean.json", encoding="utf-8") as f:
    articles = json.load(f)

total = len(articles)
products = {}
languages = {}
for a in articles:
    products[a["product"]] = products.get(a["product"], 0) + 1
    languages[a["language"]] = languages.get(a["language"], 0) + 1

top_product = max(products, key=products.get)
top_product_count = products[top_product]
lang_count = len(languages)

products_sorted = sorted(products.items(), key=lambda x: -x[1])
languages_sorted = sorted(languages.items(), key=lambda x: -x[1])

product_labels = json.dumps([p[0] for p in products_sorted])
product_data = json.dumps([p[1] for p in products_sorted])
product_colors = json.dumps(["#DF4E10"] + ["#002856"] * (len(products_sorted) - 1))
lang_labels = json.dumps([l[0] for l in languages_sorted])
lang_data = json.dumps([l[1] for l in languages_sorted])

generated_date = datetime.now().strftime("%B %d, %Y")

# ── Extract CA logo from reference HTML ────────────────────────
REFERENCE = r"C:\Users\daarango\Documents\Command Alkon\src\su_implementation_and_adoption_report.html"
logo_src = ""
for enc in ("utf-16", "utf-8"):
    try:
        with open(REFERENCE, encoding=enc) as f:
            content = f.read()
        m = re.search(r'src="(data:image/png;base64,[^"]+)"', content)
        if m:
            logo_src = m.group(1)
            break
    except Exception:
        continue

logo_tag = (
    f'<img src="{logo_src}" style="height:32px;"/>'
    if logo_src
    else "<span style=\"color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:20px;letter-spacing:1px;\">COMMAND ALKON</span>"
)

# ── Build HTML ─────────────────────────────────────────────────
html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Knowledge Base — Published Articles Dashboard</title>
<link rel="icon" type="image/x-icon" href="https://www.commandalkon.com/favicon.ico">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#F4F6F9;font-family:'Barlow',sans-serif;color:#1A1A2E}
.lbl-grey{color:#64748B;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
.stat-num{font-family:'Barlow Condensed',sans-serif;font-size:40px;font-weight:700;color:#002856;line-height:1}
.stat-lbl{color:#64748B;font-size:13px;font-weight:500;margin-top:6px;text-transform:uppercase;letter-spacing:0.8px}
</style>
</head>
<body>

<!-- NAV -->
<nav style="position:sticky;top:0;z-index:1000;background:#002856;box-shadow:0 2px 12px rgba(0,0,0,0.25);display:flex;align-items:center;justify-content:space-between;padding:0 32px;height:56px;">
  <div style="display:flex;align-items:center;gap:10px;">
    LOGO_TAG
    <span style="color:#DF4E10;font-size:18px;margin:0 6px;">|</span>
    <span style="color:#A8BFDA;font-size:15px;font-weight:600;">Knowledge Base Dashboard</span>
  </div>
  <div style="color:#A8BFDA;font-size:13px;font-weight:500;">Generated GENERATED_DATE</div>
</nav>

<!-- HERO -->
<header style="background:linear-gradient(135deg,#002856 0%,#003d7a 60%,#004d99 100%);padding:32px 48px;position:relative;overflow:hidden;">
  <div style="position:absolute;right:-60px;top:-60px;width:380px;height:380px;border:2px solid rgba(223,78,16,0.15);border-radius:50%;"></div>
  <div style="position:absolute;right:20px;top:20px;width:240px;height:240px;border:2px solid rgba(223,78,16,0.1);border-radius:50%;"></div>

  <div style="max-width:1100px;margin:0 auto;position:relative;">
    <div style="display:inline-block;background:rgba(223,78,16,0.15);border:1px solid rgba(223,78,16,0.4);border-radius:4px;padding:4px 14px;margin-bottom:20px;">
      <span style="color:#DF4E10;font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;">Executive Report</span>
    </div>
    <h1 style="margin:0 0 8px;color:#FFFFFF;font-family:'Barlow Condensed',sans-serif;font-size:48px;font-weight:700;line-height:1.1;letter-spacing:-0.5px;">Knowledge Base</h1>
    <h2 style="margin:0 0 24px;color:#A8BFDA;font-size:22px;font-weight:600;letter-spacing:0.3px;">Published Articles Report — GENERATED_DATE</h2>

    <div style="display:flex;gap:40px;flex-wrap:wrap;margin-bottom:28px;">
      <div>
        <div style="color:#6B8BAE;font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:4px;">Prepared By</div>
        <div style="color:#FFFFFF;font-size:15px;font-weight:500;">Diego Arango &mdash; Digital Engagement Project Manager</div>
      </div>
      <div>
        <div style="color:#6B8BAE;font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:4px;">Data Source</div>
        <div style="color:#FFFFFF;font-size:15px;font-weight:500;">Salesforce &mdash; Published Articles Weekly Report</div>
      </div>
    </div>

    <!-- KPI CARDS -->
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:720px;">
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #DF4E10;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Total Published Articles</div>
        <div class="stat-num">TOTAL</div>
        <div class="stat-lbl">All products &amp; languages</div>
      </div>
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #002856;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Top Product</div>
        <div class="stat-num" style="font-size:26px;line-height:1.2;">TOP_PRODUCT</div>
        <div class="stat-lbl">TOP_PRODUCT_COUNT articles</div>
      </div>
      <div style="background:#FFFFFF;border-radius:10px;padding:20px 24px;border-top:3px solid #DF4E10;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div class="lbl-grey">Languages</div>
        <div class="stat-num">LANG_COUNT</div>
        <div class="stat-lbl">Active languages</div>
      </div>
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

    <!-- CHART: Articles by Product -->
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <div style="width:3px;height:20px;background:#DF4E10;border-radius:2px;flex-shrink:0;"></div>
        <div style="font-size:11px;font-weight:700;color:#002856;text-transform:uppercase;letter-spacing:1px;">Articles by Product</div>
      </div>
      <canvas id="chartProducts"></canvas>
    </div>

    <!-- CHART: Articles by Language -->
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <div style="width:3px;height:20px;background:#DF4E10;border-radius:2px;flex-shrink:0;"></div>
        <div style="font-size:11px;font-weight:700;color:#002856;text-transform:uppercase;letter-spacing:1px;">Articles by Language</div>
      </div>
      <canvas id="chartLanguages"></canvas>
    </div>

  </div>
</main>

<script>
const ctxP = document.getElementById('chartProducts').getContext('2d');
new Chart(ctxP, {
  type: 'bar',
  data: {
    labels: PRODUCT_LABELS,
    datasets: [{
      label: 'Articles',
      data: PRODUCT_DATA,
      backgroundColor: PRODUCT_COLORS,
      borderRadius: 4,
      borderSkipped: false
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: ctx => ' ' + ctx.parsed.x + ' articles' } }
    },
    scales: {
      x: {
        grid: { color: '#F1F5F9' },
        ticks: { color: '#64748B', font: { family: 'Barlow', size: 12 } }
      },
      y: {
        grid: { display: false },
        ticks: { color: '#334155', font: { family: 'Barlow', size: 12, weight: '600' } }
      }
    }
  }
});

const ctxL = document.getElementById('chartLanguages').getContext('2d');
new Chart(ctxL, {
  type: 'doughnut',
  data: {
    labels: LANG_LABELS,
    datasets: [{
      data: LANG_DATA,
      backgroundColor: ['#002856','#DF4E10','#3B6FA0','#F57A40','#1A4A7A','#C0A882'],
      borderWidth: 2,
      borderColor: '#FFFFFF'
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#334155', font: { family: 'Barlow', size: 12 }, padding: 16 }
      }
    },
    cutout: '65%'
  }
});
</script>
</body>
</html>"""

html = (
    html.replace("LOGO_TAG", logo_tag)
    .replace("GENERATED_DATE", generated_date)
    .replace("TOTAL", str(total))
    .replace("TOP_PRODUCT", top_product)
    .replace("TOP_PRODUCT_COUNT", str(top_product_count))
    .replace("LANG_COUNT", str(lang_count))
    .replace("PRODUCT_LABELS", product_labels)
    .replace("PRODUCT_DATA", product_data)
    .replace("PRODUCT_COLORS", product_colors)
    .replace("LANG_LABELS", lang_labels)
    .replace("LANG_DATA", lang_data)
)

with open("dashboard_executive.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard generated -> dashboard_executive.html")
print(f"  Total: {total} articles")
print(f"  Top product: {top_product} ({top_product_count})")
print(f"  Languages: {lang_count}")
