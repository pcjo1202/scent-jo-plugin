---
description: Lighthouse CLI(Simulated 4G Throttling)로 대상 URL을 N회 측정하여 TTFB, FCP, LCP, CLS 통계 보고서를 생성한다. 인수로 URL과 측정 횟수를 지정할 수 있다. 예: /lighthouse, /lighthouse https://cashwalklabs.io/news, /lighthouse https://cashwalklabs.io/news 5, /lighthouse 5 (기본 URL에 5회 측정).
allowed-tools:
  - Bash(lighthouse *)
  - Bash(python3 *)
  - Bash(open /tmp/lighthouse_report_*)
  - Read
  - TodoWrite
---

# Lighthouse Performance Measurement

Lighthouse CLI(Simulated 4G Throttling, Headless Chrome)로 대상 URL을 반복 측정하여 TTFB, FCP, LCP, CLS 통계 보고서를 생성한다.

---

## Step 1. $ARGUMENTS 파싱

`$ARGUMENTS`에서 **URL**과 **측정 횟수(RUNS)**를 추출한다.

| 인수 패턴 | URL | RUNS |
|-----------|-----|------|
| *(없음)* | `https://cashwalklabs.io/news` | `10` |
| `https://example.com` | 해당 URL | `10` |
| `5` (숫자만) | `https://cashwalklabs.io/news` | `5` |
| `https://example.com 5` | 해당 URL | `5` |
| `5 https://example.com` | 해당 URL | `5` |

**파싱 규칙:**
- `https://` 또는 `http://`로 시작하는 토큰 → URL
- 숫자로만 이루어진 토큰 → RUNS (1~30 범위, 벗어나면 10으로 보정)
- 나머지 토큰 무시

---

## Step 2. Lighthouse CLI 설치 확인

```bash
lighthouse --version
```

미설치 시 사용자에게 `npm i -g lighthouse` 실행을 안내하고 중단한다.

---

## Step 3. 측정 실행

결과를 `/tmp/lighthouse_results_YYYYMMDD_HHMMSS.csv`에 저장한다. 타임스탬프를 파일명에 포함하여 이전 결과를 덮어쓰지 않는다.

다음 Bash 스크립트를 실행한다. `TARGET_URL`과 `RUNS`를 Step 1에서 파싱한 값으로 대체한다.

```bash
TARGET_URL="<파싱된 URL>"
RUNS=<파싱된 횟수>
RESULT_FILE="/tmp/lighthouse_results_$(date +%Y%m%d_%H%M%S).csv"

echo "=== Lighthouse ${RUNS}회 측정 시작 (Simulated 4G Throttling) ==="
echo "URL: ${TARGET_URL}"
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

for i in $(seq 1 $RUNS); do
  echo "--- 측정 #$i 시작: $(date '+%H:%M:%S') ---"
  result=$(lighthouse "$TARGET_URL" \
    --only-categories=performance \
    --throttling-method=simulate \
    --preset=perf \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --output=json \
    --quiet 2>/dev/null)

  ttfb=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['audits']['server-response-time']['numericValue'])" 2>/dev/null)
  fcp=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['audits']['first-contentful-paint']['numericValue'])" 2>/dev/null)
  lcp=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['audits']['largest-contentful-paint']['numericValue'])" 2>/dev/null)
  cls=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['audits']['cumulative-layout-shift']['numericValue'])" 2>/dev/null)
  perf=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['categories']['performance']['score'])" 2>/dev/null)

  echo "  TTFB: ${ttfb}ms | FCP: ${fcp}ms | LCP: ${lcp}ms | CLS: ${cls} | Score: ${perf}"
  echo "$i,$ttfb,$fcp,$lcp,$cls,$perf" >> "$RESULT_FILE"
done

echo ""
echo "=== 전체 측정 완료: $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "결과 파일: $RESULT_FILE"
```

**timeout은 600000ms(10분)**으로 설정한다. 측정 중 한 회차에서 파싱 실패(빈 값)가 발생하면 해당 회차를 건너뛰고 로그에 경고를 남긴다.

---

## Step 4. 통계 산출

측정 완료 후 동일 CSV 파일을 읽어 통계를 계산한다.

