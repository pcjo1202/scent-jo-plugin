---
name: lighthouse
description: "Lighthouse CLI(Simulated 4G Throttling)로 대상 URL을 N회 측정하여 TTFB, FCP, LCP, CLS, INP 통계 보고서를 생성한다. URL은 필수 인수이며, 측정 횟수는 선택(기본 10회). 예: /lighthouse https://example.com, /lighthouse https://example.com 5."
allowed-tools:
  - Bash(node --version)
  - Bash(lighthouse --version)
  - Bash(lighthouse "http*" --only-categories=performance *)
  - Bash(npx lighthouse@latest "http*" --only-categories=performance *)
  - Bash(npm i -g lighthouse*)
  - Bash(TARGET_URL=* LH_CMD=* RUNS=* RESULT_FILE=* SKIPPED=0 *)
  - Bash(python3 << 'PYEOF'*)
  - Bash(python3 */scripts/generate_report.py *)
  - Bash(open /tmp/lighthouse_report_*)
  - Bash(cat /tmp/lighthouse_results_*)
  - Read
  - Write
  - TodoWrite
  - Agent
  - AskUserQuestion
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

## Step 2. 측정 환경 선택

AskUserQuestion 도구로 **두 가지 질문**을 동시에 던진다. 하나의 AskUserQuestion 호출에 2개 질문을 담아 한 번에 물어본다.

**질문 1 — 디바이스:**

| 선택지 | 설명 |
|--------|------|
| Mobile (기본) | 모바일 뷰포트 (Moto G Power 에뮬레이션) |
| Desktop | 데스크톱 뷰포트 (1350x940) |

**질문 2 — 쓰로틀링:**

| 선택지 | 설명 |
|--------|------|
| Simulated (기본) | 4G 시뮬레이션 — RTT 150ms, 1.6Mbps down, CPU 4x slowdown |
| Applied (DevTools) | Chrome 실제 쓰로틀링 적용 — RTT 150ms, 1.6Mbps down, CPU 4x slowdown |
| No Throttling | 쓰로틀링 없음 — 실제 네트워크 속도 사용 |
| Custom | 사용자 지정 (RTT, throughput, CPU 직접 입력) |

**응답 → 플래그 매핑:**

| 디바이스 | 플래그 |
|----------|--------|
| Mobile | *(없음 — Lighthouse 기본값)* |
| Desktop | `--preset=desktop` |

| 쓰로틀링 | 플래그 |
|----------|--------|
| Simulated | `--throttling-method=simulate` |
| Applied | `--throttling-method=devtools` |
| No Throttling | `--throttling-method=provided` |
| Custom | 사용자에게 추가 질문하여 플래그 확정 |

**Custom 선택 시 추가 질문:**
- "쓰로틀링 설정을 입력해주세요 (예: `--throttling.rttMs=150 --throttling.throughputKbps=1600 --throttling.cpuSlowdownMultiplier=4`)"
- 입력받은 값을 `--throttling-method=simulate`와 함께 Lighthouse CLI 플래그에 추가

두 응답을 조합하여 변수로 보관한다:
- `DEVICE_NAME`: 디바이스명 (예: `Mobile`, `Desktop`)
- `THROTTLE_NAME`: 쓰로틀링명 (예: `Simulated`, `Applied`, `No Throttling`, 또는 사용자 지정명)
- `THROTTLE_DESC`: 쓰로틀링 상세 설명 (예: `RTT 150ms, 1.6Mbps down, CPU 4x`)
- `PROFILE_NAME`: `{DEVICE_NAME} + {THROTTLE_NAME}` (예: `Mobile + Simulated`)
- `PROFILE_FLAGS`: 디바이스 플래그 + 쓰로틀링 플래그 결합 문자열

---

## Step 3. Lighthouse CLI 확인

먼저 Node.js 설치 여부를 확인한다:

```bash
node --version
```

**Node.js 미설치 시** → "Lighthouse 실행에 Node.js가 필요합니다. https://nodejs.org 에서 설치해주세요." 안내 후 **중단**.

Node.js가 있으면 Lighthouse 설치 여부를 확인한다:

```bash
lighthouse --version
```

**설치되어 있으면** → `LH_CMD=lighthouse`로 설정하고 Step 4로 진행.

**미설치 시** → AskUserQuestion으로 사용자에게 선택지를 제시한다:

| 선택지 | 설명 |
|--------|------|
| npm i -g lighthouse (Recommended) | 글로벌 설치 후 실행. 이후 빠르게 재사용 가능 |
| npx로 실행 | 설치 없이 바로 실행. 첫 실행 시 다운로드 시간 소요 |

- **글로벌 설치 선택 시** → `npm i -g lighthouse` 실행. 성공하면 `LH_CMD=lighthouse`. 실패 시(권한 등) npx 전환을 안내.
- **npx 선택 시** → `LH_CMD="npx lighthouse@latest"`로 설정.

이후 모든 측정 스크립트에서 `lighthouse` 대신 `$LH_CMD`를 사용한다.

---

## Step 4. 측정 실행 (Sub-Agent 병렬)

