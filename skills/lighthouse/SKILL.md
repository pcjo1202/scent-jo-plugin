---
name: lighthouse
description: Lighthouse CLI(Simulated 4G Throttling)로 대상 URL을 N회 측정하여 TTFB, FCP, LCP, CLS, INP 통계 보고서를 생성한다. URL은 필수 인수이며, 측정 횟수는 선택(기본 10회). 예: /lighthouse https://example.com, /lighthouse https://example.com 5.
allowed-tools:
  - Bash(lighthouse --version)
  - Bash(lighthouse "http*" --only-categories=performance *)
  - Bash(lighthouse --output-path=* *)
  - Bash(TARGET_URL=* RUNS=* RESULT_FILE=* SKIPPED=0 *)
  - Bash(python3 << 'PYEOF'*)
  - Bash(python3 */scripts/generate_report.py *)
  - Bash(open /tmp/lighthouse_report_*)
  - Read
  - TodoWrite
---

# Lighthouse Performance Measurement

Lighthouse CLI(Simulated 4G Throttling, Headless Chrome)로 대상 URL을 반복 측정하여 TTFB, FCP, LCP, CLS, INP 통계 보고서를 생성한다.

---

## Step 1. $ARGUMENTS 파싱

`$ARGUMENTS`에서 **URL**(필수)과 **측정 횟수(RUNS)**(선택)를 추출한다.

| 인수 패턴 | URL | RUNS |
|-----------|-----|------|
| *(없음)* | **오류 — URL을 입력해달라고 안내** | — |
| `https://example.com` | 해당 URL | `10` |
| `https://example.com 5` | 해당 URL | `5` |
| `5 https://example.com` | 해당 URL | `5` |
| `5` (숫자만) | **오류 — URL을 입력해달라고 안내** | — |

**파싱 규칙:**
- `https://` 또는 `http://`로 시작하는 토큰 → URL (**필수**, 없으면 사용자에게 URL 입력을 요청하고 중단)
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
SKIPPED=0

echo "=== Lighthouse ${RUNS}회 측정 시작 (Simulated 4G Throttling) ==="
echo "URL: ${TARGET_URL}"
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

for i in $(seq 1 $RUNS); do
  echo "--- 측정 #$i 시작: $(date '+%H:%M:%S') ---"
  result=$(lighthouse "$TARGET_URL" \
    --only-categories=performance \
    --throttling-method=simulate \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --max-wait-for-load=60000 \
    --output=json \
    --quiet 2>/dev/null)

  if [ -z "$result" ]; then
    echo "  [WARN] 측정 #$i 실패 — Lighthouse 응답 없음. 건너뜀."
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  parsed=$(echo "$result" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    a = d['audits']
    ttfb = a['server-response-time']['numericValue']
    fcp  = a['first-contentful-paint']['numericValue']
    lcp  = a['largest-contentful-paint']['numericValue']
    cls  = a['cumulative-layout-shift']['numericValue']
    inp  = a.get('interaction-to-next-paint', {}).get('numericValue', 0)
    score = d['categories']['performance']['score']
    print(f'{ttfb},{fcp},{lcp},{cls},{inp},{score}')
except Exception as e:
    print(f'ERROR:{e}', file=sys.stderr)
" 2>/dev/null)

  if [ -z "$parsed" ] || echo "$parsed" | grep -q "^ERROR"; then
    echo "  [WARN] 측정 #$i 파싱 실패. 건너뜀."
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  ttfb=$(echo "$parsed" | cut -d, -f1)
  fcp=$(echo "$parsed" | cut -d, -f2)
  lcp=$(echo "$parsed" | cut -d, -f3)
  cls=$(echo "$parsed" | cut -d, -f4)
  inp=$(echo "$parsed" | cut -d, -f5)
  score=$(echo "$parsed" | cut -d, -f6)

  echo "  TTFB: ${ttfb}ms | FCP: ${fcp}ms | LCP: ${lcp}ms | CLS: ${cls} | INP: ${inp}ms | Score: ${score}"
  echo "$i,$ttfb,$fcp,$lcp,$cls,$inp,$score" >> "$RESULT_FILE"
done

echo ""
echo "=== 전체 측정 완료: $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "유효: $((RUNS - SKIPPED))/${RUNS}회 | 건너뜀: ${SKIPPED}회"
echo "결과 파일: $RESULT_FILE"
```

---

## Step 4. 통계 산출

측정 완료 후, Step 3에서 출력된 `$RESULT_FILE` 경로를 사용하여 통계를 계산한다.

```bash
python3 << 'PYEOF'
import statistics, sys

RESULT_FILE = "<Step 3에서 출력된 RESULT_FILE 경로>"

data = []
with open(RESULT_FILE) as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) < 7:
            continue
        try:
            data.append({
                'run': int(parts[0]),
                'ttfb': float(parts[1]),
                'fcp': float(parts[2]),
                'lcp': float(parts[3]),
                'cls': float(parts[4]),
                'inp': float(parts[5]),
                'score': float(parts[6])
            })
        except (ValueError, IndexError):
            continue

