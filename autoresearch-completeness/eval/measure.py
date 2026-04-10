#!/usr/bin/env python3
"""
Frozen Metric v2 — 완성도 복합 점수 측정기
절대 수정 금지 (autoresearch Frozen Metric 원칙)

복합 점수 = 테스트커버리지(35) + Python lint(25) + 프론트엔드lint(20) + 테스트통과(20)
"""
import subprocess
import sys
import re
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def run_cmd(cmd, cwd=None, timeout=300):
    """명령 실행 후 (returncode, stdout, stderr) 반환"""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=cwd or PROJECT_ROOT, timeout=timeout,
            encoding='utf-8', errors='replace'
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def measure_pytest_coverage():
    """영역 1: pytest 라인 커버리지 + 통과율"""
    cov_json = PROJECT_ROOT / "cov_report.json"

    rc, out, err = run_cmd([
        sys.executable, "-m", "pytest", "tests/", "--tb=no", "-q",
        "-p", "no:cacheprovider",
        f"--cov=services", f"--cov=routes",
        f"--cov-report=json:{cov_json}",
    ], timeout=600)

    combined = out + err

    # 통과율 파싱
    passed = failed = errors = 0
    m = re.search(r'(\d+)\s+passed', combined)
    if m:
        passed = int(m.group(1))
    m = re.search(r'(\d+)\s+failed', combined)
    if m:
        failed = int(m.group(1))
    m = re.search(r'(\d+)\s+error', combined)
    if m:
        errors = int(m.group(1))

    total = passed + failed + errors
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 커버리지 파싱
    coverage_pct = 0.0
    try:
        with open(cov_json, encoding='utf-8') as f:
            cov_data = json.load(f)
        coverage_pct = cov_data['totals']['percent_covered']
    except Exception:
        pass

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": total,
        "pass_rate": round(pass_rate, 2),
        "coverage_pct": round(coverage_pct, 1),
    }


def measure_ruff_lint():
    """영역 2: Python lint (미사용 import/변수)"""
    rc, out, err = run_cmd([
        "ruff", "check", "services/", "routes/",
        "--select=F401,F811,F841",
        "--statistics"
    ], timeout=30)

    combined = out + err
    # "Found 59 errors" 패턴 또는 statistics 행의 숫자 합산
    m = re.search(r'Found\s+(\d+)\s+error', combined)
    if m:
        lint_count = int(m.group(1))
    else:
        # statistics 형식: "47\tF401\t..." 행의 첫 번째 숫자 합산
        lint_count = sum(int(n) for n in re.findall(r'^(\d+)\t', combined, re.MULTILINE))

    return {
        "ruff_errors": lint_count,
        "ruff_detail": combined[-300:]
    }


def measure_eslint():
    """영역 3: 프론트엔드 ESLint errors + warnings"""
    frontend_dir = PROJECT_ROOT / "frontend"

    rc, out, err = run_cmd(
        ["npx.cmd", "eslint", ".", "--format", "json"],
        cwd=frontend_dir, timeout=120
    )

    total_issues = 0
    eslint_errors = 0
    eslint_warnings = 0
    try:
        data = json.loads(out)
        for r in data:
            eslint_errors += r.get('errorCount', 0)
            eslint_warnings += r.get('warningCount', 0)
        total_issues = eslint_errors + eslint_warnings
    except Exception:
        # ESLint 실행 실패 시 stderr에서 에러 수 추정
        total_issues = len(re.findall(r'error|warning', err))

    return {
        "eslint_errors": eslint_errors,
        "eslint_warnings": eslint_warnings,
        "eslint_total": total_issues,
    }


def measure_typescript():
    """영역 보너스: TypeScript 에러"""
    frontend_dir = PROJECT_ROOT / "frontend"
    rc, out, err = run_cmd(
        ["npx.cmd", "tsc", "--noEmit"],
        cwd=frontend_dir, timeout=120
    )
    if rc == 0:
        return {"ts_errors": 0}
    error_count = len(re.findall(r'error TS\d+', out + err))
    return {"ts_errors": error_count}


