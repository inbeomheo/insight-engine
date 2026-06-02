# QA_REPORT

- Generated: 2026-06-03 07:06:45
- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:5001`
- ChatMock: `http://127.0.0.1:8000/v1`
- Target model: `chatmock/gpt-5.5`

## QA Matrix

| ID | Name | Expect |
|---|---|---|
| home-load | 홈 로드 | 메인 UI가 보인다 |
| studio-layout | 스튜디오 레이아웃 | 스튜디오 shell과 composer가 보인다 |
| studio-copy-polish | 스튜디오 핵심 카피 | 핵심 스튜디오 라벨과 빈 상태가 읽히는 한국어로 표시된다 |
| studio-copy-readable | 스튜디오 깨진 카피 방지 | 보이는 스튜디오/소스/우측 패널 카피에 물음표 placeholder가 없다 |
| studio-status-labels | 스튜디오 상태 요약 라벨 | Generate Dock과 우측 패널이 raw 설정값 대신 사용자용 한국어 라벨을 보여준다 |
| generate-dock-source-summary | Generate Dock 소스 종류 요약 | 텍스트/파일/음성처럼 현재 선택한 소스 종류가 Generate Dock 요약에 표시된다 |
| output-blueprint-advanced | Output Blueprint 고급 컨트롤 | 웹 보강, 웹 리서치, 댓글 분석, 상세도, 에이전트, 모델 요약 컨트롤이 보인다 |
| header-status-summary | 헤더 상태 요약 | 헤더에 현재 모델과 작업 상태가 표시된다 |
| mobile-right-panel-drawer | 모바일 작업 패널 Drawer | 모바일 헤더에서 Studio 작업 패널을 열 수 있다 |
| source-file-generate | 파일 소스 생성 | 파일 탭에서 업로드 후 Generate Dock으로 결과를 만든다 |
| source-voice-generate | 음성 소스 생성 | 음성 탭에서 오디오 업로드 후 Generate Dock으로 결과를 만든다 |
| chatmock-server | ChatMock OpenAI 호환 서버 | HTTP 200과 gpt-5.5 모델이 반환된다 |
| provider-chatmock | ChatMock 5.5 공급자 노출 | chatmock/gpt-5.5를 선택할 수 있다 |
| direct-text-generate | 직접 텍스트 생성 | 생성 결과가 보인다 |
| direct-text-advanced-request-options | 직접 텍스트 고급 옵션 요청 반영 | 직접 텍스트 생성도 상세도, 웹 보강, 에이전트 설정을 /generate 요청에 포함한다 |
| batch-advanced-request-options | 개별 배치 생성 고급 옵션 요청 반영 | 2개 이상 URL의 개별 배치 생성도 상세도, 웹 보강, 에이전트 설정을 /generate-batch 요청에 포함한다 |
| merged-advanced-request-options | 통합 생성 고급 옵션 요청 반영 | 통합 생성도 상세도, 웹 보강, 에이전트 설정을 /api/generate-merged 요청에 포함한다 |
| fusion-advanced-request-options | 퓨전 생성 고급 옵션 요청 반영 | 퓨전 생성도 상세도, 웹 보강, 에이전트, 웹 리서치, 댓글 설정을 /api/generate-fusion 요청에 포함한다 |
| text-dock-generate | 텍스트 Generate Dock 생성 | Generate Dock이 직접 텍스트 소스를 처리한다 |
| result-workbench | Result Workbench 패널 | 생성 결과에 빠른 workbench 액션이 보인다 |
| studio-result-toolbar | 스튜디오 결과 툴바 | 결과 영역이 결과 수, 필터, 보기 모드, 현재 표시 수를 스튜디오 톤으로 요약한다 |
| studio-empty-state-guidance | 스튜디오 빈 상태 안내 | 결과가 없을 때 소스 입력, 산출물 설계, Generate Dock, Workbench 흐름을 안내한다 |
| result-workbench-copy-readable | Result Workbench 카피 | Result Workbench 빠른 액션이 읽히는 한국어이고 물음표 placeholder가 없다 |
| result-workbench-sections | Result Workbench 섹션형 액션 허브 | 읽기, 개선, NLM, 내보내기, 배포, 관리 섹션이 결과 카드에서 바로 보인다 |
| result-workbench-read-actions | Result Workbench 읽기 액션 | 읽기 섹션에서 제목/본문 복사, 리치 복사, 자막/요약 토글을 바로 실행할 수 있다 |
| result-workbench-preview-actions | Result Workbench 미리보기 액션 | 읽기 섹션에서 Markdown/HTML 미리보기와 타임라인 전환을 바로 실행할 수 있다 |
| result-workbench-export-status | Result Workbench 내보내기 실행 상태 | Workbench 내보내기 버튼을 실행하면 다운로드와 함께 섹션 안에 완료 상태가 남는다 |
| result-workbench-nlm-all | Result Workbench 전체 NLM 산출물 | 비디오, 인포그래픽, 슬라이드, 마인드맵, 퀴즈, 플래시카드, 브리핑, 스터디 가이드가 Workbench에서 바로 보인다 |
| result-workbench-nlm-podcast-removed | Result Workbench NLM 팟캐스트 제거 | 사용하지 않는 NLM 팟캐스트 액션은 Workbench와 메뉴에 보이지 않는다 |
| workbench-nlm-auth-notice | Workbench NLM 인증 안내 | NotebookLM 인증이 없을 때 토스트만이 아니라 Workbench NLM 섹션 안에 nlm login 안내가 남는다 |
| right-panel-settings | 우측 패널 설정 요약 | 우측 패널에 현재 모델/스타일/모드가 표시된다 |
| right-panel-advanced-summary | 우측 패널 고급 설정 요약 | 우측 패널 현재 설정에 상세도, 웹 보강, 웹 리서치, 댓글 분석, 에이전트 상태가 함께 표시된다 |
| right-panel-nlm | 우측 패널 NLM 산출물 | 우측 패널이 최근 NotebookLM 산출물 상태를 요약한다 |
| right-panel-nlm-quick-view | 우측 패널 NLM 바로 보기 | 우측 패널 NLM 산출물 빠른 액션이 최근 완료 산출물 보기 창을 연다 |
| notebooklm-view-download-labels | NotebookLM 보기/HTML 저장 라벨 | 완료된 NotebookLM 산출물이 브라우저 보기와 HTML 저장을 명확히 구분하고 원본 MD 저장으로 오인되지 않는다 |
| notebooklm-html-download-extension | NotebookLM HTML 저장 확장자 | Markdown 산출물의 HTML 저장 버튼은 백엔드가 MD attachment를 보내도 .html 파일로 저장한다 |
| right-panel-export-all | 우측 패널 전체 내보내기 | 우측 패널 내보내기 빠른 액션이 전체 결과 Markdown 다운로드와 완료 상태를 남긴다 |
| right-panel-rewrite-action | 우측 패널 플랫폼 변환 실행 | 우측 패널 플랫폼 변환 빠른 액션이 최근 결과의 플랫폼별 카피 변환 모달을 연다 |
| right-panel-recent-result-focus | 우측 패널 최근 결과 이동 | 우측 패널 최근 결과를 클릭하면 해당 결과 카드로 이동하고 포커스 상태가 남는다 |
| right-panel-schedule-card | 우측 패널 예약 카드 이동 | 우측 패널 하단 예약 카드를 클릭하면 예약 캘린더로 이동한다 |
| right-panel-quick-actions | 우측 패널 빠른 액션 | 빠른 액션이 캘린더/설정/workbench 대상으로 이동한다 |
| right-panel-action-guidance | 우측 패널 빠른 액션 안내 | 각 빠른 액션이 어떤 작업 영역으로 이동하는지 짧은 설명과 대상 상태를 보여준다 |
| youtube-url-validation | YouTube URL 입력 검증 | URL이 허용되거나 실행 가능한 오류가 표시된다 |
| style-selection | 스타일 선택 | 스타일 컨트롤을 사용할 수 있다 |
| settings-open | 설정 열기 | 설정 패널이 보인다 |
| history-panel | 히스토리 패널 | 히스토리 빈 상태 또는 목록이 보인다 |
| export-buttons | 내보내기 버튼 | 생성 후 내보내기 액션이 보인다 |
| menu-all-items | 결과 카드 전체 액션 메뉴 | 복사, 프롬프트, NLM, 내보내기, 예약, 공유, 삭제 액션이 보이고 직접 CMS 발행 액션은 없다 |
| menu-action-clicks | 결과 카드 전체 액션 실행 | 남은 메뉴 항목을 클릭하면 예상 UI/API/download side effect가 발생한다 |

