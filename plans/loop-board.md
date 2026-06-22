# insight-engine 루프 보드

> dev-loop 스킬(.claude/skills/dev-loop/SKILL.md)의 상태 파일.
> 컨텍스트는 세션마다 사라지지만 이 파일은 남는다 — 루프의 척추.
> 규칙: 항목마다 "완료 기준" 필수 / 사람 결정이 필요한 항목은 `[사람]` 태그 / 사이클당 1항목.

## 진행중

(없음)

## 백로그

- [ ] feat(ui): GraphVisualization.tsx 노드 색 #6366f1(3곳: 45/160/175) → Signal 처리 — 구식 인디고이나 데이터 시각화 팔레트(NODE_COLORS). --chart-* 매핑 또는 --primary 검토. 완료기준: 결정 + build 성공
- [ ] feat(ui): 내보내기 HTML 인라인 CSS #4F46E5/#6B7280 → Signal — useExport.ts:38 + ResultCard.tsx:365 동일 문자열(독립 문서). 완료기준: build 성공
- [ ] feat(ui): ResultCard.tsx 남은 hex 감정 — 차트/데이터 색 vs UI 색 구분 후 UI 색 토큰화. 완료기준: 감정 + (UI 색 시) build 성공

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

- [x] 2026-06-22 feat(ui): SupportAssistant shadow #15171F → Signal 토큰 (PR #54, 다크모드 그림자 누락 버그 수정) — tsc 0 + build 성공 + code-reviewer 클린
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
- 2026-06-11 00:26·00:58·01:59·02:59 야간 루프 점검 — 이상 없음 (새 리뷰 코멘트·CI 런·워킹트리 변경 없음)

- 멀티라인 커밋 메시지는 Bash heredoc(`git commit -F - <<'EOF'`) 사용 — PowerShell here-string 금지 (2026-06-10)
- (사이클에서 얻은 짧은 메모를 여기에. 일반 규칙이 되면 ~/.claude/session-learnings/로 증류)