def compute_composite(cov_result, ruff_result, eslint_result, ts_result):
    """복합 점수 계산 (100점 만점)

    영역 1: 테스트 커버리지 (35점) — coverage_pct 기반
        85%+ = 35점, 70% = 24.5점, 선형 스케일
    영역 2: Python lint (25점) — ruff 에러 수 기반
        0개 = 25점, 에러당 -0.5점
    영역 3: 프론트엔드 lint (20점) — ESLint 이슈 수 기반
        0개 = 20점, 이슈당 -0.3점
    영역 4: 테스트 통과율 (20점) — 100% = 20점
        + TS 에러 페널티 (-1점/에러, 최대 -5)
    """

    # 영역 1: 테스트 커버리지 (35점)
    # 85%+ = 35점, 0% = 0점, 선형
    cov = min(cov_result["coverage_pct"], 85)
    score_coverage = round((cov / 85) * 35, 2)

    # 영역 2: Python lint (25점)
    ruff_penalty = ruff_result["ruff_errors"] * 0.5
    score_lint_py = round(max(0, 25 - ruff_penalty), 2)

    # 영역 3: 프론트엔드 lint (20점)
    eslint_penalty = eslint_result["eslint_total"] * 0.3
    score_lint_fe = round(max(0, 20 - eslint_penalty), 2)

    # 영역 4: 테스트 통과율 + TS (20점)
    total_tests = cov_result["passed"] + cov_result["failed"] + cov_result["errors"]
    if total_tests > 0:
        pass_score = (cov_result["passed"] / total_tests) * 20
    else:
        pass_score = 0

    ts_penalty = min(ts_result["ts_errors"], 5)
    score_tests = round(max(0, pass_score - ts_penalty), 2)

    total = round(score_coverage + score_lint_py + score_lint_fe + score_tests, 2)

    return {
        "score_coverage": score_coverage,
        "score_lint_py": score_lint_py,
        "score_lint_fe": score_lint_fe,
        "score_tests": score_tests,
        "total": total,
    }


def main():
    start = time.time()

    print("=== Frozen Metric v2: 완성도 복합 점수 측정 ===\n")

    print("[1/4] pytest + 커버리지 측정 중...")
    cov_r = measure_pytest_coverage()
    print(f"  passed={cov_r['passed']} failed={cov_r['failed']} errors={cov_r['errors']}")
    print(f"  coverage={cov_r['coverage_pct']}%")

    print("[2/4] Python lint (ruff) 측정 중...")
    ruff_r = measure_ruff_lint()
    print(f"  ruff_errors={ruff_r['ruff_errors']}")

    print("[3/4] 프론트엔드 lint (ESLint) 측정 중...")
    eslint_r = measure_eslint()
    print(f"  eslint_errors={eslint_r['eslint_errors']} warnings={eslint_r['eslint_warnings']} total={eslint_r['eslint_total']}")

    print("[4/4] TypeScript 에러 측정 중...")
    ts_r = measure_typescript()
    print(f"  ts_errors={ts_r['ts_errors']}")

    scores = compute_composite(cov_r, ruff_r, eslint_r, ts_r)
    elapsed = round(time.time() - start, 1)

    print(f"\n=== 복합 점수: {scores['total']} / 100 ===")
    print(f"  테스트커버리지: {scores['score_coverage']}/35  (coverage={cov_r['coverage_pct']}%)")
    print(f"  Python lint:    {scores['score_lint_py']}/25  (ruff={ruff_r['ruff_errors']}개)")
    print(f"  프론트엔드lint: {scores['score_lint_fe']}/20  (eslint={eslint_r['eslint_total']}개)")
    print(f"  테스트통과:     {scores['score_tests']}/20  (pass_rate={cov_r['pass_rate']}%)")
    print(f"  측정 소요:      {elapsed}s")

    result = {
        **cov_r, **ruff_r, **eslint_r, **ts_r, **scores,
        "elapsed": elapsed,
    }

    print(f"\n__METRIC_JSON__={json.dumps(result)}")
    return scores["total"]


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 99 else 1)
