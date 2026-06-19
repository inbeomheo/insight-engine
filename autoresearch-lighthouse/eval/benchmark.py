#!/usr/bin/env python3
"""
벤치마크 래퍼 — prepare.py 를 실행하고 표준 출력에서 composite_score 를 추출.
이 파일은 Frozen Metric의 일부이므로 에이전트가 수정하면 안 된다.
"""
import re
import subprocess
import sys
import time

METRIC_NAME = "composite_score"
COMMAND = "python autoresearch-lighthouse/eval/prepare.py"
TIMEOUT = 1500  # 빌드(5분) + 서버 + lighthouse 3회(최대 9분) 여유


def run_benchmark():
    start = time.time()
    try:
        result = subprocess.run(
            COMMAND,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        elapsed = time.time() - start
        output = result.stdout + result.stderr

        match = re.search(rf"{METRIC_NAME}:\s*([\d.]+)", output)
        if match:
            value = float(match.group(1))
            print(f"{METRIC_NAME}: {value}")
            print(f"elapsed_seconds: {elapsed:.2f}")
            print(f"exit_code: {result.returncode}")
            return value
        else:
            sys.stderr.write(f"ERROR: '{METRIC_NAME}:' 패턴을 출력에서 찾을 수 없음\n")
            sys.stderr.write(output[-1500:] + "\n")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        sys.stderr.write(f"ERROR: 타임아웃 ({TIMEOUT}초 초과)\n")
        sys.exit(1)


if __name__ == "__main__":
    run_benchmark()
