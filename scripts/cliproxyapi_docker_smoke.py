"""모델 계정이나 외부 네트워크 없이 CLIProxyAPI 컨테이너 인증을 검증한다."""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import time


DEFAULT_IMAGE = "insight-engine-cliproxyapi:ci"


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=30, **kwargs)


def main() -> int:
    image = os.getenv("CLIPROXYAPI_SMOKE_IMAGE", DEFAULT_IMAGE)
    name = f"insight-cliproxyapi-ci-{secrets.token_hex(8)}"
    api_key = secrets.token_urlsafe(32)
    environment = dict(os.environ, CLIPROXYAPI_API_KEY=api_key)
    started = False
    try:
        # 값은 프로세스 환경으로만 전달한다. Docker 인자/예외 출력에 키가 들어가지 않는다.
        _run([
            "docker", "run", "--detach", "--name", name,
            "--network", "none", "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs", "/data/cliproxyapi/auth:rw,noexec,nosuid,uid=10001,gid=10001,size=8m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--env", "CLIPROXYAPI_API_KEY", image,
        ], check=True, env=environment)
        started = True
        help_result = _run([
            "docker", "exec", name, "/usr/local/bin/CLIProxyAPI", "-help",
        ], check=True)
        help_text = help_result.stdout + help_result.stderr
        if not all(flag in help_text for flag in ("-codex-login", "-no-browser", "-config")):
            raise RuntimeError("CLIProxyAPI 로그인 옵션을 확인할 수 없습니다.")
        _run([
            "docker", "exec", name, "python", "-c",
            "import os; assert os.geteuid() == 10001",
        ], check=True)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            result = _run([
                "docker", "exec", name, "python",
                "/opt/cliproxyapi/runtime.py", "healthcheck",
            ], check=False)
            if result.returncode == 0:
                print("CLIProxyAPI 검증 통과: 비루트 실행, 인증 요청 200, 무인증 요청 401, 로그인 옵션 확인.")
                return 0
            running = _run([
                "docker", "inspect", "--format={{.State.Running}}", name,
            ], check=False)
            if running.returncode or running.stdout.strip() != "true":
                raise RuntimeError("CLIProxyAPI가 상태 확인 전에 종료되었습니다.")
            time.sleep(2)
        raise RuntimeError("CLIProxyAPI 상태 확인 제한 시간을 초과했습니다.")
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"CLIProxyAPI 검증 실패 ({type(exc).__name__}).", file=sys.stderr)
        if started:
            logs = _run(["docker", "logs", name], check=False)
            print((logs.stdout + logs.stderr).replace(api_key, "[redacted]"), file=sys.stderr)
        return 1
    finally:
        if started:
            # 이 실행에서 새로 생성한 임시 컨테이너만 정리한다. 영구 볼륨은 만들지 않는다.
            _run(["docker", "rm", "--force", name], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