if not data:
    print("ERROR: 유효한 측정 결과 없음")
    sys.exit(1)

def stats(values):
    s = sorted(values)
    n = len(s)
    return {
        'min': min(values),
        'max': max(values),
        'avg': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if n > 1 else 0,
        'p75': s[int(n * 0.75)] if n > 1 else s[0],
        'p90': s[int(n * 0.90)] if n > 1 else s[0],
    }

for name, key in [('TTFB', 'ttfb'), ('FCP', 'fcp'), ('LCP', 'lcp'), ('INP', 'inp')]:
    values = [d[key] for d in data]
    s = stats(values)
    print(f"{name}_AVG={s['avg']:.1f}")
    print(f"{name}_MED={s['median']:.1f}")
    print(f"{name}_MIN={s['min']:.1f}")
    print(f"{name}_MAX={s['max']:.1f}")
    print(f"{name}_P75={s['p75']:.1f}")
    print(f"{name}_P90={s['p90']:.1f}")
    print(f"{name}_STD={s['stdev']:.1f}")

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

print(f"\nVALID_RUNS={len(data)}")
PYEOF
```

---

## Step 5. 보고서 출력

다음 마크다운 형식을 **정확히** 따라 출력한다. 모든 수치를 Step 3, 4의 결과로 채운다.

```
## Lighthouse 성능 측정 보고서

**URL:** `{TARGET_URL}`
**측정 조건:** Lighthouse CLI, Simulated 4G Throttling, Headless Chrome
**측정 횟수:** {유효 횟수}/{RUNS}회 | **측정 일시:** {YYYY-MM-DD HH:MM}

---

### 개별 측정 결과

| # | TTFB (ms) | FCP (ms) | LCP (ms) | CLS | INP (ms) | Performance Score |
|---|-----------|----------|----------|-----|----------|-------------------|
| 1 | {값} | {값} | {값} | {값} | {값} | {값} |
| ... | ... | ... | ... | ... | ... | ... |

---

### 통계 요약

| 지표 | Avg | Median | P75 | P90 | Min | Max | StdDev |
|------|-----|--------|-----|-----|-----|-----|--------|
| **TTFB** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **FCP** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **LCP** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **CLS** | {값} | {값} | {값} | {값} | {값} | {값} | {값} |
| **INP** | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms | {값}ms |
| **Score** | {값} | {값} | — | — | {값} | {값} | — |

---

### 분석

- **TTFB:** {Good ≤800ms 기준 대비 평가. 등급 표시}
- **FCP:** {Good ≤1,800ms 기준 대비 평가. Median과 P90 기준으로 분석}
- **LCP:** {Good ≤2,500ms 기준 대비 평가. P90 스파이크 주의 여부}
- **CLS:** {Good ≤0.1 기준 대비 평가. 레이아웃 안정성 분석}
- **INP:** {Good ≤200ms 기준 대비 평가. 상호작용 응답성 분석}
- **분산:** {StdDev가 Avg 대비 20% 이상인 지표가 있으면 불안정으로 표시, 스파이크 회차 언급}

---

### 참고: Core Web Vitals 등급 기준

| 메트릭 | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| TTFB | ≤ 800ms | 800 ~ 1,800ms | > 1,800ms |
| FCP  | ≤ 1,800ms | 1,800 ~ 3,000ms | > 3,000ms |
| LCP  | ≤ 2,500ms | 2,500 ~ 4,000ms | > 4,000ms |
| CLS  | ≤ 0.1 | 0.1 ~ 0.25 | > 0.25 |
| INP  | ≤ 200ms | 200 ~ 500ms | > 500ms |
```

**등급 판정:**
- Median 기준으로 기본 등급 판정
- P90이 다음 등급 임계값을 넘으면 추가 경고 (예: "Median Good이나 P90 Needs Improvement 진입")
- StdDev가 Avg의 20%를 초과하면 "측정 편차 큼" 경고 추가

---

## Step 6. HTML 보고서 생성 및 열기

이 스킬에 번들된 `scripts/generate_report.py`를 사용하여 HTML 보고서를 생성하고 브라우저에서 연다.

```bash
python3 <이 스킬의 scripts/generate_report.py 경로> "<RESULT_FILE 경로>" "<TARGET_URL>" <RUNS>
```

스크립트가 자동으로 `/tmp/lighthouse_report_YYYYMMDD_HHMMSS.html`을 생성하고 `open` 명령으로 브라우저를 연다.
