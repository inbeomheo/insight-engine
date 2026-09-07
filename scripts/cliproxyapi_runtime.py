"""CLIProxyAPI의 인증 설정, 실행, 상태 확인을 표준 라이브러리로 제공한다."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_AUTH_DIR = "/data/cliproxyapi/auth"
DEFAULT_BINARY = "/usr/local/bin/CLIProxyAPI"


def isolated_environment() -> dict[str, str]:
    """다른 게이트웨이의 관리·원격 인증 저장소 설정을 상속하지 않는다."""
    return {
        name: value for name, value in os.environ.items()
        if name.upper() not in {"MANAGEMENT_PASSWORD", "HOME_JWT", "DEPLOY"}
        and not name.upper().startswith(("PGSTORE_", "GITSTORE_", "OBJECTSTORE_"))
    }


def _api_key() -> str:
    key = os.environ.get("CLIPROXYAPI_API_KEY", "").strip()
    if not key or key.lower() in {"dummy", "changeme", "your-api-key", "your-api-key-1"}:
        raise ValueError("CLIPROXYAPI_API_KEY에 새 서버 인증 키를 설정하세요.")
    if any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ValueError("CLIPROXYAPI_API_KEY는 공백 없는 ASCII 문자열이어야 합니다.")
    return key


def create_config() -> Path:
    """새 전용 임시 디렉터리만 사용하므로 기존 설정이나 인증 파일을 덮어쓰지 않는다."""
    key = _api_key()
    auth_dir = Path(os.getenv("CLIPROXYAPI_AUTH_DIR", DEFAULT_AUTH_DIR))
    if not auth_dir.is_absolute():
        raise ValueError("CLIPROXYAPI_AUTH_DIR는 절대 경로여야 합니다.")
    config = {
        "host": os.getenv("CLIPROXYAPI_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "port": 8317,
        "auth-dir": str(auth_dir),
        "api-keys": [key],
        "remote-management": {
            "allow-remote": False,
            "secret-key": "",
            "disable-control-panel": True,
            "disable-auto-update-panel": True,
        },
        "debug": False,
        "logging-to-file": False,
        "request-log": False,
        "usage-statistics-enabled": False,
        "pprof": {"enable": False},
        "plugins": {"enabled": False},
        "ws-auth": True,
    }
    directory = Path(tempfile.mkdtemp(prefix="cliproxyapi-"))
    path = directory / "config.yaml"
    # JSON은 YAML의 부분집합이다. 키에 따옴표가 있어도 안전하게 인코딩된다.
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(config, handle)
    return path


def healthcheck() -> None:
    """등록 모델이 없어도 서버 인증이 동작하는지 확인한다."""
    request = Request(
        "http://127.0.0.1:8317/v1/models",
        headers={"Authorization": f"Bearer {_api_key()}"},
    )
    with urlopen(request, timeout=3) as response:
        payload = json.load(response)
        if response.status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("CLIProxyAPI 모델 목록 응답을 확인할 수 없습니다.")
    try:
        with urlopen(request.full_url, timeout=3):
            pass
    except HTTPError as exc:
        if exc.code != 401:
            raise ValueError("CLIProxyAPI가 인증 없는 요청을 차단하지 않았습니다.") from None
    else:
        raise ValueError("CLIProxyAPI가 인증 없는 요청을 차단하지 않았습니다.")
    for path in ("/v0/management/config", "/management.html"):
        try:
            with urlopen("http://127.0.0.1:8317" + path, timeout=3):
                pass
        except HTTPError as exc:
            if exc.code == 404:
                continue
        raise ValueError("CLIProxyAPI 관리 기능이 비활성화되어 있지 않습니다.")


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    mode = arguments[0] if arguments else "serve"
    if len(arguments) > 1 or mode not in {"serve", "login", "healthcheck"}:
        raise ValueError("사용법: runtime.py [serve|login|healthcheck]")
    if mode == "healthcheck":
        healthcheck()
        return 0
    binary = os.getenv("CLIPROXYAPI_BINARY", DEFAULT_BINARY)
    if not Path(binary).is_absolute():
        raise ValueError("CLIPROXYAPI_BINARY는 절대 경로여야 합니다.")
    config_path = create_config()
    command = [binary, "-config", str(config_path)]
    if mode == "login":
        command.extend(["-codex-login", "-no-browser"])
    # 공식 바이너리가 현재 디렉터리의 .env를 자동으로 읽으므로 새 임시 경로에서 시작한다.
    os.chdir(config_path.parent)
    os.execve(binary, command, isolated_environment())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        # HTTP 응답/프로세스 인자/환경변수는 출력하지 않는다.
        print(f"CLIProxyAPI 실행 실패 ({type(exc).__name__}). 인증 키와 실행 설정을 확인하세요.", file=sys.stderr)
        raise SystemExit(1) from None
