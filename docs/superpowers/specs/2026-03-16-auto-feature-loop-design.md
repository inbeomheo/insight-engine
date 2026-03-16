# Auto Feature Loop — Meta-Prompt 기반 기능 자율 확장

## 목적

Insight Engine 앱에 autoresearch 패턴을 적용하여, 코드베이스 분석 → 기능 발굴 → 구현 → 검증 → keep/revert를 10라운드 자율 반복하는 루프를 설계한다.

## 실행 방식

- 1세션 연속 실행 (`/loop` 스킬 활용)
- 1기능/라운드, 총 10라운드
- meta-prompt-generator로 루프 제어 프롬프트 생성

## 전체 구조

```
Meta-Prompt (루프의 두뇌)
  → 코드베이스 분석 → 기능 후보 발굴
  → 구현 전략 결정
  → keep/revert 판단 기준

라운드 N (10회 반복):
  Phase 1: DISCOVER — 코드베이스 분석 → 개선점/신기능 1개 선정
  Phase 2: PLAN — 수정 파일, 신규 파일, 테스트 목록 작성
  Phase 3: IMPLEMENT — 백엔드 + 프론트엔드 코드 작성
  Phase 4: TEST — 단위 테스트 작성 + pytest + tsc + build
  Phase 5: JUDGE — Frozen Metric 통과 → keep + commit / 실패 → revert
```

## Frozen Metric

| 체크 | 명령 | 통과 기준 |
|------|------|----------|
| 타입 체크 | `cd frontend && npx tsc --noEmit` | exit 0 |
| 프론트 빌드 | `cd frontend && npx next build` | exit 0 |
| 백엔드 테스트 | `python -m pytest tests/ -x -q` | 기존 통과 수 이상 |
| 신규 테스트 | `python -m pytest tests/test_신규.py -v` | 전체 통과 |

4개 모두 통과 → keep (git commit), 하나라도 실패 → revert (git checkout .)

## 기능 발굴 전략 (DISCOVER Phase)

매 라운드 아래 소스 분석으로 기능 후보 자율 선정:

| 소스 | 분석 방법 |
|------|----------|
| 코드 TODO/FIXME | grep 수집 |
| 미사용 서비스 | import 되었으나 라우트 없는 서비스 |
| 기존 기능 보강 | 에러 핸들링 부족, 엣지케이스 |
| UX 개선 | 로딩 스켈레톤, 빈 상태 등 |
| 성능 | 번들 크기, 쿼리 최적화, 캐싱 |

이전 라운드에서 추가한 기능은 제외 (중복 방지).

## keep/revert 흐름

```
git stash (안전망)
  → 구현
  → Frozen Metric 4종 실행
  → 전부 통과?
    YES → git add + commit "feat: [R{N}] 기능명"
    NO  → git checkout . (전체 복원)
  → progress.md에 결과 기록
  → 다음 라운드
```

## 산출물

- `autoresearch/feature-loop/program.md` — 루프 제어 meta-prompt
- `autoresearch/feature-loop/eval.sh` — Frozen Metric 실행 스크립트
- `autoresearch/feature-loop/progress.tsv` — 라운드별 결과 기록
- 매 라운드 성공 시 git commit

## 제약 조건

- 기존 테스트 깨뜨리면 무조건 revert
- 외부 패키지 추가 금지 (기존 의존성 범위 내)
- 1라운드당 최대 3파일 수정/생성 (범위 제한)
