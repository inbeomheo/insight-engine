#!/bin/bash
# autoresearch 자율 루프 — Claude Code CLI로 반복 실행
# 사용법: bash autoresearch/run-loop.sh [라운드수]
# 예시:   bash autoresearch/run-loop.sh 50

set -e
cd "$(dirname "$0")/.."

MAX_ROUNDS=${1:-100}
PROGRESS="autoresearch/feature-loop/progress.tsv"
CURRENT=$(tail -1 "$PROGRESS" | cut -f1)
START=$((CURRENT + 1))
END=$((START + MAX_ROUNDS - 1))

echo "=== Autoresearch Loop: R${START} ~ R${END} ==="
echo "프로젝트: $(pwd)"
echo "베이스라인: $(cat autoresearch/feature-loop/baseline.txt)"
echo ""

for round in $(seq $START $END); do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔄 Round $round 시작 ($(date '+%H:%M:%S'))"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  claude -p "$(cat <<PROMPT
autoresearch/feature-loop/program.md를 읽고 Round ${round}을 실행해.

현재 progress.tsv를 읽어서 이전 라운드와 중복되지 않는 기능을 발굴해.
절차: DISCOVER → PLAN → IMPLEMENT → TEST → JUDGE → RECORD

JUDGE 기준:
- python -m pytest tests/ -q
- passed 수가 $(cat autoresearch/feature-loop/baseline.txt) 이상이면 KEEP

KEEP이면:
- git add + git commit -m "feat: [R${round}] 기능명"
- progress.tsv에 결과 추가

REVERT이면:
- git checkout .
- 신규 파일 삭제
- progress.tsv에 revert 기록

제약: 외부 패키지 추가 금지, 3파일 이내, from __future__는 최상단.
PROMPT
  )" 2>&1 | tail -5

  echo ""
  echo "✅ Round $round 완료 ($(date '+%H:%M:%S'))"
  echo ""

  # 쿨다운 (API rate limit 방지)
  sleep 10
done

echo ""
echo "=== 루프 완료: R${START} ~ R${END} ==="
echo "최종 progress.tsv:"
cat "$PROGRESS"
