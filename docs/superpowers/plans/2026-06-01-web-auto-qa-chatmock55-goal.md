# Web Auto QA with ChatMock 5.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insight Engine의 주요 웹 기능을 ChatMock 5.5 기반으로 브라우저 자동 QA하고, 실패한 기능은 수정 후 `QA_REPORT.md`에 증거를 남긴다.

**Architecture:** 백엔드 Flask(`app.py`)와 프론트 Next.js(`frontend`)를 로컬에서 동시에 실행한다. AI 호출은 실제 외부 과금형 SDK가 아니라 OpenAI 호환 ChatMock 프록시(`CHATMOCK_BASE_URL`)로 고정하고, Playwright가 사용자 시나리오를 브라우저에서 직접 실행한다. 실패는 재현 스크립트 → 원인 수정 → 동일 스크립트 재실행 순서로 처리한다.

**Tech Stack:** Python 3.13, Flask, LiteLLM, ChatMock OpenAI-compatible API, Next.js 16, React 19, Playwright, PowerShell.

---

## Safety / Secrets

- 노출된 GLM Coding Plan 키는 문서/커밋에 저장하지 않는다.
- 로컬에서만 PowerShell 환경변수로 주입한다.
- `.env`에는 실제 키 대신 `CHATMOCK_API_KEY=dummy`만 저장한다.
- GLM Coding Plan은 제공 문서상 지원 도구 제한이 있으므로, 앱 QA용 모델 경로는 `chatmock/gpt-5.5`로 통일한다.

## Files Map

- Modify: `config.py` — ChatMock 모델 목록에 `chatmock/gpt-5.5` 추가.
- Modify: `routes/blog_routes.py` — 기본 생성 모델을 `chatmock/gpt-5.5`로 전환.
- Modify: `.env` — ChatMock 로컬 프록시 설정 추가, Supabase placeholder는 로컬 모드로 취급.
- Create: `tests/e2e/autoqa/qa_matrix.json` — 자동 QA 대상 기능 목록.
- Create: `tests/e2e/autoqa/run_autoqa.py` — Playwright 브라우저 QA 러너.
- Create: `QA_REPORT.md` — 실행 결과, 스크린샷, 실패/수정 내역.

---

### Task 1: ChatMock 5.5 모델을 앱 기본값으로 고정

**Files:**
- Modify: `config.py`
- Modify: `routes/blog_routes.py`
- Modify: `.env`

- [ ] **Step 1: `config.py`에 ChatMock 5.5 추가**

`SUPPORTED_PROVIDERS['chatmock']['models']`를 아래처럼 만든다.

```python
'chatmock': {
    'name': 'ChatMock',
    'api_base': os.getenv('CHATMOCK_BASE_URL', 'http://127.0.0.1:8000/v1'),
    'models': [
        {'id': 'chatmock/gpt-5.5', 'name': 'GPT-5.5', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
        {'id': 'chatmock/gpt-5.4', 'name': 'GPT-5.4', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
    ]
},
```

- [ ] **Step 2: `routes/blog_routes.py` 기본 모델 변경**

```python
DEFAULT_MODEL = 'chatmock/gpt-5.5'
```

- [ ] **Step 3: `.env`에 ChatMock 설정 추가/수정**

```env
CHATMOCK_BASE_URL=http://127.0.0.1:8000/v1
CHATMOCK_API_KEY=dummy
DEFAULT_MODEL=chatmock/gpt-5.5
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

- [ ] **Step 4: 설정 검증**

Run:

```powershell
.\.venv\Scripts\python.exe - <<'PY'
from config import get_available_providers
p = get_available_providers()
assert 'chatmock' in p
assert p['chatmock']['models'][0]['id'] == 'chatmock/gpt-5.5'
print('chatmock provider ok')
PY
```

Expected:

```text
chatmock provider ok
```

---

### Task 2: ChatMock 서버 연결 확인

**Files:**
- No code change unless server is unreachable.

- [ ] **Step 1: ChatMock 설치 확인**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip show chatmock
```

Expected: package metadata 출력.

