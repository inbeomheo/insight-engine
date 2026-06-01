# QA_REPORT

- Generated: 2026-06-01 23:35:49
- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:5001`
- ChatMock: `http://127.0.0.1:8000/v1`
- Target model: `chatmock/gpt-5.5`

## QA Matrix

| ID | Name | Expect |
|---|---|---|
| home-load | 홈 로드 | main UI visible |
| chatmock-server | ChatMock OpenAI 호환 서버 | HTTP 200 |
| provider-chatmock | ChatMock 5.5 공급자 노출 | chatmock/gpt-5.5 selectable |
| direct-text-generate | 직접 텍스트 생성 | generated result visible |
| youtube-url-validation | YouTube URL 입력 검증 | URL accepted or actionable error |
| style-selection | 스타일 선택 | style controls usable |
| settings-open | 설정 열기 | settings panel visible |
| history-panel | 히스토리 패널 | history empty state or list visible |
| export-buttons | 내보내기 버튼 | export actions visible after generation |

## Results

| Case | Result | Evidence |
|---|---|---|
| chatmock-server | PASS | /v1/models ids=['gpt-5.5', 'gpt-5', 'gpt-5.1', 'gpt-5.2', 'gpt-5.4', 'gpt-5.3-codex'] |
| provider-chatmock-api | PASS | first_model=chatmock/gpt-5.5 |
| direct-text-api | PASS | title='ChatMock 5.5 API 공개: 핵심만 먼저 확인해요', source=direct_input |
| home-load | PASS | tests/e2e/autoqa/artifacts/home-load.png |
| settings-open | PASS | tests/e2e/autoqa/artifacts/settings-open.png |
| provider-chatmock | PASS | settings popover contains ChatMock/GPT-5.5 |
| style-selection | PASS | style buttons=22 |
| youtube-url-validation | PASS | tests/e2e/autoqa/artifacts/youtube-url-validation.png |
| direct-text-generate | PASS | tests/e2e/autoqa/artifacts/direct-text-generate.png |
| history-panel | PASS | tests/e2e/autoqa/artifacts/history-panel.png |
| export-buttons | PASS | tests/e2e/autoqa/artifacts/export-buttons.png |

## Fixes Applied

- `config.py`: Set ChatMock default provider model to `chatmock/gpt-5.5` and filtered placeholder API keys.
- `routes/blog_routes.py`: Switched default generation model to `DEFAULT_MODEL` / `chatmock/gpt-5.5`.
- `frontend/app/page.tsx`: Wired the existing direct-text input component into the main page.
- `tests/e2e/autoqa/*`: Added ChatMock 5.5 server wrapper, QA matrix, Playwright QA runner, and Windows stack runner/cleanup script.
- QA CORS/CSRF path is verified with explicit `CORS_ORIGINS`, `Origin`, and `Referer` headers matching browser execution.
- Export-menu QA now scopes clicks to the generated result card, avoiding the Next.js dev overlay.

## Summary

- Failures: `0`
