# QA_REPORT

- Generated: 2026-06-03 02:28:32
- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:5001`
- ChatMock: `http://127.0.0.1:8000/v1`
- Target model: `chatmock/gpt-5.5`

## QA Matrix

| ID | Name | Expect |
|---|---|---|
| home-load | 홈 로드 | main UI visible |
| studio-layout | ???? ???? | studio shell and composer visible |
| header-status-summary | Header status summary | header shows current model and work status |
| mobile-right-panel-drawer | Mobile right panel drawer | mobile header opens the studio work panel drawer |
| source-file-generate | Source file generate | file tab accepts upload and Generate Dock creates a result |
| source-voice-generate | Source voice generate | voice tab accepts audio upload and Generate Dock creates a result |
| chatmock-server | ChatMock OpenAI 호환 서버 | HTTP 200 |
| provider-chatmock | ChatMock 5.5 공급자 노출 | chatmock/gpt-5.5 selectable |
| direct-text-generate | 직접 텍스트 생성 | generated result visible |
| text-dock-generate | ??? Dock ?? | Generate Dock handles direct text source |
| result-workbench | ?? ??? | visible result workbench quick actions |
| right-panel-settings | Right panel settings | right panel shows current model/style/mode settings |
| right-panel-nlm | Right panel NLM artifacts | right panel summarizes recent NotebookLM artifacts by status |
| right-panel-quick-actions | Right panel quick actions | quick actions navigate to calendar/settings/workbench targets |
| youtube-url-validation | YouTube URL 입력 검증 | URL accepted or actionable error |
| style-selection | 스타일 선택 | style controls usable |
| settings-open | 설정 열기 | settings panel visible |
| history-panel | 히스토리 패널 | history empty state or list visible |
| export-buttons | 내보내기 버튼 | export actions visible after generation |
| menu-all-items | 결과 카드 전체 액션 메뉴 | all copy, prompt, NLM, export, schedule, share, delete actions are visible and direct CMS publish actions are absent |
| menu-action-clicks | 결과 카드 전체 액션 실행 | each remaining menu item can be clicked and produces the expected UI/API/download side effect with external services mocked |

## Results

