"""실제 CLIProxyAPI와 로컬 가짜 공급자 사이의 OpenAI 통신 계약.

실행: CLIPROXYAPI_TEST_BINARY=/absolute/path/cli-proxy-api \
    node scripts/run_python.cjs -m pytest tests/test_cliproxyapi_protocol.py -v
실제 계정과 외부 공급자는 사용하지 않으며 생성한 임시 자료는 보존한다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

import pytest


USAGE = {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}
MODEL = "protocol-local-model"
TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_note",
        "description": "로컬 노트 조회",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
}
TOOL_CALL = {
    "id": "call_local_1", "type": "function",
    "function": {"name": "lookup_note", "arguments": '{"query":"노트"}'},
}


@pytest.fixture(scope="module")
def protocol_gateway():
    binary = os.environ.get("CLIPROXYAPI_TEST_BINARY")
    if not binary:
        pytest.skip("CLIPROXYAPI_TEST_BINARY 설정 시 실제 바이너리 통합 검증 실행")
    executable = Path(binary)
    assert executable.is_absolute() and executable.is_file(), "바이너리 절대 경로 필요"
    gateway_key, upstream_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    recorded = []

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            recorded.append((self.path, self.headers.get("Authorization"), payload))
            if self.path != "/v1/chat/completions" or self.headers.get("Authorization") != f"Bearer {upstream_key}":
                self.send_error(400)
                return
            base = {"id": "chatcmpl-local", "created": 1, "model": MODEL}
            self.send_response(200)
            if payload.get("stream"):
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunks = [
                    {"choices": [{"index": 0, "delta": {"role": "assistant", "content": "로컬 "}, "finish_reason": None}]},
                    {"choices": [{"index": 0, "delta": {"content": "응답"}, "finish_reason": None}]},
                    {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                    {"choices": [], "usage": USAGE},
                ]
                for chunk in chunks:
                    data = {**base, "object": "chat.completion.chunk", **chunk}
                    self.wfile.write(("data: " + json.dumps(data) + "\n\n").encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                return
            message = {"role": "assistant", "content": "로컬 응답"}
            finish = "stop"
            if payload.get("tools"):
                message = {"role": "assistant", "content": None, "tool_calls": [TOOL_CALL]}
                finish = "tool_calls"
            body = json.dumps({
                **base, "object": "chat.completion", "usage": USAGE,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            }).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    work = Path(tempfile.mkdtemp(prefix="ie-cliproxy-protocol-"))
    work.chmod(0o700)
    auth = work / "auth"
    auth.mkdir(mode=0o700)
    config = {
        "host": "127.0.0.1", "port": port, "auth-dir": str(auth),
        "api-keys": [gateway_key], "request-retry": 0,
        "logging-to-file": False, "error-logs-max-files": 0,
        "remote-management": {
            "allow-remote": False, "secret-key": "",
            "disable-control-panel": True, "disable-auto-update-panel": True,
        },
        "plugins": {"enabled": False},
        "openai-compatibility": [{
            "name": "local-protocol-test",
            "base-url": f"http://127.0.0.1:{upstream.server_port}/v1",
            "api-key-entries": [{"api-key": upstream_key, "proxy-url": "direct"}],
            "models": [{"name": MODEL, "alias": MODEL}],
        }],
    }
    config_path = work / "config.yaml"
    with config_path.open("x", encoding="utf-8") as output:
        config_path.chmod(0o600)
        json.dump(config, output)
    opener = build_opener(ProxyHandler({}))
    base_url = f"http://127.0.0.1:{port}/v1"
    process = None
    try:
        # 최소 환경과 -local-model로 기존 인증·프록시·원격 모델 목록을 배제한다.
        process = subprocess.Popen(
            [str(executable), "-config", str(config_path), "-local-model"],
            cwd=work, env={"PATH": os.environ.get("PATH", "")},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            assert process.poll() is None, "CLIProxyAPI가 준비 전에 종료됨"
            try:
                request = Request(base_url + "/models", headers={"Authorization": f"Bearer {gateway_key}"})
                with opener.open(request, timeout=1) as response:
                    if MODEL in {item["id"] for item in json.load(response)["data"]}:
                        break
            except (URLError, TimeoutError):
                pass
            time.sleep(0.05)
        else:
            pytest.fail("15초 내 로컬 테스트 모델 준비 실패")

        def call(**extra):
            recorded.clear()
            payload = {"model": MODEL, "messages": [{"role": "user", "content": "노트"}], **extra}
            request = Request(
                base_url + "/chat/completions", data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {gateway_key}", "Content-Type": "application/json"},
            )
            with opener.open(request, timeout=5) as response:
                return response.headers.get_content_type(), response.read(), payload

        yield call, recorded, upstream_key
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        upstream.shutdown()
        upstream.server_close()
        thread.join(timeout=2)


def test_real_gateway_completion_and_usage(protocol_gateway):
    call, recorded, upstream_key = protocol_gateway
    content_type, raw, sent = call(temperature=0.5, max_tokens=32)
    result = json.loads(raw)
    assert content_type == "application/json"
    assert result["choices"][0]["message"]["content"] == "로컬 응답"
    assert result["choices"][0]["finish_reason"] == "stop"
    assert result["usage"] == USAGE
    assert len(recorded) == 1
    path, authorization, received = recorded[0]
    assert path == "/v1/chat/completions"
    assert authorization == f"Bearer {upstream_key}"
    for field in ("model", "messages", "temperature", "max_tokens"):
        assert received[field] == sent[field]


def test_real_gateway_tool_call(protocol_gateway):
    call, recorded, _ = protocol_gateway
    _, raw, _ = call(tools=[TOOL], tool_choice="auto")
    choice = json.loads(raw)["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    assert choice["message"]["tool_calls"] == [TOOL_CALL]
    assert recorded[0][2]["tools"] == [TOOL]
    assert recorded[0][2]["tool_choice"] == "auto"


def test_real_gateway_sse_text_finish_and_final_usage(protocol_gateway):
    call, recorded, _ = protocol_gateway
    content_type, raw, _ = call(stream=True, stream_options={"include_usage": True})
    assert content_type == "text/event-stream"
    events = [line[6:] for line in raw.decode().splitlines() if line.startswith("data: ")]
    assert events[-1] == "[DONE]"
    chunks = [json.loads(event) for event in events[:-1]]
    text = "".join(choice.get("delta", {}).get("content", "") for chunk in chunks for choice in chunk["choices"])
    assert text == "로컬 응답"
    assert any(choice.get("finish_reason") == "stop" for chunk in chunks for choice in chunk["choices"])
    assert chunks[-1]["choices"] == []
    assert chunks[-1]["usage"] == USAGE
    assert recorded[0][2]["stream"] is True
    assert recorded[0][2]["stream_options"]["include_usage"] is True
