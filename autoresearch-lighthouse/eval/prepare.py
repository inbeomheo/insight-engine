#!/usr/bin/env python3
"""
prepare.py — Frozen Metric 측정 인프라 (절대 수정 금지 영역)
=============================================================
에이전트가 수정하면 안 되는 고정 평가 코드.

측정 파이프라인:
  1. npm run build (frontend/)
  2. first-load JS 측정 (build-manifest.json rootMainFiles+polyfillFiles)
  3. next start 백그라운드 기동 (포트 3100)
  4. lighthouse (mobile 기본, performance,seo) N회 → median
  5. 복합 점수 = performance*0.4 + seo*0.4 + bundle_score*0.2
  6. 표준 출력: "composite_score: <값>"

외부 의존성: lighthouse(devDep), 시스템 Chrome.
방향: higher_is_better (100점 만점).
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# 경로: eval/prepare.py → autoresearch-lighthouse/ → insight-engine/
AR_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = AR_ROOT.parent
FRONTEND = PROJECT_ROOT / "frontend"

PORT = int(os.environ.get("LH_PORT", "3100"))
URL = f"http://localhost:{PORT}/"
RUNS = int(os.environ.get("LH_RUNS", "3"))
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "300"))   # 빌드는 넉넉히 5분
SERVER_READY_TIMEOUT = int(os.environ.get("SERVER_READY_TIMEOUT", "90"))
LH_TIMEOUT = int(os.environ.get("LH_TIMEOUT", "180"))          # lighthouse 1회당 3분
# Chrome 경로 (chrome-launcher 가 CHROME_PATH 환경변수 사용). x86 우선, env 오버라이드 가능.
CHROME_PATH = os.environ.get(
    "CHROME_PATH",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
# lighthouse CLI (node 직접 실행으로 Windows quoting 문제 회피)
LH_CLI = str(FRONTEND / "node_modules" / "lighthouse" / "cli" / "index.js")


# ---------- first-load JS ----------
def measure_first_load_kb():
    """build-manifest.json 의 rootMainFiles + polyfillFiles 합산 (KB).
    = 모든 페이지 공통 first-load JS (Turbopack app router).
    dynamic import 로 개선 가능한 진짜 '초기 로드' 번들."""
    mf = FRONTEND / ".next" / "build-manifest.json"
    if not mf.exists():
        return None
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return None
    files = list(m.get("rootMainFiles", [])) + list(m.get("polyfillFiles", []))
    total = 0
    found = False
    for rel in files:
        p = FRONTEND / ".next" / rel
        if p.exists():
            total += p.stat().st_size
            found = True
    return (total / 1024.0) if found else None


def bundle_score(kb):
    """first-load JS KB → 점수. 100KB=100점, 700KB=0점 선형, 클램프 [0,100].
    모바일 first-load 권장 <130KB 기준. 베이스라인 ~510KB → 약 32점 시작."""
    if kb is None:
        return 0.0
    return max(0.0, min(100.0, 100.0 - (kb - 100.0) / 6.0))


# ---------- 프로세스/포트 관리 ----------
def _run(cmd, timeout=None, cwd=None):
    # Windows(cp949) 기본 인코딩 회피 — npm/next/lighthouse UTF-8 출력 안전 디코딩
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd,
    )


def cleanup_port(port):
    """해당 포트를 LISTEN 중인 프로세스를 트리 킬 (Windows). 루프 포트 충돌 방지."""
    try:
        r = subprocess.run(
            f'netstat -ano | findstr ":{port}"',
            shell=True, capture_output=True, text=True,
        )
        pids = set()
        for line in r.stdout.splitlines():
            parts = line.split()
            # LISTENING 라인만: "... TCP 0.0.0.0:3100 ... LISTENING <PID>"
            if len(parts) >= 5 and "LISTENING" in line:
                pids.add(parts[-1])
        for pid in pids:
            subprocess.run(
                f"taskkill /F /T /PID {pid}",
                shell=True, capture_output=True, text=True,
            )
    except Exception:
        pass


def wait_ready(url, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            time.sleep(1.0)
    return False


def kill_tree(proc):
    """Popen한 서버 프로세스 트리 종료."""
    if proc is None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
    except Exception:
        pass
    cleanup_port(PORT)  # 확정 정리


# ---------- lighthouse ----------
def run_lighthouse_once(run_idx, user_data_dir):
    """lighthouse 1회 실행 → (perf_score, seo_score) 또는 None. 점수는 0~100.
    node 직접 실행 + 인자 리스트(shell=False)로 Windows cmd quoting 문제 회피.
    preset 미지정 = mobile (기본). 모바일 성능이 진짜 개선 변수."""
    out_json = AR_ROOT / f".lh_run_{run_idx}.json"
    try:
        out_json.unlink(missing_ok=True)
    except Exception:
        pass

    chrome_flags = (
        f"--headless=new --user-data-dir={user_data_dir} "
        f"--no-first-run --no-default-browser-check --disable-gpu"
    )
    args = [
        "node", LH_CLI, URL,
        "--only-categories=performance,seo",
        "--output=json",
        f"--output-path={out_json}",
        "--quiet",
        f"--chrome-flags={chrome_flags}",
    ]
    env = dict(os.environ)
    env["CHROME_PATH"] = CHROME_PATH
    try:
        r = subprocess.run(
            args, shell=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=LH_TIMEOUT, cwd=str(FRONTEND), env=env,
        )
    except Exception as e:
        sys.stderr.write(f"[lh exec error] {e}\n")
        return None
    if not out_json.exists():
        sys.stderr.write(f"[lh no json] rc={r.returncode}\n")
        sys.stderr.write(f"  stdout: {r.stdout[-800:]}\n")
        sys.stderr.write(f"  stderr: {r.stderr[-800:]}\n")
        return None
    try:
        lhr = json.loads(out_json.read_text(encoding="utf-8"))
        cats = lhr["categories"]
        perf = cats["performance"]["score"]
        seo = cats["seo"]["score"]
        if perf is None or seo is None:
            return None
        return perf * 100.0, seo * 100.0
    except Exception as e:
        sys.stderr.write(f"[lh parse error] {e}\n")
        return None
    finally:
        try:
            out_json.unlink(missing_ok=True)
        except Exception:
            pass


# ---------- 메인 ----------
def main():
    # 0. 시작 전 포트 정리 (이전 실험 잔여 서버)
    cleanup_port(PORT)

    # 1. 빌드
    b = _run("npm run build", timeout=BUILD_TIMEOUT, cwd=str(FRONTEND))
    if b.returncode != 0:
        sys.stderr.write("ERROR: build failed\n")
        sys.stderr.write((b.stdout + b.stderr)[-2000:] + "\n")
        sys.exit(1)

    # 2. first-load JS 측정
    kb = measure_first_load_kb()
    bscore = bundle_score(kb)

    # 3. 서버 기동
    proc = subprocess.Popen(
        f"npx next start -p {PORT}",
        shell=True, cwd=str(FRONTEND),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_ready(URL, timeout=SERVER_READY_TIMEOUT):
            sys.stderr.write("ERROR: next start 서버 기동 실패/타임아웃\n")
            sys.exit(1)

        # 4. lighthouse N회 (mobile)
        perfs, seos = [], []
        with tempfile.TemporaryDirectory(prefix="lh_profile_") as udd:
            for i in range(RUNS):
                res = run_lighthouse_once(i, udd)
                if res is not None:
                    perfs.append(res[0])
                    seos.append(res[1])

        if not perfs:
            sys.stderr.write("ERROR: lighthouse 점수 0건 수집 실패\n")
            sys.exit(1)

        perf = statistics.median(perfs)
        seo = statistics.median(seos)
        composite = perf * 0.4 + seo * 0.4 + bscore * 0.2

        # 5. 표준 출력 (benchmark.py 가 composite_score 파싱)
        print(f"composite_score: {composite:.2f}")
        print(f"performance_score: {perf:.2f}")
        print(f"seo_score: {seo:.2f}")
        print(f"first_load_kb: {kb:.1f}" if kb is not None else "first_load_kb: N/A")
        print(f"bundle_score: {bscore:.2f}")
        print(f"runs: {len(perfs)}")
        print(f"perf_runs: {perfs}")
        print(f"seo_runs: {seos}")
    finally:
        kill_tree(proc)


if __name__ == "__main__":
    main()