| Case | Result | Evidence |
|---|---|---|
| chatmock-server | PASS | /v1/models ids=['gpt-5.5', 'gpt-5', 'gpt-5.1', 'gpt-5.2', 'gpt-5.4', 'gpt-5.3-codex'] |
| provider-chatmock-api | PASS | first_model=chatmock/gpt-5.5 |
| direct-text-api | PASS | title='ChatMock 5.5 API 변화 요약', source=direct_input |
| home-load | PASS | tests/e2e/autoqa/artifacts/home-load.png |
| studio-layout | PASS | studio hero/source composer visible |
| header-status-summary | PASS | tests/e2e/autoqa/artifacts/header-status-summary.png |
| source-file-generate | PASS | tests/e2e/autoqa/artifacts/source-file-generate.png |
| source-voice-generate | PASS | tests/e2e/autoqa/artifacts/source-voice-generate.png |
| settings-open | PASS | tests/e2e/autoqa/artifacts/settings-open.png |
| provider-chatmock | PASS | settings popover contains ChatMock/GPT-5.5 |
| style-selection | PASS | style buttons=22 |
| youtube-url-validation | PASS | tests/e2e/autoqa/artifacts/youtube-url-validation.png |
| direct-text-generate | PASS | tests/e2e/autoqa/artifacts/direct-text-generate.png |
| text-dock-generate | PASS | tests/e2e/autoqa/artifacts/direct-text-generate.png |
| result-workbench | PASS | tests/e2e/autoqa/artifacts/result-workbench.png |
| history-panel | PASS | tests/e2e/autoqa/artifacts/history-panel.png |
| export-buttons | PASS | tests/e2e/autoqa/artifacts/export-buttons.png |
| menu-all-items | PASS | tests/e2e/autoqa/artifacts/menu-all-items.png |
| menu-action:제목-복사 | PASS | clipboard_len=16 |
| menu-action:전체-복사 | PASS | clipboard_len=127 |
| menu-action:프롬프트-보기 | PASS | tests/e2e/autoqa/artifacts/menu-prompt-view.png |
| menu-action:플랫폼-변환 | PASS | tests/e2e/autoqa/artifacts/menu-platform-convert.png |
| menu-action:NLM-팟캐스트 | PASS | type=audio |
| menu-action:NLM-비디오 | PASS | type=video |
| menu-action:NLM-인포그래픽 | PASS | type=infographic |
| menu-action:NLM-슬라이드 | PASS | type=slide_deck |
| menu-action:NLM-마인드맵 | PASS | type=mindmap |
| menu-action:NLM-퀴즈 | PASS | type=quiz |
| menu-action:NLM-플래시카드 | PASS | type=flashcards |
| menu-action:NLM-브리핑 | PASS | type=briefing |
| menu-action:NLM-스터디-가이드 | PASS | type=study_guide |
| menu-action:이벤트-추출 | PASS | tests/e2e/autoqa/artifacts/menu-event-extract.png |
| menu-action:영상에-질문하기 | PASS | tests/e2e/autoqa/artifacts/menu-video-chat.png |
| menu-action:HTML-내보내기 | PASS | download=QA 전체 메뉴 테스트 리포트.html |
| menu-action:DOCX-내보내기 | PASS | download=QA 전체 메뉴 테스트 리포트.docx |
| menu-action:마크다운-md | PASS | download=QA 전체 메뉴 테스트 리포트.md |
| menu-action:텍스트-txt | PASS | download=QA 전체 메뉴 테스트 리포트.txt |
| menu-action:패키지-zip | PASS | download=QA 전체 메뉴 테스트 리포트.zip |
| menu-action:PDF-인쇄 | PASS | print_called=True |
| menu-action:예약-발행 | PASS | tests/e2e/autoqa/artifacts/menu-schedule.png |
| menu-action:공유 | PASS | clipboard_len=197 |
| menu-action:삭제 | PASS | card_removed=True |
| right-panel-settings | PASS | tests/e2e/autoqa/artifacts/right-panel-settings.png |
| right-panel-nlm | PASS | nlm_count=3 |
| right-panel-quick-actions | PASS | tests/e2e/autoqa/artifacts/right-panel-calendar.png |
| mobile-right-panel-drawer | PASS | tests/e2e/autoqa/artifacts/mobile-right-panel-drawer.png |

## Browser Console Errors

- `[right-panel] A tree hydrated but some attributes of the server rendered HTML didn't match the client properties. This won't be patched up. This can happen if a SSR-ed Client Component used:

- A server/client branch `if (typeof window !== 'undefined')`.
- Variable input such as `Date.now()` or `Math.random()` which changes each time it's called.
- Date formatting in a user's locale which doesn't match the server.
- External changing data without sending a snapshot of it along with the HTML.
- I`

## Notes

- Result-card action menu QA mocks NotebookLM, schedule, rewrite, event extraction, video QA, and binary export APIs to avoid external side effects.
- ???? console error? ?? ??? ??????.

## Fixes Applied

- `config.py`: Set ChatMock default provider model to `chatmock/gpt-5.5` and filtered placeholder API keys.
- `routes/blog_routes.py`: Switched default generation model to `DEFAULT_MODEL` / `chatmock/gpt-5.5`.
- `frontend/app/page.tsx`: Wired the existing direct-text input component into the main page.
- `tests/e2e/autoqa/*`: Added ChatMock 5.5 server wrapper, QA matrix, Playwright QA runner, and Windows stack runner/cleanup script.
- QA CORS/CSRF path is verified with explicit `CORS_ORIGINS`, `Origin`, and `Referer` headers matching browser execution.
- Export-menu QA now scopes clicks to the generated result card, avoiding the Next.js dev overlay.
- Result-card action-menu QA now clicks every copy, prompt, platform, NLM, event, chat, export, schedule, share, and delete item with external side effects mocked.

## Summary

- Failures: `0`