- [ ] **Step 2: ChatMock 실행 방법 확인**

Run:

```powershell
.\.venv\Scripts\python.exe -m chatmock --help
```

Expected: 실행 옵션 출력. 실패하면 아래를 실행해 엔트리포인트를 찾는다.

```powershell
.\.venv\Scripts\python.exe - <<'PY'
import chatmock, pkgutil
print(chatmock.__file__)
print([m.name for m in pkgutil.iter_modules(chatmock.__path__)])
PY
```

- [ ] **Step 3: ChatMock 서버 시작**

예시 명령은 도움말 결과에 맞춘다. 기본 포트는 8000이어야 한다.

```powershell
$env:CHATMOCK_BASE_URL='http://127.0.0.1:8000/v1'
# 도움말에서 확인된 실제 실행 명령 사용
```

- [ ] **Step 4: OpenAI 호환 엔드포인트 검증**

Run:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/v1/models' -TimeoutSec 5
```

Expected: 모델 목록 또는 200 응답.

---

### Task 3: 앱 서버 2개를 동시에 띄우기

**Files:**
- No source change.

- [ ] **Step 1: 백엔드 실행**

```powershell
$env:CHATMOCK_BASE_URL='http://127.0.0.1:8000/v1'
$env:CHATMOCK_API_KEY='dummy'
$env:SUPABASE_URL=''
$env:SUPABASE_ANON_KEY=''
.\.venv\Scripts\python.exe app.py
```

Expected:

```text
http://localhost:5001
```

- [ ] **Step 2: 프론트엔드 실행**

```powershell
cd frontend
npm run dev
```

Expected:

```text
http://localhost:3000
```

- [ ] **Step 3: 헬스 체크**

```powershell
Invoke-WebRequest http://localhost:5001/api/providers
Invoke-WebRequest http://localhost:3000
```

Expected: 둘 다 HTTP 200.

---

### Task 4: QA 매트릭스 작성

**Files:**
- Create: `tests/e2e/autoqa/qa_matrix.json`

- [ ] **Step 1: 디렉터리 생성**

```powershell
New-Item -ItemType Directory -Force tests/e2e/autoqa
```

- [ ] **Step 2: QA 매트릭스 파일 생성**

```json
[
  {"id":"home-load","name":"홈 로드","url":"http://localhost:3000","expect":"main UI visible"},
  {"id":"provider-chatmock","name":"ChatMock 5.5 공급자 노출","url":"http://localhost:3000","expect":"chatmock/gpt-5.5 selectable"},
  {"id":"direct-text-generate","name":"직접 텍스트 생성","input":"충분히 긴 한국어 테스트 텍스트입니다. 자동 QA가 생성 버튼을 누르고 결과 영역을 확인합니다.","expect":"generated result visible"},
  {"id":"youtube-url-validation","name":"YouTube URL 입력 검증","input":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","expect":"URL accepted or actionable error"},
  {"id":"style-selection","name":"스타일 선택","expect":"style controls usable"},
  {"id":"settings-open","name":"설정 열기","expect":"settings panel visible"},
  {"id":"history-panel","name":"히스토리 패널","expect":"history empty state or list visible"},
  {"id":"export-buttons","name":"내보내기 버튼","expect":"export actions visible after generation"}
]
```

---

### Task 5: Playwright 자동 QA 러너 작성

**Files:**
- Create: `tests/e2e/autoqa/run_autoqa.py`
- Create directory: `tests/e2e/autoqa/artifacts/`

- [ ] **Step 1: 러너 파일 생성**

```python
from __future__ import annotations

import json
import pathlib
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = pathlib.Path(__file__).resolve().parents[3]
ARTIFACTS = pathlib.Path(__file__).resolve().parent / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
REPORT = ROOT / "QA_REPORT.md"
BASE_URL = "http://localhost:3000"


def record(lines: list[str], ok: bool, case_id: str, message: str) -> None:
    mark = "PASS" if ok else "FAIL"
    lines.append(f"| {case_id} | {mark} | {message} |")


def safe_click(page, selector: str) -> bool:
    try:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            loc.click(timeout=3000)
            return True
    except Exception:
        return False
    return False


def main() -> int:
    lines = [
        "# QA Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Case | Result | Evidence |",
        "|---|---|---|",
    ]
    failures = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(ARTIFACTS / "home.png"), full_page=True)
            record(lines, True, "home-load", "home.png captured")
        except Exception as e:
            record(lines, False, "home-load", str(e))
            failures += 1
            browser.close()
            REPORT.write_text("\n".join(lines), encoding="utf-8")
            return failures

        content = page.content().lower()
        has_chatmock = "chatmock" in content or "gpt-5.5" in content
        record(lines, has_chatmock, "provider-chatmock", "chatmock/gpt-5.5 visible in DOM" if has_chatmock else "provider not visible")
        failures += 0 if has_chatmock else 1

        # 직접 텍스트 입력: 가능한 selector를 순차 시도
        text = "충분히 긴 한국어 테스트 텍스트입니다. 자동 QA가 생성 버튼을 누르고 결과 영역을 확인합니다. " * 3
        filled = False
        for selector in ["textarea", "#content", "#url-input", "input[type='text']"]:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible():
                    loc.fill(text, timeout=3000)
                    filled = True
                    break
            except Exception:
                pass
        clicked = False
        for selector in ["button:has-text('생성')", "button:has-text('Generate')", "button[type='submit']"]:
            clicked = safe_click(page, selector)
            if clicked:
                break
        page.wait_for_timeout(5000)
        page.screenshot(path=str(ARTIFACTS / "direct-text-generate.png"), full_page=True)
        ok = filled and clicked and ("error" not in page.content().lower()[:2000])
        record(lines, ok, "direct-text-generate", "direct-text-generate.png captured")
        failures += 0 if ok else 1

        if console_errors:
            lines.append("\n## Console Errors")
            for err in console_errors[:20]:
                lines.append(f"- {err}")

        browser.close()

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 실행**

