"""
Lighthouse HTML Report Generator

Usage:
    python3 generate_report.py <csv_path> <target_url> <runs>

Reads the CSV produced by the lighthouse measurement loop,
computes statistics, and generates an HTML report that opens in the browser.
"""

import statistics
import os
import sys
import html as html_mod
from datetime import datetime


def read_csv(path):
    data = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 7:
                continue
            try:
                data.append(
                    {
                        "run": int(parts[0]),
                        "ttfb": float(parts[1]),
                        "fcp": float(parts[2]),
                        "lcp": float(parts[3]),
                        "cls": float(parts[4]),
                        "inp": float(parts[5]),
                        "score": float(parts[6]),
                    }
                )
            except (ValueError, IndexError):
                continue
    return data


def calc_stats(values):
    s = sorted(values)
    n = len(s)
    return {
        "min": min(values),
        "max": max(values),
        "avg": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if n > 1 else 0,
        "p75": s[int(n * 0.75)] if n > 1 else s[0],
        "p90": s[int(n * 0.90)] if n > 1 else s[0],
    }


THRESHOLDS = {
    "TTFB": (800, 1800),
    "FCP": (1800, 3000),
    "LCP": (2500, 4000),
    "CLS": (0.1, 0.25),
    "INP": (200, 500),
}


def grade(name, value):
    if name == "Score":
        if value >= 90:
            return ("good", "Good")
        if value >= 50:
            return ("warn", "Needs Improvement")
        return ("poor", "Poor")
    g, ni = THRESHOLDS[name]
    if value <= g:
        return ("good", "Good")
    if value <= ni:
        return ("warn", "Needs Improvement")
    return ("poor", "Poor")