## Results

| Case | Result | Evidence |
|---|---|---|
| chatmock-server | PASS | /v1/models ids=['gpt-5.5', 'gpt-5', 'gpt-5.1', 'gpt-5.2', 'gpt-5.4', 'gpt-5.3-codex'] |
| provider-chatmock-api | PASS | first_model=chatmock/gpt-5.5 |
| direct-text-api | PASS | title='ChatMock 5.5 API 회귀 테스트 요약', source=direct_input |
| home-load | PASS | tests/e2e/autoqa/artifacts/home-load.png |
| studio-layout | PASS | studio hero/source composer visible |
| header-status-summary | PASS | tests/e2e/autoqa/artifacts/header-status-summary.png |
| studio-copy-polish | PASS | tests/e2e/autoqa/artifacts/studio-copy-polish.png |
| studio-empty-state-guidance | PASS | tests/e2e/autoqa/artifacts/studio-empty-state-guidance.png |
| studio-copy-readable | PASS | tests/e2e/autoqa/artifacts/studio-copy-readable.png |
| studio-status-labels | PASS | tests/e2e/autoqa/artifacts/studio-status-labels.png |
| generate-dock-source-summary | PASS | tests/e2e/autoqa/artifacts/generate-dock-source-summary.png |
| output-blueprint-advanced | PASS | tests/e2e/autoqa/artifacts/output-blueprint-advanced.png |
| source-file-generate | PASS | tests/e2e/autoqa/artifacts/source-file-generate.png |
| source-voice-generate | PASS | tests/e2e/autoqa/artifacts/source-voice-generate.png |
| settings-open | PASS | tests/e2e/autoqa/artifacts/settings-open.png |
| provider-chatmock | PASS | settings popover contains ChatMock/GPT-5.5 |
| style-selection | PASS | style buttons=22 |
| youtube-url-validation | PASS | tests/e2e/autoqa/artifacts/youtube-url-validation.png |
| direct-text-generate | PASS | tests/e2e/autoqa/artifacts/direct-text-generate.png |
| text-dock-generate | PASS | tests/e2e/autoqa/artifacts/direct-text-generate.png |
| studio-result-toolbar | PASS | tests/e2e/autoqa/artifacts/studio-result-toolbar.png |
| result-workbench | PASS | tests/e2e/autoqa/artifacts/result-workbench.png |
| result-workbench-copy-readable | PASS | tests/e2e/autoqa/artifacts/result-workbench-copy-readable.png |
| result-workbench-sections | PASS | tests/e2e/autoqa/artifacts/result-workbench-sections.png |
| result-workbench-read-actions | PASS | tests/e2e/autoqa/artifacts/result-workbench-read-actions.png |
| result-workbench-preview-actions | PASS | tests/e2e/autoqa/artifacts/result-workbench-preview-actions.png |
| result-workbench-nlm-all | PASS | tests/e2e/autoqa/artifacts/result-workbench-nlm-all.png |
| result-workbench-nlm-podcast-removed | PASS | NLM 팟캐스트 액션 없음 |
| history-panel | PASS | tests/e2e/autoqa/artifacts/history-panel.png |
| export-buttons | PASS | tests/e2e/autoqa/artifacts/export-buttons.png |
| notebooklm-view-download-labels | PASS | tests/e2e/autoqa/artifacts/notebooklm-view-download-labels.png |
| notebooklm-html-download-extension | PASS | download=qa-study-guide.html |
| menu-all-items | PASS | tests/e2e/autoqa/artifacts/menu-all-items.png |
| menu-action:제목-복사 | PASS | clipboard_len=16 |
| menu-action:전체-복사 | PASS | clipboard_len=127 |
| menu-action:프롬프트-보기 | PASS | tests/e2e/autoqa/artifacts/menu-prompt-view.png |
| menu-action:플랫폼-변환 | PASS | tests/e2e/autoqa/artifacts/menu-platform-convert.png |
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
| result-workbench-export-status | PASS | tests/e2e/autoqa/artifacts/result-workbench-export-status.png |
| menu-action:PDF-인쇄 | PASS | print_called=True |
| menu-action:예약-발행 | PASS | tests/e2e/autoqa/artifacts/menu-schedule.png |
| menu-action:공유 | PASS | clipboard_len=197 |
| menu-action:삭제 | PASS | card_removed=True |
| workbench-nlm-auth-notice | PASS | tests/e2e/autoqa/artifacts/workbench-nlm-auth-notice.png |
| direct-text-advanced-request-options | PASS | payload={'url': '', 'model': 'chatmock/gpt-5.5', 'style': 'blog_seo', 'modifiers': {'length': 'medium', 'writing_style': 'conversational', 'language': 'ko'}, 'content': 'Direct text advanced option QA source. This text is intentionally longer than fifty characters so generation is enabled.', 'web_search': True, 'agent_mode': True, 'detail_level': 'deep'} |
| batch-advanced-request-options | PASS | payload={'urls': ['https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'https://www.youtube.com/watch?v=wr4nCMUy1dk'], 'model': 'chatmock/gpt-5.5', 'style': 'blog_seo', 'modifiers': {'length': 'medium', 'writing_style': 'conversational', 'language': 'ko'}, 'detail_level': 'deep', 'web_search': True, 'agent_mode': True} |
| merged-advanced-request-options | PASS | payload={'urls': ['https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'https://www.youtube.com/watch?v=wr4nCMUy1dk'], 'model': 'chatmock/gpt-5.5', 'style': 'blog_seo', 'modifiers': {'length': 'medium', 'writing_style': 'conversational', 'language': 'ko'}, 'detail_level': 'deep', 'web_search': True, 'agent_mode': True} |
| fusion-advanced-request-options | PASS | payload={'urls': ['https://www.youtube.com/watch?v=aaaaaaaaaaa', 'https://www.youtube.com/watch?v=bbbbbbbbbbb'], 'style': 'blog_seo', 'model': 'chatmock/gpt-5.5', 'modifiers': {'length': 'medium', 'writing_style': 'conversational', 'language': 'ko'}, 'enable_web_research': True, 'enable_deep_comments': True, 'detail_level': 'deep', 'web_search': True, 'agent_mode': True} |
| right-panel-settings | PASS | tests/e2e/autoqa/artifacts/right-panel-settings.png |
| right-panel-advanced-summary | PASS | tests/e2e/autoqa/artifacts/right-panel-advanced-summary.png |
| right-panel-nlm | PASS | nlm_count=3 |
| right-panel-nlm-quick-view | PASS | url=http://127.0.0.1:5001/api/notebooklm/view/rp-briefing |
| right-panel-action-guidance | PASS | tests/e2e/autoqa/artifacts/right-panel-action-guidance.png |
| right-panel-export-all | PASS | download=insight-studio-export-2026-06-02.md; notice=전체 내보내기 완료 · 1개 결과 |
| right-panel-rewrite-action | PASS | tests/e2e/autoqa/artifacts/right-panel-rewrite-action.png |
| right-panel-recent-result-focus | PASS | tests/e2e/autoqa/artifacts/right-panel-recent-result-focus.png |
| right-panel-schedule-card | PASS | tests/e2e/autoqa/artifacts/right-panel-schedule-card.png |
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
- 브라우저 console error는 참고용으로 기록했습니다.

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
