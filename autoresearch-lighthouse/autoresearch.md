# autoresearch.md — Lighthouse 모바일 성능/SEO + first-load JS

## 도메인
Insight Engine 프론트엔드 (Next.js 16 + Turbopack + React 19) Lighthouse 최적화

## 메트릭
composite_score = performance*0.4 + seo*0.4 + bundle_score*0.2 (higher_is_better, 100점)
- performance/seo: lighthouse MOBILE 3회 median (매우 안정적)
- bundle_score: first-load JS KB. 100KB=100점, 700KB=0점 선형

## 베이스라인 (E000, keep)
- composite **68.32** = perf 55 / seo 100 / first_load 510.5KB(bundle_score 31.58)

## first-load 구성 분석 (rootMainFiles)
- 219KB framework(react-dom) / 116KB Next / 110KB framework-공통 = **~330KB 고정(framework)**
- 32+23KB 앱 인프라 / 10KB turbopack = ~65KB
- → framework가 대부분, 앱 코드 감소분은 제한적. 성능(55) 개선이 복합 점수에 더 큰 레버(가중치 0.4)

## 측정 명령
`python C:/Users/qlqla/.claude/skills/autoresearch/scripts/loop_runner.py ./autoresearch-lighthouse . '<desc>'`
(내부적으로 benchmark.py → prepare.py: 빌드→first-load→next start→lighthouse mobile 3회→composite)

## 수정 대상 / 금지
- 수정: `frontend/` (app/, components/, lib/, next.config.ts, public/)
- 금지: Python 백엔드 / eval/ / meta_eval/ / prepare.py / 다른 autoresearch 디렉토리 / 기능 변경 / push

## Outer Loop 상태
- 현재 라운드: 1 진행 중
- 최고 composite_score: 68.32 (베이스라인)
- 전략: first-load 앱 코드 감소 + 모바일 성능(LCP/CLS/TBT) 동시 타격

## 라운드별 기록
| 라운드 | 전략 | Inner 회수 | 최종점수 | 수렴회차 | outer_score |
|--------|------|-----------|---------|---------|-------------|
| 1 | first-load 분리 시도 | 1 | - | - | - |

## Inner Loop 이력
| ID | 가설 | composite | 상태 |
|----|------|-----------|------|
| E000 | BASELINE | 68.32 | keep |
| E002 | Toaster(sonner) dynamic import | 68.32 | revert (first-load 영향 0 — sonner 미미) |

## 학습 노트
- sonner(Toaster)는 first-load에 유의미 기여 안 함 (이미 작음). 클라이언트 Provider의 작은 의존성 dynamic化는 효과 없음.
- 큰 framework 청크(219/116/110KB)는 줄일 수 없음. 남은 레버는 앱 코드 + 성능(LCP/CLS/TBT).
- 수동 분석 패턴: `python -c`로 build-manifest rootMainFiles 청크 크기 확인 (위 표 참조).

## 다음 가질 후보 (우선순위)
1. **`/` page.tsx에서 ResultCard 체인 dynamic** — ResultCard가 직접 import면 first-load 앱 코드 큰 덩어리. 단, 서브컴포넌트는 이미 dynamic이므로 ResultCard 껍데기만 남을 수도 (사전 확인 필요)
2. **viewport `userScalable:false` 제거** — 접근성(perf 아님)이나 보조
3. **성능 audits 기반**: prepare.py 부가 출력이 없으므로, lighthouse JSON 수동 1회 실행해 LCP/CLS/INP/TBT + opportunities 추출 → 병목 타겟팅
4. 미사용 의존성/직접 import 중 무거운 것 (katex/mermaid는 이미 dynamic 확인)
5. next.config `optimizePackageImports` 확장 (date-fns, recharts 등 사용 시)

## NEVER STOP
사용자가 /loop 자율로 인계. 매 라운드: autoresearch.md/inner_results.tsv 읽어 상태 파악 → 가질 1개 → loop_runner 측정 → keep(commit)/revert(checkout) → 본 파일 갱신.
아이디어 고갈 시: lighthouse audits 수동 추출로 새 병목 발구, 또는 near-miss 가질 조합.