```bash
python3 << 'PYEOF'
import statistics, sys

data = []
with open("RESULT_FILE_PATH") as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) < 6:
            continue
        try:
            data.append({
                'run': int(parts[0]),
                'ttfb': float(parts[1]),
                'fcp': float(parts[2]),
                'lcp': float(parts[3]),
                'cls': float(parts[4]),
                'score': float(parts[5])
            })
        except (ValueError, IndexError):
            continue

if not data:
    print("ERROR: 유효한 측정 결과 없음")
    sys.exit(1)

n = len(data)

def stats(values):
    s = sorted(values)
    return {
        'min': min(values),
        'max': max(values),
        'avg': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if len(values) > 1 else 0,
        'p75': s[int(n * 0.75)] if n > 1 else s[0],
        'p90': s[int(n * 0.90)] if n > 1 else s[0],
    }

for name, key in [('TTFB', 'ttfb'), ('FCP', 'fcp'), ('LCP', 'lcp')]:
    values = [d[key] for d in data]
    s = stats(values)
    print(f"{name}_AVG={s['avg']:.1f}")
    print(f"{name}_MED={s['median']:.1f}")
    print(f"{name}_MIN={s['min']:.1f}")
    print(f"{name}_MAX={s['max']:.1f}")
    print(f"{name}_P75={s['p75']:.1f}")
    print(f"{name}_P90={s['p90']:.1f}")
    print(f"{name}_STD={s['stdev']:.1f}")

# CLS는 단위 없음 (소수점 4자리까지)
cls_values = [d['cls'] for d in data]
cs = stats(cls_values)
print(f"CLS_AVG={cs['avg']:.4f}")
print(f"CLS_MED={cs['median']:.4f}")
print(f"CLS_MIN={cs['min']:.4f}")
print(f"CLS_MAX={cs['max']:.4f}")
print(f"CLS_P75={cs['p75']:.4f}")
print(f"CLS_P90={cs['p90']:.4f}")
print(f"CLS_STD={cs['stdev']:.4f}")

scores = [d['score'] for d in data]
print(f"SCORE_AVG={statistics.mean(scores)*100:.0f}")
print(f"SCORE_MED={statistics.median(scores)*100:.0f}")
print(f"SCORE_MIN={min(scores)*100:.0f}")
print(f"SCORE_MAX={max(scores)*100:.0f}")
PYEOF
```

`RESULT_FILE_PATH`는 Step 3에서 생성한 CSV 파일 경로로 대체한다.

---

## Step 5. 보고서 출력

다음 마크다운 형식을 **정확히** 따라 출력한다. 모든 수치를 Step 3, 4의 결과로 채운다.

```
## Lighthouse 성능 측정 보고서

**URL:** `{TARGET_URL}`
**측정 조건:** Lighthouse CLI, Simulated 4G Throttling, Headless Chrome
**측정 횟수:** {RUNS}회 | **측정 일시:** {YYYY-MM-DD HH:MM}

---

### 개별 측정 결과

| # | TTFB (ms) | FCP (ms) | LCP (ms) | CLS | Performance Score |
|---|-----------|----------|----------|-----|-------------------|
| 1 | {값} | {값} | {값} | {값} | {값} |
| ... | ... | ... | ... | ... | ... |

---

### 통계 요약

| 지표 | Avg | Median | P75 | P90 | Min | Max | StdDev |
|------|-----|--------|-----|-----|-----|-----|--------|
| **TTFB** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **FCP** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **LCP** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **CLS** | {값} | {값} | {값} | {값} | {값} | {값} | {값} |
| **Score** | {값} | {값} | — | — | {값} | {값} | — |

---

### 분석

- **TTFB:** {Good ≤800ms 기준 대비 평가. 등급 표시}
- **FCP:** {Good ≤1,800ms 기준 대비 평가. Median과 P90 기준으로 분석}
- **LCP:** {Good ≤2,500ms 기준 대비 평가. P90 스파이크 주의 여부}
- **CLS:** {Good ≤0.1 기준 대비 평가. 레이아웃 안정성 분석}
- **분산:** {StdDev가 Avg 대비 20% 이상인 지표가 있으면 불안정으로 표시, 스파이크 회차 언급}

---

### 참고: Core Web Vitals 등급 기준

| 메트릭 | Good ✅ | Needs Improvement ⚠️ | Poor ❌ |
|--------|---------|----------------------|--------|
| TTFB | ≤ 800ms | 800 ~ 1,800ms | > 1,800ms |
| FCP  | ≤ 1,800ms | 1,800 ~ 3,000ms | > 3,000ms |
| LCP  | ≤ 2,500ms | 2,500 ~ 4,000ms | > 4,000ms |
| CLS  | ≤ 0.1 | 0.1 ~ 0.25 | > 0.25 |
```

