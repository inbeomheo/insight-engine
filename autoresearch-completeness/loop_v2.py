#!/usr/bin/env python3
"""
Autoresearch 자율 루프 v2 — 100라운드 완성도 + 기능 고도화
Claude Code CLI를 호출하여 각 라운드마다:
1. 메트릭 측정
2. 가장 점수가 낮은 영역 선택
3. Claude 에이전트에게 개선 요청
4. 메트릭 재측정 → keep/revert
"""
import subprocess
import sys
import json
import time
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEASURE_SCRIPT = PROJECT_ROOT / "autoresearch-completeness" / "eval" / "measure.py"
RESULTS_FILE = PROJECT_ROOT / "autoresearch-completeness" / "inner_results.tsv"
SESSION_FILE = PROJECT_ROOT / "autoresearch-completeness" / "autoresearch.md"
MAX_ROUNDS = 100


def run(cmd, cwd=None, timeout=600):
    """명령 실행"""
    r = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=cwd or PROJECT_ROOT, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    return r.returncode, r.stdout, r.stderr


def measure():
    """Frozen Metric 측정, JSON 결과 반환"""
    rc, out, err = run([sys.executable, str(MEASURE_SCRIPT)], timeout=900)
    combined = out + err
    # __METRIC_JSON__= 라인 파싱
    for line in combined.split('\n'):
        if '__METRIC_JSON__=' in line:
            json_str = line.split('__METRIC_JSON__=')[1].strip()
            return json.loads(json_str)
    return None


def get_improvement_prompt(metrics):
    """메트릭 기반으로 개선 프롬프트 생성"""
    score = metrics['total']

    # 가장 점수가 낮은 영역 찾기
    areas = [
        ('테스트 커버리지', metrics['score_coverage'], 35, f"coverage={metrics['coverage_pct']}%"),
        ('Python lint', metrics['score_lint_py'], 25, f"ruff={metrics['ruff_errors']}개"),
        ('프론트엔드 lint', metrics['score_lint_fe'], 20, f"eslint={metrics['eslint_total']}개"),
        ('테스트 통과', metrics['score_tests'], 20, f"pass_rate={metrics['pass_rate']}%"),
    ]

    # 만점이 아닌 영역 중 개선 여지가 큰 순
    improvable = [(name, score, max_score, detail)
                  for name, score, max_score, detail in areas
                  if score < max_score]

    if not improvable:
        # 메트릭 100점이면 기능 고도화로 전환
        return _feature_enhancement_prompt(metrics)

    # 가장 큰 갭
    improvable.sort(key=lambda x: (x[2] - x[1]), reverse=True)
    target = improvable[0]

    prompts = {
        '테스트 커버리지': _coverage_prompt(metrics),
        'Python lint': _ruff_prompt(metrics),
        '프론트엔드 lint': _eslint_prompt(metrics),
        '테스트 통과': _test_pass_prompt(metrics),
    }

    return prompts.get(target[0], _feature_enhancement_prompt(metrics))


def _coverage_prompt(m):
    return f"""테스트 커버리지를 올려주세요. 현재 {m['coverage_pct']}%.

1. `python -c "import json; d=json.load(open('cov_report.json')); [(print(f'{{i[\"summary\"][\"missing_lines\"]:4d}} ({{i[\"summary\"][\"percent_covered\"]:5.1f}}%) {{p}}')) for p,i in sorted(d['files'].items(), key=lambda x: x[1]['summary']['missing_lines'], reverse=True)[:10] if i['summary']['percent_covered']<50]"` 로 하위 파일 확인
2. 가장 미커버 줄이 많은 파일 1-2개 선택
3. tests/ 디렉토리에 테스트 파일 생성
4. `@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)` 필수
5. 외부 API 모두 mock, assertion에 500 포함
6. `python -m pytest [새 테스트 파일] -q --tb=short -p no:cacheprovider` 로 통과 확인
7. `python -m pytest tests/ --tb=no -q -p no:cacheprovider` 로 전체 회귀 없음 확인"""


def _ruff_prompt(m):
    return f"""ruff lint 에러 {m['ruff_errors']}개를 수정해주세요.

1. `ruff check services/ routes/ --select=F401,F811,F841` 로 에러 목록 확인
2. 자동 수정: `ruff check services/ routes/ --select=F401,F811,F841 --fix`
3. 남은 에러 수동 수정 (미사용 import 제거, 미사용 변수 제거/_ 접두사)
4. `python -m pytest tests/ --tb=no -q -p no:cacheprovider` 로 회귀 없음 확인"""


def _eslint_prompt(m):
    return f"""ESLint 이슈 {m['eslint_total']}개를 수정해주세요.

1. `cd frontend && npx eslint . --format json` 으로 이슈 목록 확인
2. 미사용 import/변수 제거
3. react-hooks 경고는 eslint-disable 또는 코드 수정
4. 전체 빌드 확인: `cd frontend && npx next build`"""


def _test_pass_prompt(m):
    return f"""실패하는 테스트 {m['failed']}개와 에러 {m['errors']}개를 수정해주세요.

1. `python -m pytest tests/ --tb=short -q -p no:cacheprovider` 로 실패 목록 확인
2. 각 실패 테스트 파일을 읽고 원인 파악
3. 테스트 또는 서비스 코드 수정
4. 전체 통과 확인"""


