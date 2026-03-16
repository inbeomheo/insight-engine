# Auto Feature Loop Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** meta-prompt-generator로 생성한 루프 제어 프롬프트를 사용해, 코드베이스 분석 → 기능 발굴 → 구현 → 검증 → keep/revert를 10라운드 자율 반복한다.

**Architecture:** autoresearch 3파일 구조(program.md, eval.sh, progress.tsv)를 세팅한 뒤, meta-prompt가 매 라운드 DISCOVER → PLAN → IMPLEMENT → TEST → JUDGE 5단계를 자율 실행. Frozen Metric(tsc + next build + pytest)으로 keep/revert 판정.

**Tech Stack:** Flask (Python), Next.js 16 (TypeScript), pytest, Bash eval script

---

## Chunk 1: 인프라 세팅

### Task 1: Frozen Metric 평가 스크립트 생성

**Files:**
- Create: `autoresearch/feature-loop/eval.sh`

- [ ] **Step 1: eval.sh 작성**

```bash
#!/bin/bash
# Frozen Metric — 4개 체크 모두 통과해야 keep
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0

echo "=== [1/4] TypeScript 타입 체크 ==="
cd "$PROJECT_ROOT/frontend"
if npx tsc --noEmit 2>&1; then
  echo "PASS: tsc"
  ((PASS++))
else
  echo "FAIL: tsc"
  ((FAIL++))
fi

echo "=== [2/4] Next.js 빌드 ==="
if npx next build 2>&1; then
  echo "PASS: next build"
  ((PASS++))
else
  echo "FAIL: next build"
  ((FAIL++))
fi

echo "=== [3/4] 백엔드 pytest ==="
cd "$PROJECT_ROOT"
PYTEST_OUT=$(python -m pytest tests/ -x -q 2>&1) || true
echo "$PYTEST_OUT"
# "N passed" 에서 N 추출
PASSED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= passed)' | tail -1)
BASELINE=$(cat autoresearch/feature-loop/baseline.txt 2>/dev/null || echo "0")
if [ "${PASSED:-0}" -ge "$BASELINE" ]; then
  echo "PASS: pytest ($PASSED >= $BASELINE)"
  ((PASS++))
else
  echo "FAIL: pytest ($PASSED < $BASELINE)"
  ((FAIL++))
fi

echo "=== [4/4] 신규 테스트 ==="
if [ -n "$NEW_TEST_FILE" ] && [ -f "$NEW_TEST_FILE" ]; then
  if python -m pytest "$NEW_TEST_FILE" -v 2>&1; then
    echo "PASS: new test"
    ((PASS++))
  else
    echo "FAIL: new test"
    ((FAIL++))
  fi
else
  echo "SKIP: no new test file"
  ((PASS++))
fi

echo ""
echo "=== RESULT: $PASS pass / $FAIL fail ==="
if [ "$FAIL" -eq 0 ]; then
  echo "VERDICT: KEEP"
  exit 0
else
  echo "VERDICT: REVERT"
  exit 1
fi
```

- [ ] **Step 2: 실행 권한 부여**

Run: `chmod +x autoresearch/feature-loop/eval.sh`

---

### Task 2: 베이스라인 측정

**Files:**
- Create: `autoresearch/feature-loop/baseline.txt`
- Create: `autoresearch/feature-loop/progress.tsv`

- [ ] **Step 1: 현재 pytest 통과 수 측정**

Run: `python -m pytest tests/ -x -q 2>&1 | grep -oP '\d+(?= passed)' | tail -1 > autoresearch/feature-loop/baseline.txt`

- [ ] **Step 2: progress.tsv 헤더 생성**

```
round	feature	status	passed_tests	files_changed	commit
```

- [ ] **Step 3: tsc + next build 베이스라인 확인**

Run: `cd frontend && npx tsc --noEmit && npx next build`
Expected: 둘 다 exit 0

---

### Task 3: Meta-Prompt 생성 (program.md)

**Files:**
- Create: `autoresearch/feature-loop/program.md`

- [ ] **Step 1: /meta-prompt-generator 스킬로 루프 제어 프롬프트 생성**

입력 요약:
- 역할: 코드베이스 분석 → 기능 1개 발굴 → 구현 → 테스트 작성 → Frozen Metric 검증
- 컨텍스트: Insight Engine (Flask + Next.js), 250+ 서비스, 20+ 라우트
- 발굴 소스: TODO/FIXME, 미연결 서비스, UX 개선, 성능, 에러 핸들링
- 제약: 기존 테스트 깨뜨리지 않기, 외부 패키지 추가 금지, 라운드당 3파일 이내
- 판정: eval.sh 실행 → exit 0이면 keep + commit, exit 1이면 revert

- [ ] **Step 2: program.md를 autoresearch/feature-loop/에 저장**

---

## Chunk 2: 루프 실행 (10라운드)

### Task 4: 라운드 1-10 자율 실행

각 라운드의 실행 흐름:

- [ ] **Step 1: DISCOVER** — 코드베이스 분석으로 기능 후보 1개 선정
- [ ] **Step 2: PLAN** — 수정/생성할 파일 목록 + 테스트 계획
- [ ] **Step 3: IMPLEMENT** — 코드 작성 (백엔드 + 프론트엔드)
- [ ] **Step 4: TEST** — 단위 테스트 작성
- [ ] **Step 5: JUDGE** — eval.sh 실행 → keep/revert
- [ ] **Step 6: RECORD** — progress.tsv에 결과 기록

반복 10회. 각 라운드 성공 시:
```bash
git add -A && git commit -m "feat: [R{N}] 기능명"
```

실패 시:
```bash
git checkout .
```

---

## 성공 기준

- 10라운드 완료
- keep 비율 70% 이상 (7/10)
- 기존 테스트 전체 통과 유지
- progress.tsv에 전 라운드 기록