**등급 판정:**
- Median 기준으로 기본 등급 판정
- P90이 다음 등급 임계값을 넘으면 추가 경고 (예: "Median Good이나 P90 Needs Improvement 진입")
- StdDev가 Avg의 20%를 초과하면 "측정 편차 큼" 경고 추가

---

## Step 6. HTML 보고서 생성 및 열기

Step 5의 마크다운 보고서 출력 후, 동일한 내용을 HTML 파일로 생성하고 브라우저에서 자동으로 연다.

HTML 파일은 CSV와 같은 타임스탬프를 사용하여 `/tmp/lighthouse_report_YYYYMMDD_HHMMSS.html`에 저장한다.

다음 Python 스크립트를 실행한다. `RESULT_FILE_PATH`는 Step 3에서 생성한 CSV 파일 경로로, `TARGET_URL`과 `RUNS`는 Step 1에서 파싱한 값으로 대체한다.

```bash
python3 << 'PYEOF'
import statistics, os, webbrowser
from datetime import datetime

RESULT_FILE = "RESULT_FILE_PATH"
TARGET_URL = "TARGET_URL_VALUE"
RUNS = RUNS_VALUE

data = []
with open(RESULT_FILE) as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) < 6:
            continue
        try:
            data.append({
                'run': int(parts[0]),
                'ttfb': float(parts[1]),
                'fcp': float(parts[2]),
                'lcp': float(parts[3]),
                'cls': float(parts[4]),
                'score': float(parts[5])
            })
        except (ValueError, IndexError):
            continue

n = len(data)

def calc_stats(values):
    s = sorted(values)
    return {
        'min': min(values), 'max': max(values),
        'avg': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if len(values) > 1 else 0,
        'p75': s[int(len(s) * 0.75)] if len(s) > 1 else s[0],
        'p90': s[int(len(s) * 0.90)] if len(s) > 1 else s[0],
    }

metrics = {}
for name, key in [('TTFB', 'ttfb'), ('FCP', 'fcp'), ('LCP', 'lcp'), ('CLS', 'cls')]:
    metrics[name] = calc_stats([d[key] for d in data])
score_vals = [d['score'] * 100 for d in data]
metrics['Score'] = calc_stats(score_vals)

thresholds = {
    'TTFB': (800, 1800), 'FCP': (1800, 3000),
    'LCP': (2500, 4000), 'CLS': (0.1, 0.25),
}

def grade(name, value):
    if name == 'Score':
        if value >= 90: return ('good', 'Good')
        if value >= 50: return ('warn', 'Needs Improvement')
        return ('poor', 'Poor')
    g, ni = thresholds[name]
    if value <= g: return ('good', 'Good')
    if value <= ni: return ('warn', 'Needs Improvement')
    return ('poor', 'Poor')

now = datetime.now().strftime('%Y-%m-%d %H:%M')

# --- HTML 생성 ---
rows_html = ""
for d in data:
    score_cls, _ = grade('Score', d['score'] * 100)
    rows_html += f"""<tr>
      <td>{d['run']}</td>
      <td>{d['ttfb']:.1f}</td><td>{d['fcp']:.1f}</td><td>{d['lcp']:.1f}</td>
      <td>{d['cls']:.4f}</td>
      <td class="{score_cls}">{d['score']*100:.0f}</td>
    </tr>"""

metric_descs = {
    'TTFB': 'Time to First Byte',
    'FCP': 'First Contentful Paint',
    'LCP': 'Largest Contentful Paint',
    'CLS': 'Cumulative Layout Shift',
}

stats_rows = ""
for name in ['TTFB', 'FCP', 'LCP', 'CLS']:
    s = metrics[name]
    fmt = '.4f' if name == 'CLS' else '.1f'
    unit = '' if name == 'CLS' else 'ms'
    g_cls, g_label = grade(name, s['median'])
    desc = metric_descs[name]
    stats_rows += f"""<tr>
      <td><strong>{name}</strong><span class="metric-desc">{desc}</span></td>
      <td>{s['avg']:{fmt}}{unit}</td>
      <td class="{g_cls}">{s['median']:{fmt}}{unit}</td>
      <td>{s['p75']:{fmt}}{unit}</td><td>{s['p90']:{fmt}}{unit}</td>
      <td>{s['min']:{fmt}}{unit}</td><td>{s['max']:{fmt}}{unit}</td>
      <td>{s['stdev']:{fmt}}{unit}</td>
    </tr>"""
ss = metrics['Score']
sg_cls, _ = grade('Score', ss['median'])
stats_rows += f"""<tr>
  <td><strong>Score</strong><span class="metric-desc">Overall Performance</span></td>
  <td>{ss['avg']:.0f}</td><td class="{sg_cls}">{ss['median']:.0f}</td>
  <td>—</td><td>—</td>
  <td>{ss['min']:.0f}</td><td>{ss['max']:.0f}</td><td>—</td>
</tr>"""

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lighthouse Report — {TARGET_URL}</title>
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
    <span><strong>URL:</strong> {TARGET_URL}</span>
    <span><strong>Runs:</strong> {RUNS}</span>
    <span><strong>Throttling:</strong> Simulated 4G</span>
    <span><strong>Date:</strong> {now}</span>
  </div>

  <div class="card">
    <h2>Individual Results</h2>
    <table>
      <thead><tr><th>#</th><th>TTFB (ms)</th><th>FCP (ms)</th><th>LCP (ms)</th><th>CLS</th><th>Score</th></tr></thead>
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
        <tr><td>TTFB<span class="metric-desc">Time to First Byte — server response time</span></td><td>&le; 800ms</td><td>800 ~ 1,800ms</td><td>&gt; 1,800ms</td></tr>
        <tr><td>FCP<span class="metric-desc">First Contentful Paint — first visible content render</span></td><td>&le; 1,800ms</td><td>1,800 ~ 3,000ms</td><td>&gt; 3,000ms</td></tr>
        <tr><td>LCP<span class="metric-desc">Largest Contentful Paint — main content render</span></td><td>&le; 2,500ms</td><td>2,500 ~ 4,000ms</td><td>&gt; 4,000ms</td></tr>
        <tr><td>CLS<span class="metric-desc">Cumulative Layout Shift — visual stability</span></td><td>&le; 0.1</td><td>0.1 ~ 0.25</td><td>&gt; 0.25</td></tr>
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
    link.download = 'lighthouse_report_{TARGET_URL.replace("https://","").replace("/","_")}_{now.replace(" ","_")}.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
    btn.innerHTML = '<svg viewBox="0 0 16 16" style="width:14px;height:14px;fill:currentColor"><path d="M8 12l-4-4h2.5V2h3v6H12L8 12zm-6 2h12v1.5H2V14z"/></svg> Download PNG';
    btn.disabled = false;
  }}).catch(() => {{
    btn.textContent = 'Error — retry';
    btn.disabled = false;
  }});
}}
</script>
</body>
</html>"""

# CSV 파일명에서 타임스탬프 추출하여 HTML 파일명 생성
timestamp = os.path.basename(RESULT_FILE).replace('lighthouse_results_', '').replace('.csv', '')
html_path = f"/tmp/lighthouse_report_{timestamp}.html"
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML 보고서 생성: {html_path}")

# 브라우저에서 자동 열기
os.system(f"open {html_path}")
print("브라우저에서 보고서를 열었습니다.")
PYEOF
```

**주의사항:**
- `open` 명령은 macOS 전용이다. Linux에서는 `xdg-open`, Windows에서는 `start`로 대체한다.
- HTML 보고서는 Median 기준 등급에 따라 수치에 색상(초록/주황/빨강)이 적용된다.