def _feature_enhancement_prompt(m):
    """기능 고도화 프롬프트 — 메트릭 100점 후 전환"""
    import random
    enhancements = [
        # 코드 품질
        "services/ 또는 routes/ 에서 가장 복잡한(줄 수 많은) 함수를 찾아 리팩토링하세요. 200줄 이상 함수를 작은 함수로 분해. 기존 테스트 통과 유지 필수.",
        "중복 코드를 찾아 공통 유틸로 추출하세요. `rg -c 'pattern'` 등으로 반복 패턴 검색. 테스트 통과 유지.",
        "에러 핸들링이 부족한 서비스 함수에 try/except와 의미있는 에러 메시지를 추가하세요. 새 테스트도 작성.",
        # 테스트 강화
        "엣지 케이스 테스트를 추가하세요: 빈 입력, 매우 긴 입력, 특수문자, 유니코드. 기존 테스트가 적은 서비스 선택.",
        "services/agents/ 에이전트 테스트를 보강하세요. orchestrator, research_agent 등의 에러 경로 테스트.",
        "services/mcp/ MCP 플러그인 테스트를 추가하세요. plugin_sdk.py (0% 커버리지) 우선.",
        # 성능/보안
        "N+1 쿼리 패턴이나 불필요한 반복 API 호출을 찾아 최적화하세요.",
        "SSRF, 인젝션 등 보안 취약점을 점검하고 방어 코드를 추가하세요. 테스트도 작성.",
        # 프론트엔드
        "프론트엔드 컴포넌트의 접근성(a11y)을 개선하세요. aria 속성, 키보드 네비게이션 등.",
        "프론트엔드 타입 안전성을 강화하세요. any 타입을 구체적 타입으로 교체.",
    ]
    task = random.choice(enhancements)
    return f"""기능 고도화 작업을 수행해주세요.

{task}

**반드시 지킬 것:**
- `python -m pytest tests/ --tb=no -q -p no:cacheprovider` 전체 통과 유지
- `ruff check services/ routes/ --select=F401,F811,F841` 0 에러 유지
- 기존 동작을 깨뜨리지 않을 것"""


def git_commit(round_num, score, msg):
    """변경사항 커밋"""
    run(["git", "add", "-A"])
    commit_msg = f"autoresearch R{round_num}: {score:.1f}점 — {msg}"
    run(["git", "commit", "-m", commit_msg, "--allow-empty"])


def git_revert():
    """변경사항 되돌리기"""
    run(["git", "checkout", "--", "."])
    run(["git", "clean", "-fd", "--exclude=autoresearch-completeness/"])


def log_result(round_num, before, after, action, kept):
    """결과를 TSV에 기록"""
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        if round_num == 1:
            f.write("round\tbefore\tafter\tdelta\taction\tkept\ttimestamp\n")
        f.write(f"{round_num}\t{before:.2f}\t{after:.2f}\t{after-before:.2f}\t{action}\t{kept}\t{datetime.now().isoformat()}\n")


def update_session(round_num, score, msg):
    """세션 파일 업데이트"""
    with open(SESSION_FILE, 'a', encoding='utf-8') as f:
        f.write(f"| {round_num} | {score:.2f} | {msg[:50]} | {'keep' if score > 0 else 'revert'} |\n")


def call_claude(prompt, timeout=600):
    """Claude Code CLI를 호출하여 코드 수정"""
    rc, out, err = run(
        ["claude", "--yes", "--model", "sonnet", "-p", prompt],
        timeout=timeout
    )
    return rc == 0, (out + err)[-500:]


def main():
    print(f"=== Autoresearch 자율 루프 v2 시작 (최대 {MAX_ROUNDS}라운드) ===\n")

    # 베이스라인 측정
    print("[0] 베이스라인 측정 중...")
    baseline = measure()
    if not baseline:
        print("ERROR: 베이스라인 측정 실패")
        return

    best_score = baseline['total']
    print(f"  베이스라인: {best_score:.2f}/100\n")

    for r in range(1, MAX_ROUNDS + 1):
        print(f"\n{'='*60}")
        print(f"[Round {r}/{MAX_ROUNDS}] 현재 최고: {best_score:.2f}/100")
        print(f"{'='*60}\n")

        # 1. 개선 방향 결정
        current = measure()
        if not current:
            print("  WARNING: 측정 실패, 다음 라운드로")
            continue

        prompt = get_improvement_prompt(current)
        action = prompt.split('\n')[0][:60]
        print(f"  방향: {action}")

        # 2. Claude 에이전트 호출
        print(f"  Claude 호출 중...")
        success, output = call_claude(prompt, timeout=900)
        print(f"  Claude 완료: {'성공' if success else '실패'}")

        # 3. 메트릭 재측정
        print(f"  메트릭 재측정 중...")
        after = measure()
        if not after:
            print("  WARNING: 재측정 실패, revert")
            git_revert()
            log_result(r, current['total'], current['total'], action, False)
            continue

        delta = after['total'] - current['total']
        print(f"  결과: {current['total']:.2f} → {after['total']:.2f} (Δ{delta:+.2f})")

        # 4. keep/revert 판정
        if after['total'] >= current['total'] and after['passed'] >= current['passed']:
            # 점수 유지/개선 + 테스트 회귀 없음 → keep
            print(f"  → KEEP (Δ{delta:+.2f})")
            git_commit(r, after['total'], action)
            best_score = max(best_score, after['total'])
            log_result(r, current['total'], after['total'], action, True)
            update_session(r, after['total'], action)
        else:
            # 악화 → revert
            print(f"  → REVERT (점수 하락 또는 테스트 회귀)")
            git_revert()
            log_result(r, current['total'], after['total'], action, False)
            update_session(r, current['total'], f"REVERT: {action}")

        # 5. 100점 달성 확인
        if best_score >= 100.0:
            print(f"\n🎯 100점 달성! 기능 고도화 모드로 전환합니다.")
            # 100점 이후에도 계속 루프 (기능 고도화)

    print(f"\n=== 루프 종료: {MAX_ROUNDS}라운드 완료 ===")
    print(f"최종 최고 점수: {best_score:.2f}/100")


if __name__ == "__main__":
    main()
