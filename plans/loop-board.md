# insight-engine 루프 보드

> dev-loop 스킬(.claude/skills/dev-loop/SKILL.md)의 상태 파일.
> 컨텍스트는 세션마다 사라지지만 이 파일은 남는다 — 루프의 척추.
> 규칙: 항목마다 "완료 기준" 필수 / 사람 결정이 필요한 항목은 `[사람]` 태그 / 사이클당 1항목.

## 진행중

(없음)

## 백로그

- [ ] ruff 정리 (기존 위반, 단일 `style:` PR): scheduler_worker.py format(따옴표 `'scheduler_worker'`/`'/tmp/...'` wrap/빈줄) + test_logging_config.py `LOG_FORMAT`/`DATE_FORMAT` 미사용 import(F401). PR #71/#72 추가 라인은 준수.
- [ ] [사람] CI 수정 푸시 막힘 — git/gh 토큰에 `workflow` 스코프가 없어 .github/workflows 변경
  푸시가 원격에서 거부됨. 수정안은 `plans/ci-workflow-fix.patch`에 보존
  (master 트리거 + flake8 권고화 + RATE_LIMIT_ENABLED=false + 미선언 의존성 테스트 격리).
  - 적용법: `gh auth refresh -h github.com -s workflow` (브라우저 인증) →
    `git apply plans/ci-workflow-fix.patch` → 커밋 → 푸시
- [ ] [사람] duckduckgo_search가 requirements.txt에 미선언 — web_research_service.py:7이 톱레벨
  import라 새 환경에선 퓨전/웹리서치/경쟁분석 기능이 깨짐. 의존성 추가 여부 결정 필요
  (추가 시 ci-workflow-fix.patch의 테스트 격리 4건도 해제)
- [ ] [사람] ci.yml의 docker-build/deploy/커버리지 잡이 `refs/heads/main` 게이트 — master로
  바꾸면 푸시마다 Docker Hub 푸시 + Railway 프로덕션 배포가 켜지므로 운영 결정 필요
- [ ] [사람] 데드 엔드포인트 잔여 335건 — 삭제 안전 판정 완료, 제품 결정 대기
  (plans/dead-code-audit-2026-06-10.md 참조)

## Done

