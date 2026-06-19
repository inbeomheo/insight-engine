# 연구 디렉티브 — Lighthouse 성능/SEO 최적화

## 도메인
Insight Engine 프론트엔드 (Next.js 16 + React 19 + Tailwind v4) 의 Lighthouse 성능/SEO 최적화.

## 목표
복합 점수(composite_score)를 최대화한다. (방향: 높을수록 좋음, 100점 만점)
- 복합 점수 = `performance*0.4 + seo*0.4 + bundle_score*0.2`
- 측정: `python autoresearch-lighthouse/eval/benchmark.py`
- 상세: `autoresearch-lighthouse/eval/prepare.py` (이 파일은 수정 금지)

## 수정 가능 영역 (target)
**`frontend/` 디렉토리 내** 만 수정 가능:
- `frontend/app/` (layout, page, globals.css 등)
- `frontend/components/` (ResultCard, UrlInput, Header 등)
- `frontend/lib/` (api.ts 등 — 단 기능 변경 금지, 번들 영향만)
- `frontend/next.config.ts`
- `frontend/public/` (아이콘, 매니페스트)

## 수정 금지 영역 (절대 건드리지 말 것)
- Python 백엔드 전체 (`app.py`, `routes/`, `services/`, `config.py`, ...)
- `autoresearch-lighthouse/eval/`, `autoresearch-lighthouse/meta_eval/` (측정 코드 자체 — 고쳐서 점수 올리면 부정행위)
- 다른 autoresearch 디렉토리 (`autoresearch/`, `autoresearch-completeness/`)
- `frontend/` 의 **기능/동작 변경** (UI 동작·API 호출은 그대로 유지, 성능/SEO만 개선)
- `prepare.py` 의 번들 점수 매핑·측정 로직

## 시간 예산
실험 1회당 최대 ~1500초 (빌드 + lighthouse 3회). 실측 ~3분.

## 제약 조건
- **빌드(`npm run build`)가 반드시 성공**해야 함 — 실패 시 즉시 revert.
- **hydration 에러 회피** (기존 UX 세션 학습): 항상 렌더되는 컴포넌트의 className/태그/속성 변경은 SSR 불일치를 유발. 조건부 렌더링 블록 내부, 또는 useEffect 이후에만 마운트되는 부분을 우선 수정. SSR 시점에 결정되는 값(날짜·랜덤·window) 변경 금지.
- 기존 UI 동작·접근성(ARIA)·기능을 퇴보시키면 안 됨.
- 외부 패키지 추가 금지 (이미 devDep에 lighthouse 있음).

## 실험 실행 방법
1. `frontend/` 내 파일 수정 — **한 번에 하나의 가설**(아래 힌트 참조)
2. `python autoresearch-lighthouse/eval/benchmark.py` 실행
3. 출력에서 `composite_score:` 뒤의 숫자를 읽음
4. 이전 최고 기록보다 **높으면 keep(git commit)**, 같거나 낮으면 **revert(git reset)**
5. `inner_results.tsv` 에 기록
6. 다음 가설로 → 1로 (NEVER STOP)

## keep/revert 판정
- `composite_score` 가 이전 최고보다 **0.3점 이상** 높으면 keep (측정 노이즈 마진)
- 0.3점 미만 차이거나 하락이면 revert
- 빌드 실패·hydration 에러·런타임 크래시 → 즉시 revert

## 최적화 힌트 (성능 카테고리 우선 — 보통 가장 큰 이득)

### 번들 크기 / LCP (bundle_score + performance 동시 개선)
1. 무거운 컴포넌트 `next/dynamic` / `React.lazy` 로 코드분할 (이미 ResultCard 서브컴포넌트에 적용됨 — 다른 무거운 것 확인)
2. `next.config.ts` 의 `experimental.optimizePackageImports` 에 미사용/대형 라이브러리 추가 (lucide-react, date 라이브러리 등)
3. 미사용 import / dead code 제거
4. 큰 정적 에셋(이미지·폰트) 최적화, `next/image` 사용 여부 점검
5. 클라이언트 컴포넌트(`"use client"`) 범위 축소 — 서버 컴포넌트 기본 유지

### SEO 카테고리
1. `app/layout.tsx` 의 metadata(title, description, meta robots, canonical)
2. Open Graph / Twitter card 메타태그
3. `robots.txt`, `sitemap.xml` (`app/robots.ts`, `app/sitemap.ts`)
4. heading 위계(h1 단일, h2/h3 구조), lang 속성, alt 텍스트
5. `<html lang="ko">` 명시

### 렌더링 / CLS / INP
1. 폰트 로딩 최적화 (Pretendard 비동기 — layout shift 점검)
2. 이미지 width/height 명시로 CLS 방지
3. `loading="lazy"` on below-fold 미디어
4. 불필요한 폴리필/클라이언트 JS 제거

## NEVER STOP
루프가 시작되면 사용자가 수동 중단할 때까지 절대 멈추지 않는다.
아이디어가 고갈되면:
- 성능 점수의 하위 항목(LCP/CLS/INP/TBT) 상세를 prepare.py 보조 출력에서 확인 후 집중
- 번들 구조 분석(어떤 청크가 큰가) 후 타겟팅
- 이전 near-miss 변경들을 조합
- 더 급진적 접근(페이지 분할, 동적 임포트 재구성)