def generate(csv_path, target_url, runs):
    data = read_csv(csv_path)
    if not data:
        print("ERROR: No valid measurement data found")
        sys.exit(1)

    safe_url = html_mod.escape(target_url)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    metrics = {}
    for name, key in [("TTFB", "ttfb"), ("FCP", "fcp"), ("LCP", "lcp"), ("CLS", "cls"), ("INP", "inp")]:
        metrics[name] = calc_stats([d[key] for d in data])
    score_vals = [d["score"] * 100 for d in data]
    metrics["Score"] = calc_stats(score_vals)

    # --- Individual rows ---
    rows_html = ""
    for d in data:
        score_cls, _ = grade("Score", d["score"] * 100)
        rows_html += f"""<tr>
      <td>{d['run']}</td>
      <td>{d['ttfb']:.1f}</td><td>{d['fcp']:.1f}</td><td>{d['lcp']:.1f}</td>
      <td>{d['cls']:.4f}</td><td>{d['inp']:.0f}</td>
      <td class="{score_cls}">{d['score']*100:.0f}</td>
    </tr>"""

    # --- Stats rows ---
    metric_descs = {
        "TTFB": "Time to First Byte",
        "FCP": "First Contentful Paint",
        "LCP": "Largest Contentful Paint",
        "CLS": "Cumulative Layout Shift",
        "INP": "Interaction to Next Paint",
    }
    stats_rows = ""
    for name in ["TTFB", "FCP", "LCP", "CLS", "INP"]:
        s = metrics[name]
        fmt = ".4f" if name == "CLS" else ".1f" if name != "INP" else ".0f"
        unit = "" if name == "CLS" else "ms"
        g_cls, _ = grade(name, s["median"])
        desc = metric_descs[name]
        stats_rows += f"""<tr>
      <td><strong>{name}</strong><span class="metric-desc">{desc}</span></td>
      <td>{s['avg']:{fmt}}{unit}</td>
      <td class="{g_cls}">{s['median']:{fmt}}{unit}</td>
      <td>{s['p75']:{fmt}}{unit}</td><td>{s['p90']:{fmt}}{unit}</td>
      <td>{s['min']:{fmt}}{unit}</td><td>{s['max']:{fmt}}{unit}</td>
      <td>{s['stdev']:{fmt}}{unit}</td>
    </tr>"""

    ss = metrics["Score"]
    sg_cls, _ = grade("Score", ss["median"])
    stats_rows += f"""<tr>
  <td><strong>Score</strong><span class="metric-desc">Overall Performance</span></td>
  <td>{ss['avg']:.0f}</td><td class="{sg_cls}">{ss['median']:.0f}</td>
  <td>-</td><td>-</td>
  <td>{ss['min']:.0f}</td><td>{ss['max']:.0f}</td><td>-</td>
</tr>"""

    # --- Sanitize URL for filename ---
    safe_filename_url = target_url.replace("https://", "").replace("http://", "").replace("/", "_")

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lighthouse Report - {safe_url}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
  :root {{ --good: #0cce6b; --warn: #ffa400; --poor: #ff4e42; --bg: #f8f9fa; --card: #fff; --border: #e0e0e0; --text: #1a1a1a; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.25rem; }}
  h1 {{ font-size: 1.5rem; }}
  .download-btn {{ display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; background: #228be6; color: #fff; border: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }}
  .download-btn:hover {{ background: #1c7ed6; }}
  .download-btn:active {{ background: #1971c2; }}
  .download-btn svg {{ width: 14px; height: 14px; fill: currentColor; }}
  .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  .meta span {{ margin-right: 1.5rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.25rem; }}
  .card h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th, td {{ padding: 0.5rem 0.75rem; text-align: right; border-bottom: 1px solid var(--border); }}
  th {{ background: #f1f3f5; font-weight: 600; text-align: right; }}
  th:first-child, td:first-child {{ text-align: left; }}
  .good {{ color: var(--good); font-weight: 700; }}
  .warn {{ color: var(--warn); font-weight: 700; }}
  .poor {{ color: var(--poor); font-weight: 700; }}
  .metric-desc {{ font-size: 0.75rem; color: #868e96; font-weight: 400; display: block; margin-top: 2px; }}
  .cwv {{ font-size: 0.8rem; }}
  .cwv td, .cwv th {{ padding: 0.35rem 0.75rem; }}
  .valid-runs {{ font-size: 0.8rem; color: #868e96; margin-top: 0.5rem; }}
</style>
</head>
<body>
<div class="container" id="report">
  <div class="header">
    <h1>Lighthouse Performance Report</h1>
    <button class="download-btn" onclick="downloadAsImage()">
      <svg viewBox="0 0 16 16"><path d="M8 12l-4-4h2.5V2h3v6H12L8 12zm-6 2h12v1.5H2V14z"/></svg>
      Download PNG
    </button>
  </div>
  <div class="meta">
    <span><strong>URL:</strong> {safe_url}</span>
    <span><strong>Runs:</strong> {runs} (valid: {len(data)})</span>
    <span><strong>Throttling:</strong> Simulated 4G</span>
    <span><strong>Date:</strong> {now}</span>
  </div>

  <div class="card">
    <h2>Individual Results</h2>
    <table>
      <thead><tr><th>#</th><th>TTFB (ms)</th><th>FCP (ms)</th><th>LCP (ms)</th><th>CLS</th><th>INP (ms)</th><th>Score</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Statistics</h2>
    <table>
      <thead><tr><th>Metric</th><th>Avg</th><th>Median</th><th>P75</th><th>P90</th><th>Min</th><th>Max</th><th>StdDev</th></tr></thead>
      <tbody>{stats_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Core Web Vitals Thresholds</h2>
    <table class="cwv">
      <thead><tr><th>Metric</th><th class="good">Good</th><th class="warn">Needs Improvement</th><th class="poor">Poor</th></tr></thead>
      <tbody>
        <tr><td>TTFB<span class="metric-desc">Time to First Byte</span></td><td>&le; 800ms</td><td>800 ~ 1,800ms</td><td>&gt; 1,800ms</td></tr>
        <tr><td>FCP<span class="metric-desc">First Contentful Paint</span></td><td>&le; 1,800ms</td><td>1,800 ~ 3,000ms</td><td>&gt; 3,000ms</td></tr>
        <tr><td>LCP<span class="metric-desc">Largest Contentful Paint</span></td><td>&le; 2,500ms</td><td>2,500 ~ 4,000ms</td><td>&gt; 4,000ms</td></tr>
        <tr><td>CLS<span class="metric-desc">Cumulative Layout Shift</span></td><td>&le; 0.1</td><td>0.1 ~ 0.25</td><td>&gt; 0.25</td></tr>
        <tr><td>INP<span class="metric-desc">Interaction to Next Paint</span></td><td>&le; 200ms</td><td>200 ~ 500ms</td><td>&gt; 500ms</td></tr>
      </tbody>
    </table>
  </div>
</div>
<script>
function downloadAsImage() {{
  const btn = document.querySelector('.download-btn');
  btn.textContent = 'Capturing...';
  btn.disabled = true;
  html2canvas(document.getElementById('report'), {{
    scale: 2,
    backgroundColor: '#f8f9fa',
    useCORS: true
  }}).then(canvas => {{
    const link = document.createElement('a');
    link.download = 'lighthouse_report_{safe_filename_url}_{now.replace(" ","_")}.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
    btn.innerHTML = '<svg viewBox="0 0 16 16" style="width:14px;height:14px;fill:currentColor"><path d="M8 12l-4-4h2.5V2h3v6H12L8 12zm-6 2h12v1.5H2V14z"/></svg> Download PNG';
    btn.disabled = false;
  }}).catch(() => {{
    btn.textContent = 'Error - retry';
    btn.disabled = false;
  }});
}}
</script>
</body>
</html>"""

    timestamp = os.path.basename(csv_path).replace("lighthouse_results_", "").replace(".csv", "")
    html_path = f"/tmp/lighthouse_report_{timestamp}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML report: {html_path}")
    os.system(f"open {html_path}")
    print("Opened report in browser.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <csv_path> <target_url> <runs>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2], int(sys.argv[3]))
