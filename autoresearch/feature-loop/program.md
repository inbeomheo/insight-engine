# Auto Feature Loop — 라운드 제어 프롬프트

## Context

Insight Engine은 YouTube 영상 URL로 AI 기반 다국어 콘텐츠를 자동 생성하는 Flask + Next.js 웹앱이다.
- 백엔드: Flask (Python), 250+ 서비스 (`services/` 하위 도메인별 구조), 20+ 라우트
- 프론트엔드: Next.js 16 + Tailwind v4 + shadcn (`frontend/`)
- 테스트: pytest (`tests/`), 베이스라인 3399 passed
- 이전 autoresearch: 프론트엔드 RSI 99.45/100, 프롬프트 튜닝 96.4점 달성

## Task

매 라운드마다 코드베이스를 분석하여 가치 있는 기능 1개를 자율 발굴하고, 구현 → 테스트 → 검증까지 완료한다. 10라운드 반복.

## 라운드 실행 절차

### Phase 1: DISCOVER (기능 발굴)

아래 5가지 소스를 순회하며 구현할 기능 1개를 선정한다:

| 우선순위 | 소스 | 분석 방법 | 예시 |
|---------|------|----------|------|
| 1 | TODO/FIXME 주석 | `grep -rn "TODO\|FIXME" services/ routes/ frontend/` | 미구현 캐시, 미완성 검증 |
| 2 | 미연결 서비스 | `services/` 내 파일 중 `routes/`에서 import 안 되는 것 | 만들어놓고 API 없는 서비스 |
| 3 | 에러 핸들링 보강 | try/except 없는 외부 API 호출, 사용자 에러 메시지 미흡 | 타임아웃 처리 누락 |
| 4 | UX 개선 | 로딩 스켈레톤, 빈 상태, 접근성 개선 | 빈 목록 안내 문구 없음 |
| 5 | 성능 최적화 | 불필요한 리렌더링, 캐싱, 쿼리 최적화 | API 응답 캐시 없음 |

**선정 기준:**
- 사용자 가치가 높은 것 우선
- 이전 라운드에서 이미 구현한 기능 제외 (`progress.tsv` 확인)
- 3파일 이내로 구현 가능한 범위
- 기존 코드 구조를 따르는 변경

**출력:** 기능명 1줄 + 선정 이유 1줄

### Phase 2: PLAN (설계)

선정한 기능에 대해:
- 수정할 기존 파일 목록 (파일경로 + 변경 내용 1줄 요약)
- 생성할 신규 파일 목록 (파일경로 + 역할 1줄 요약)
- 작성할 테스트 파일 (파일경로 + 테스트 케이스 목록)

**제약:**
- 총 변경 파일 3개 이내
- 외부 패키지(pip install, npm install) 추가 금지 — 기존 의존성만 사용
- 기존 코드 스타일/패턴 준수 (CLAUDE.md 참조)

### Phase 3: IMPLEMENT (구현)

PLAN에 따라 코드를 작성한다:
- 백엔드: Python, 기존 서비스 패턴 (`services/도메인/파일.py`)
- 프론트엔드: TypeScript + React, shadcn 컴포넌트, Tailwind 클래스
- 라우트: 기존 `routes/*.py` 패턴, `@require_auth` 데코레이터
- import 경로: `from services.도메인 import 서비스명`

### Phase 4: TEST (테스트 작성 + 실행)

구현한 기능의 단위 테스트를 작성한다:
- 파일: `tests/test_기능명.py`
- 패턴: `@patch` 기반 mock, Supabase 비활성화 필수
- 최소 3개 테스트 케이스 (정상, 엣지, 에러)
- 실행: `python -m pytest tests/test_기능명.py -v`

### Phase 5: JUDGE (판정)

Frozen Metric 4종을 순차 실행한다:

```bash
# 1. TypeScript 타입 체크
cd frontend && npx tsc --noEmit

# 2. Next.js 빌드
cd frontend && npx next build

# 3. 기존 pytest (베이스라인 이상)
python -m pytest tests/ -q
# passed 수 >= 3399

# 4. 신규 테스트
python -m pytest tests/test_신규.py -v
```

**판정:**
- 4개 모두 통과 → **KEEP**: `git add` + `git commit -m "feat: [R{N}] 기능명"`
- 하나라도 실패 → **REVERT**: `git checkout .` + 신규 파일 삭제

### Phase 6: RECORD (기록)

`autoresearch/feature-loop/progress.tsv`에 1줄 추가:

```
{라운드}	{기능명}	{keep/revert}	{passed_tests}	{변경파일수}	{커밋해시 또는 -}
```

## Constraints

- 기존 테스트를 깨뜨리는 변경 금지
- 외부 패키지 추가 금지 (requirements.txt, package.json 수정 금지)
- 라운드당 변경/생성 파일 합계 3개 이내
- 이전 라운드와 동일한 기능 중복 구현 금지
- 하드코딩된 API 키/시크릿 금지
- 사용자 확인 없이 기존 데이터 삭제/변경 금지

## Success Criteria

- [ ] 10라운드 전체 완료
- [ ] keep 비율 70% 이상 (7/10)
- [ ] 베이스라인 테스트 수(3399) 유지 또는 증가
- [ ] progress.tsv에 10줄 기록 완료
- [ ] 각 keep된 라운드마다 git commit 존재