RUNS를 3등분하여 sub-agent 3개가 병렬로 측정한다. 각 sub-agent는 자신의 파트만 실행하고 개별 CSV에 결과를 저장한다.

**분배 규칙:**
- `RUNS_PER_AGENT = ceil(RUNS / 3)`
- Agent 1: 1 ~ RUNS_PER_AGENT
- Agent 2: RUNS_PER_AGENT+1 ~ RUNS_PER_AGENT*2
- Agent 3: RUNS_PER_AGENT*2+1 ~ RUNS
- RUNS가 3 이하이면 병렬 실행 없이 단일 실행

**각 sub-agent에 전달할 프롬프트:**

```
Lighthouse CLI로 성능 측정을 실행하라.

- URL: {TARGET_URL}
- 측정 회차: {START_RUN}번부터 {END_RUN}번까지
- 결과 파일: /tmp/lighthouse_results_{TIMESTAMP}_part{N}.csv
- Lighthouse 명령: {LH_CMD}
- Lighthouse 플래그: --only-categories=performance {PROFILE_FLAGS} --chrome-flags="--headless --no-sandbox --disable-gpu" --max-wait-for-load=60000 --output=json --quiet

각 회차마다 아래 Bash 스크립트를 실행하라:

TARGET_URL="{TARGET_URL}"
LH_CMD="{LH_CMD}"
RESULT_FILE="/tmp/lighthouse_results_{TIMESTAMP}_part{N}.csv"
SKIPPED=0

for i in $(seq {START_RUN} {END_RUN}); do
  echo "--- 측정 #$i 시작: $(date '+%H:%M:%S') ---"
  result=$($LH_CMD "$TARGET_URL" \
    --only-categories=performance \
    {PROFILE_FLAGS} \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --max-wait-for-load=60000 \
    --output=json \
    --quiet 2>/dev/null)

  if [ -z "$result" ]; then
    echo "  [WARN] 측정 #$i 실패 — 건너뜀."
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

echo "파트 {N} 완료 — 유효: $((({END_RUN} - {START_RUN} + 1) - SKIPPED))회"
```

**3개 sub-agent를 Agent 도구로 동시에 호출한다.** 모든 sub-agent 완료 후 다음 단계로 진행한다.

---

## Step 5. 결과 병합

3개 파트 CSV를 하나의 최종 CSV로 병합한다.

```bash
cat /tmp/lighthouse_results_{TIMESTAMP}_part1.csv \
    /tmp/lighthouse_results_{TIMESTAMP}_part2.csv \
    /tmp/lighthouse_results_{TIMESTAMP}_part3.csv \
    > /tmp/lighthouse_results_{TIMESTAMP}.csv 2>/dev/null
```

병합된 파일이 `RESULT_FILE`이 된다. 단일 실행(RUNS ≤ 3)인 경우 이 단계를 건너뛴다.

---

## Step 6. 통계 산출

측정 완료 후, Step 5에서 병합된 `$RESULT_FILE` 경로를 사용하여 통계를 계산한다.

```bash
python3 << 'PYEOF'
import statistics, sys

RESULT_FILE = "<RESULT_FILE 경로>"

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

## Step 7. 보고서 출력

다음 마크다운 형식을 **정확히** 따라 출력한다. 모든 수치를 Step 4, 6의 결과로 채운다.

```
## Lighthouse 성능 측정 보고서

**URL:** `{TARGET_URL}`
**디바이스:** {DEVICE_NAME} | **쓰로틀링:** {THROTTLE_NAME} ({THROTTLE_DESC})
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

> **Avg**: 전체 평균 | **Median**: 중앙값 (50번째 백분위, 등급 판정 기준) | **P75**: 75번째 백분위 | **P90**: 90번째 백분위 (스파이크 감지 기준) | **Min/Max**: 최솟값/최댓값 | **StdDev**: 표준편차 (측정 안정성 지표)

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

> 출처: [Core Web Vitals](https://web.dev/vitals/) | [LCP](https://web.dev/lcp/) | [CLS](https://web.dev/cls/) | [INP](https://web.dev/inp/) | [FCP](https://web.dev/fcp/) | [TTFB](https://web.dev/ttfb/)
```

**등급 판정:**
- Median 기준으로 기본 등급 판정
- P90이 다음 등급 임계값을 넘으면 추가 경고 (예: "Median Good이나 P90 Needs Improvement 진입")
- StdDev가 Avg의 20%를 초과하면 "측정 편차 큼" 경고 추가

---

## Step 8. HTML 보고서 생성 및 열기

이 스킬에 번들된 `scripts/generate_report.py`를 사용하여 HTML 보고서를 생성하고 브라우저에서 연다.

```bash
python3 <이 스킬의 scripts/generate_report.py 경로> "<RESULT_FILE 경로>" "<TARGET_URL>" <RUNS> "<DEVICE_NAME>" "<THROTTLE_NAME>" "<THROTTLE_DESC>"
```

스크립트가 자동으로 `/tmp/lighthouse_report_YYYYMMDD_HHMMSS.html`을 생성하고 `open` 명령으로 브라우저를 연다.
