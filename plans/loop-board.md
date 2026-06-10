# insight-engine 루프 보드

> dev-loop 스킬(.claude/skills/dev-loop/SKILL.md)의 상태 파일.
> 컨텍스트는 세션마다 사라지지만 이 파일은 남는다 — 루프의 척추.
> 규칙: 항목마다 "완료 기준" 필수 / 사람 결정이 필요한 항목은 `[사람]` 태그 / 사이클당 1항목.

## 진행중

(없음)

## 백로그

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

- [x] 2026-06-10 PR #23 Codex P2 리뷰 지적 3건 반영 (캐시 히트 자막 재추출 폴백 / GLM 챕터 병렬 제외 / BASE 프롬프트 소스 중립화) — 전체 5,414 passed + code-reviewer 통과
- [x] 2026-06-10 데드 엔드포인트 ~200개 제거 + 깨진 테스트 142개 정리 — 커밋 6e2da90, 전체 5,414 passed / 0 fail
- [x] 2026-06-10 성능 최적화 + 프롬프트 v4 재작성 + 정리 — 5커밋, PR #23 푸시됨

## 학습/메모

- 멀티라인 커밋 메시지는 Bash heredoc(`git commit -F - <<'EOF'`) 사용 — PowerShell here-string 금지 (2026-06-10)
- (사이클에서 얻은 짧은 메모를 여기에. 일반 규칙이 되면 ~/.claude/session-learnings/로 증류)