```powershell
.\.venv\Scripts\python.exe tests/e2e/autoqa/run_autoqa.py
```

Expected: `QA_REPORT.md` 생성, `tests/e2e/autoqa/artifacts/*.png` 생성.

---

### Task 6: 실패 기능 수정 루프

**Files:**
- Modify failing feature files only.
- Update: `QA_REPORT.md`

- [ ] **Step 1: 실패 케이스마다 로그 수집**

```powershell
Get-Content QA_REPORT.md
```

- [ ] **Step 2: 백엔드 에러는 Flask 콘솔에서 스택 확인**

Expected: 실패 endpoint, exception, status code 확인.

- [ ] **Step 3: 프론트 에러는 Playwright console errors 확인**

Expected: `QA_REPORT.md`의 `Console Errors` 섹션 확인.

- [ ] **Step 4: 하나의 실패만 수정**

규칙:
- 한 번에 한 기능만 고친다.
- 수정 후 해당 케이스만 재실행한다.
- 통과하면 전체 러너를 재실행한다.

- [ ] **Step 5: 전체 QA 재실행**

```powershell
.\.venv\Scripts\python.exe tests/e2e/autoqa/run_autoqa.py
npm run lint --prefix frontend
npx tsc --noEmit --project frontend/tsconfig.json
```

Expected:
- QA runner exit code `0`
- lint exit code `0`
- typecheck exit code `0`

---

## Completion Criteria

- `http://localhost:3000`에서 주요 UI가 로드된다.
- `/api/providers`가 ChatMock 5.5를 반환한다.
- 직접 텍스트 생성이 ChatMock 5.5로 완료된다.
- 주요 버튼/패널/스타일 선택이 브라우저 자동 QA에서 확인된다.
- 실패한 기능은 재현 스크린샷과 수정 후 통과 증거가 `QA_REPORT.md`에 남는다.
- 실제 비밀 키는 Git diff에 포함되지 않는다.

## Execution Choice

1. **Subagent-Driven (recommended)** — 태스크별 독립 실행/리뷰.
2. **Inline Execution** — 이 세션에서 순서대로 실행.