- [x] 2026-06-27 fix(test): datetime.utcnow() deprecation 제거 (PR #73, stacked base PR #71). test_account_service.py:108 datetime.utcnow() → datetime.now(timezone.utc). code-reviewer 승인(-W error::DeprecationWarning 통과, 외과적/회귀 없음) — pytest DeprecationWarning 0 + 전체 5,445 passed/0 fail
- [x] 2026-06-27 fix(logging): logging_config cp949 UnicodeEncodeError 근본 차단 (PR #72, stacked base PR #71). _ensure_utf8_stdout()로 sys.stdout을 utf-8/errors='replace'로 재구성 → get_logger 시점 buffer 고정 회피 + surrogate 안전. code-reviewer 지적(reconfigure 전환+errors=replace+테스트+타입힌트) 반영 — em-dash/이모지/surrogate 로깅 에러 0 + test_logging_config 12 passed + 전체 5,448 passed/0 fail
- [x] 2026-06-27 fix(scheduler): scheduler_worker cp949 로깅 em-dash UnicodeEncodeError 핫픽스 (PR #71 추가 커밋 9682c78+065420e). em-dash 3곳 ASCII 교정 + test 기대값 동기화 + 주석 공백 복원 — app import 에러 제거 + scheduler_worker 테스트 7 passed + ruff 통과. code-reviewer [CRITICAL](근본 미해결, services/ 123개 파일)은 사이클 3 logging_config 근본으로 이관
- [x] 2026-06-27 fix(scheduler): scheduler_worker 모듈 최상단 `import fcntl`(PR #42) → Windows에서 app import 실패, 테스트 46개 파일 컬렉션 에러 회귀 수정 (PR #71). fcntl 조건부 import + Windows 리더 락 우회, Unix flock 로직 보존 — pytest 5,445 passed(0 fail, 46 컬렉션 에러 해소) + code-reviewer 클린
- [x] 2026-06-22 feat(ui): SupportAssistant shadow #15171F → Signal 토큰 (PR #54, 다크모드 그림자 누락 버그 수정) — tsc 0 + build 성공 + code-reviewer 클린
- [x] 2026-06-23 refactor(export): <style> → 공유 모듈 + Signal 정규화 (PR #62, PR #60/#61 대체 + useExport 인쇄 #111 처리) — tsc+build 성공 + code-reviewer 클린
- [x] 2026-06-23 feat(ui): ResultCard 인쇄 템플릿 #111 → Signal foreground (PR #61, handlePrint 누락분) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): 내보내기 HTML CSS 구식 색 → Signal 정규화 (PR #60, useExport + ResultCard 5종 색) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): global-error/layout 구식 인디고 → Signal primary (PR #59, #6366f1/#4F46E5/#6b7280 정규화) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): MobileAppShell warm beige #F1EDE5 → Signal 토큰 (PR #58, L176 bg-card / L219 bg-muted, 구식 warm 제거+다크모드 버그) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): MobileAppShell 배경 #F5F6F8 → bg-background 토큰 (PR #57, 4곳, 다크모드 버그 수정) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): #2F54EB 사용처 → --primary 토큰 (PR #56, page shadow + prose border + gradient) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): page/MobileAppShell shadow 5곳 → Signal 토큰 (PR #55, 동일 패턴) — build 성공 + code-reviewer 클린
- [x] 2026-06-10 PR #23 Codex P2 리뷰 지적 3건 반영 (캐시 히트 자막 재추출 폴백 / GLM 챕터 병렬 제외 / BASE 프롬프트 소스 중립화) — 전체 5,414 passed + code-reviewer 통과
- [x] 2026-06-10 데드 엔드포인트 ~200개 제거 + 깨진 테스트 142개 정리 — 커밋 6e2da90, 전체 5,414 passed / 0 fail
- [x] 2026-06-10 성능 최적화 + 프롬프트 v4 재작성 + 정리 — 5커밋, PR #23 푸시됨

## 학습/메모

- 2026-06-22 프론트엔드 디자인 루프 시작 (/loop 20m + dev-loop, cron 0bfd9f6d). 백로그를 디자인 항목으로 채워 dev-loop이 화면 단위 리디자인을 잡도록 구성.
- 2026-06-22 보드 정책 수정: loop-board.md는 master에 직접 추적(루프 상태=인프라). 코드는 작업 브랜치/PR로 분리. 보드를 코드 PR에 넣으면 작업 브랜치에 갇혀 master 기반 새 브랜치가 백로그를 못 봄(cycle 1에서 발견).
- 2026-06-22 MobileAppShell CATEGORY_DOTS(#E90043/#7C5CFF/#20C997/#2F80ED/#F2B705) 데이터 팔레트는 의도적 유지 결정 — 한 파일 로컬 + 소스 타입 구분은 테마 독립이 맞음, 토큰화는 과잉(Simplicity First).
- 2026-06-22 settings/billing/marketplace/library/analytics/schedule/search/modals/input 영역 Signal 감정 완료 — 전부 hex 0, 이미 토큰화됨. 남은 hex는 데이터 시각화(GraphVisualization/ResultCard 차트/api og) + 구식 인디고 잔재뿐.
- 2026-06-22 GraphVisualization NODE_COLORS(#6366f1/#10b981/#f59e0b/#ef4444)는 데이터 시각화 범주 팔레트로 의도적 유지 결정 — 4 노드 타입 구분이 핵심, --chart-*와 부분 일치(entity=#f59e0b)하지만 topic red 대응 없어 로컬 유지(CATEGORY_DOTS와 동일 결정).
- 2026-06-23 ResultCard 감정 완료 — UI hex는 handlePrint 인쇄 템플릿 #111 한 곳(PR #61 처리). 나머지는 내보내기 CSS(PR #60) 또는 GRADE_STYLES Tailwind 색 이름(hex 아님). ResultCard 토큰 마이그레이션 완료.
- 2026-06-23 cycle 9 트리아지: PR #54~#61 전부 미머지 → `<style>` 리팩터 블로커(PR #60/#61과 같은 인라인 영역, 충돌). 디자인 토큰 마이그레이션은 완료. 남은 산물 = PR 8개 머지 + 리팩터 1건(머지 후).
- 2026-06-23 cycle 10: <style> 공유 모듈(lib/exportHtmlTemplate.ts) 추출 + Signal 정규화 — PR #62. PR #60/#61 supersede + useExport 인쇄 #111 미발견분 처리. **디자인 토큰 루프 백로그 완전 종료.** PR #54~#62(#60/#61은 #62가 대체) 머지 대기 — 머지 후 루프 종료.
- 2026-06-23 cycle 11 점검 — 이상 없음 (PR 리뷰 0 / CI main 게이트로 PR 미실행 / ESLint 0경고 / tsc 통과). 디자인 백로그 비어 루프 자연 종료 상태. 새 방향 없으면 빈 사이클 반복.
- 2026-06-23 **디자인 토큰 루프 종료** (cron 0bfd9f6d 삭제). 11사이클(PR #54~#62, #60/#61은 #62가 대체) 완료. 머지 대기.
- 2026-06-11 00:26·00:58·01:59·02:59 야간 루프 점검 — 이상 없음 (새 리뷰 코멘트·CI 런·워킹트리 변경 없음)

- 멀티라인 커밋 메시지는 Bash heredoc(`git commit -F - <<'EOF'`) 사용 — PowerShell here-string 금지 (2026-06-10)
- (사이클에서 얻은 짧은 메모를 여기에. 일반 규칙이 되면 ~/.claude/session-learnings/로 증류)
