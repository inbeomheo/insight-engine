# [Dep-7] SEO/GEO 스타일 + services/seo 정리 — 분할 계획

> 작성일: 2026-07-05 (docs/dep7-seo-geo-split-plan 브랜치, 워크트리 `ie-wt-c31b`)
> 이 문서는 **분석 산출물**이다. 코드 변경 없음, 실제 제거는 이 계획을 지휘자가 검토한 뒤
> 별도 사이클(코드 diff 포함)에서 배치별로 수행한다.
> 상위 기준: `plans/product-vision-2026-07.md` — "발행/SEO/캠페인 계열은 단계적(UI 노출 하향 →
> deprecated 마크 → 코드 제거) 정리 대상"이자 "코드 제거는 루프 정규 트랙, [사람] 게이트는
> 사용자 데이터/DB 스키마·외부 서비스 해지에만 유지".
> 선행 문서: `plans/dead-code-audit-2026-06-10.md` (감사 대장 포맷), CLAUDE.md의
> "dead-code 제거 batch 1~5" 원장(배치당 ≤40파일 캐스케이드, "만든 자 ≠ 검사하는 자" 재검증 원칙).

## 0. 측정 요약 (grep 근거 기반, 추측 없음)

- **`services/seo/` 총 파일 수: 27개** (`.py` 27개, 그 중 `__init__.py` 1개 + 실서비스 26개 —
  `find services/seo -type f -name "*.py" ! -name "__init__.py" | wc -l` → 26로 재확인).
  `find services/seo -type f -name "*.py" | wc -l` → 27, `find services/seo -type f | wc -l` → 27
  (비-`.py` 파일 없음, 전량 소스코드).
- 이 중 **테스트 전용 참조**(운영 코드 소비자 0)로 확인된 파일: **24개**
  (실서비스 26개 중 `search_service`, `seo_metadata_service` 2개만 활성 소비자 보유 —
  자세한 파일별 판정은 §1 표 참조).
- **verdict 집계**: 학습축 사용 0 / SEO 전용-활성 소비자 있음(판단 필요) 4 / 순수 제거 후보(테스트만) 24
  / `__init__.py`(빈 패키지 마커, 판정 제외) 1
  = 27개 전량 커버.
- **놀라운 발견 4가지** (아래 §5, §6에서 상술):
  1. `agent/tools/seo_tools.py`가 `services/seo/` 디렉토리 전체를 `pkgutil.iter_modules`로 스캔해
     모듈당 **첫 번째** public 함수만(`for` 루프 내 `break` 존재, 46번째 줄) MCP 에이전트 도구로
     자동 등록한다 — 즉 "직접 import하는 routes/services가 없다"는 grep 결과만으로는 죽은 코드로
     단정할 수 없다. 단, 이 스캔이 실행되려면 `AGENT_MODE_ENABLED=true`(기본 `false`)가 필요하고,
     이 기능을 노출하려던 것으로 보이는 프론트 컴포넌트 `frontend/components/agent/AgentPipeline.tsx`는
     `/api/agent/pipeline`(존재하지 않는 엔드포인트)을 호출하며 그 자체가 앱 어디서도 import되지
     않는 고아 컴포넌트다 (증거: §1 하단, §6).
  2. `services/seo/search_service.py`의 `index_content()`(검색 인덱스에 콘텐츠 등록)는
     **호출하는 곳이 프로덕션 코드에 전혀 없다**. `/api/search` 라우트 자체는 살아있게 등록돼
     있으나, 그 유일한 프론트 소비자로 지목했던 `GlobalSearch.tsx`도 **재검증 결과 고아
     컴포넌트**(어디서도 import되지 않음)임을 확인 — 즉 `search_service.py`는 "고장난 활성
     기능"이 아니라 **라우트만 등록돼 있고 UI 진입점이 전혀 없는 완전히 죽은 체인**이다
     (증거: §1 `search_service` 행, §0-2 최초 판단 정정).
  3. `frontend/components/result/ScoreCard.tsx`(`seo` 점수 필드 포함)도 고아 컴포넌트지만, 그 백엔드
     라우트 `/api/content-score`(`routes/advanced_routes.py:517`)는 `services/quality/quality_service.py`를
     쓰지 `services/seo/`를 전혀 참조하지 않는다 — SEO처럼 보이지만 이 정리 범위 밖 (증거: §5 가드 리스트).
  4. `agent/` 레이어에 batch-A 대상 모듈의 도구 이름을 하드코딩 참조하는 잔재가 있다:
     `agent/prompts/roles.py:106-118`의 `SEO_PROMPT`가 `analyze_search_intent`/`analyze_eeat`/
     `analyze_aeo`/`analyze_serp_features`/`find_link_opportunities`/`cluster_contents`를 프롬프트
     텍스트에 나열하고, `agent/core.py:32`의 `PARALLEL_SAFE_TOOLS`에 `check_keyword_density`가
     들어있다. 두 곳 모두 `registry`에서 도구를 찾지 못하면 조용히 미스만 나는 구조라 배치 A
     실행 자체를 막지는 않지만, 문서화되지 않은 채 방치하면 다음 정리에서 다시 헷갈릴 수 있어
     배치 A의 "함께 확인할 것"에 포함한다.

## 1. 인벤토리 — `services/seo/` 27개 파일 전수 조사

범례: **[학습축 사용]** 학습 엔진 파이프라인(생성/추출/에이전트/검색)에서 실사용,
**[SEO 전용-제거 후보]** 테스트 외 프로덕션 소비자 0, **[판단 필요]** 활성 소비자 있으나
SEO/발행 계열이라 사용자 결정 필요.

| # | 파일 | 역할(1줄) | 소비자(grep 근거) | 판정 |
|---|------|-----------|-------------------|------|
| 1 | `__init__.py` | 패키지 마커(빈 docstring) | — | 판정 대상 아님(패키지 자체) |
| 2 | `aeo_optimizer_service.py` | AI Answer Engine 최적화(직답 구조 점수) | `tests/test_aeo_optimizer_service.py`만. routes/services cross-import 0 (`grep -rln "aeo_optimizer" --include=*.py .` → 테스트 파일만) | [SEO 전용-제거 후보] |
| 3 | `anchor_text_service.py` | 앵커 텍스트 품질 감사 | `tests/test_anchor_text_service.py`만 | [SEO 전용-제거 후보] |
| 4 | `cannibalization_service.py` | 콘텐츠 카니발리제이션(주제 중복) 감지 | `tests/test_cannibalization_service.py`만 | [SEO 전용-제거 후보] |
| 5 | `competitor_analysis_service.py` | 경쟁 콘텐츠 스크레이핑+분석 (`services.data.web_scraper_service`, `services.data.auto_tag_service`를 내부에서 import했음 — 이후 `auto_tag_service`는 별도 데드코드 배치에서 제거됨) | `tests/test_competitor_analysis_service.py`만 | [SEO 전용-제거 후보] |
| 6 | `content_freshness_indicator_service.py` | 콘텐츠 최신성 지표 계산 | `tests/test_content_freshness_indicator_service.py`만 | [SEO 전용-제거 후보] |
| 7 | `content_performance_predictor_service.py` | 규칙 기반 성과(조회/공유/참여) 예측 | `tests/test_content_performance_predictor_service.py`만 | [SEO 전용-제거 후보] |
| 8 | `cta_optimizer_service.py` | CTA 문구 분석/추천 | `tests/test_cta_optimizer_service.py`만 | [SEO 전용-제거 후보] |
| 9 | `eeat_analyzer_service.py` | E-E-A-T 신뢰 신호 분석 | `tests/test_eeat_analyzer_service.py`만 | [SEO 전용-제거 후보] |
| 10 | `engagement_scorer_service.py` | 콘텐츠 참여도 점수 | `tests/test_engagement_scorer_service.py`만 | [SEO 전용-제거 후보] |
| 11 | `entity_coverage_service.py` | 엔티티 커버리지 분석 | `tests/test_entity_coverage_service.py`만 | [SEO 전용-제거 후보] |
| 12 | `freshness_monitor_service.py` | 콘텐츠 신선도 모니터링(위험도) | `tests/test_freshness_monitor_service.py`만 | [SEO 전용-제거 후보] |
| 13 | `headline_optimizer_service.py` | 헤드라인 점수/최적화 제안 | `tests/test_headline_optimizer_service.py`만 | [SEO 전용-제거 후보] |
| 14 | `image_seo_auditor_service.py` | 이미지 alt/파일명 SEO 감사 | `tests/test_image_seo_auditor_service.py`만 | [SEO 전용-제거 후보] |
| 15 | `internal_link_service.py` | 내부 링크 기회 탐지 (다건 콘텐츠 인덱싱 `_index_contents`) | `tests/test_internal_link_service.py`만. `find_link_opportunities` 호출자 0 | [SEO 전용-제거 후보] |
| 16 | `keyword_density_service.py` | 키워드 밀도 분석 | `tests/test_keyword_density_service.py`만 | [SEO 전용-제거 후보] |
| 17 | `keyword_stuffing_detector_service.py` | 키워드 스터핑 감지 | `tests/test_keyword_stuffing_detector_service.py`만 | [SEO 전용-제거 후보] |
| 18 | `meta_description_quality_service.py` | 메타 설명 품질 체크 | `tests/test_meta_description_quality_service.py`만 | [SEO 전용-제거 후보] |
| 19 | `schema_opportunity_service.py` | Schema.org 적용 기회 탐지(FAQ/HowTo/Article) | `tests/test_schema_opportunity_service.py`만 | [SEO 전용-제거 후보] |
| 20 | `search_intent_service.py` | 검색 의도 적합도(Search Intent Matcher) 분석 | `tests/test_search_intent_service.py`만 | [SEO 전용-제거 후보] |
| 21 | `search_service.py` | 인메모리 콘텐츠 검색(`index_content`/`remove_from_index`/`search`) | **`search()`**: `routes/integrations/content_workspace.py:84` (`/api/search` GET, `app.py` → `routes.integration_routes` → `routes.integrations.__init__` → `content_workspace` 체인으로 등록). 라우트의 유일한 후보 프론트 소비자였던 `frontend/components/search/GlobalSearch.tsx:44`(`fetch(apiUrl('/api/search?q=...'))`)를 재검증한 결과 **`grep -rn "GlobalSearch" frontend --include=*.tsx --include=*.ts`가 정의 파일 자신만 매치 — 이 컴포넌트를 import하는 곳이 앱 어디에도 없는 고아**임을 확인. **`index_content()`/`remove_from_index()`**: 호출자 0건(`grep -rn "index_content\|remove_from_index" --include=*.py .` → 정의부 + `internal_link_service.py`의 무관한 동명 지역함수 `_index_contents`뿐, 실제 등록 훅 없음). 종합: 라우트는 등록돼 있으나 인덱스도 채워지지 않고 UI 진입점도 없는 완전히 죽은 체인 | [판단 필요] — 코드상 죽은 체인이지만 `/api/search` 라우트 자체의 제거 여부는 [사람] 판단(§3) |
| 22 | `seo_metadata_service.py` | GEO/SEO JSON-LD 구조화 데이터 생성(`generate_video_object_schema`/`generate_faq_page_schema`/`generate_article_schema`/`generate_all_schemas`) | `routes/generation_helpers.py:713`(`generate_all_schemas`, `geo_seo` 스타일 응답의 `json_ld_schemas` 생성) + `services/agents/seo_agent.py:104`(`generate_video_object_schema`, 멀티에이전트 파이프라인 4단계) | [판단 필요] — `geo_seo` 스타일 응답 필드 + 에이전트 파이프라인 직결, 스타일 존치 여부에 종속 |
| 23 | `serp_feature_service.py` | SERP 피처(스니펫/PAA/리스트/표 등) 노출 가능성 분석 | `tests/test_serp_feature_service.py`만 | [SEO 전용-제거 후보] |
| 24 | `title_tag_length_service.py` | 타이틀 태그 길이 체크 | `tests/test_title_tag_length_service.py`만 | [SEO 전용-제거 후보] |
| 25 | `topic_cluster_service.py` | TF-IDF 기반 토픽 클러스터링 | `tests/test_topic_cluster_service.py`만 | [SEO 전용-제거 후보] |
| 26 | `topic_gap_service.py` | 토픽 갭 분석(질문/구조 갭 탐지) | `tests/test_topic_gap_service.py`만 | [SEO 전용-제거 후보] |
| 27 | `url_health_checker_service.py` | 콘텐츠 내 URL 헬스 체크 | `tests/test_url_health_checker_service.py`만 | [SEO 전용-제거 후보] |

**pkgutil 동적 로딩 보정 사항 (표 전체에 적용)**: 위 24개(#2-#20, #23-#27 — `search_service`(#21)·
`seo_metadata_service`(#22) 제외) "제거 후보" 판정은 *직접 import* 기준이다.
`agent/tools/seo_tools.py`(`_SERVICE_DIR = .../services/seo`)가 `pkgutil.iter_modules`로 이
디렉토리 전체를 스캔해 **모듈당 첫 번째** public 함수(정확히는 `inspect.getmembers`로 얻은 목록의
첫 항목 — 47번째 줄의 `for name, fn in inspect.getmembers(mod, inspect.isfunction):` 루프가
46번째 줄 `break`로 1회만 돌고 종료)를 자동으로 `registry.register(toolset="seo", ...)` 하므로,
24개 전부가 "MCP 에이전트 도구" 후보군의 멤버라는 점은 동일하게 적용된다(다만 모듈당 함수 1개만).
다만 이 스캔 경로 자체가 사실상 죽어있음을 아래에서 확인했다(§6). 따라서 pkgutil 자동등록을
"활성 소비"로 카운트하지 않고 [SEO 전용-제거 후보]로 유지하되, 배치 실행 시 반드시 재확인할
것(§4 검증 기준에 포함).

### `services/agents/seo_agent.py` / `seo_optimize_agent.py` (services/seo/ 밖이지만 직결)

- `services/agents/seo_agent.py` — `SEOAgent`: 멀티에이전트 파이프라인(`Research → Writer → Editor → SEO`)
  4단계 고정 스텝. `services/agents/orchestrator.py:18,42,130-139`에서 무조건 실행(스타일 무관, `agent_mode=true`일 때).
  `routes/blog_routes.py:678-690`에서 `agent_mode` 요청 시 `Orchestrator().run()` 호출 — **활성 경로**.
  프론트 `frontend/hooks/useGenerate.ts:221`가 `agent_mode: enableAgentMode`를 요청 바디에 실어 보내고,
  `enableAgentMode` 토글은 `frontend/app/page.tsx`에 실존(증거: `grep -rln "enableAgentMode" frontend/`).
  → **[판단 필요]**: SEO 전용 기능이 아니라 "에이전트 모드" 전체의 고정 4단계라 스타일과 무관하게
  걸려있음. 제거하려면 오케스트레이터를 3단계(Research→Writer→Editor)로 재설계해야 하며 이는
  Dep-7 범위를 넘어서는 별도 작업(§5 가드 리스트).
- `services/agents/seo_optimize_agent.py` — `optimize_seo()`: 이미 생성된 콘텐츠의 SEO 점수/제안.
  `routes/utility/feedback_quality.py:63`(`/api/seo-optimize`)에서 호출하는 라우트는 등록돼 있으나,
  프론트 `frontend/lib/api.ts:780`의 `seoOptimize()` 래퍼 함수는 **어떤 컴포넌트에서도 호출되지
  않는다**(`grep -rln "seoOptimize" frontend/components frontend/app frontend/hooks` → 0건,
  `api.ts` 정의부만 매치). → **[SEO 전용-제거 후보]**: 라우트+서비스+API래퍼 3단 모두 죽은 체인.

## 2. 스타일/파서 계약 지도 — `blog_seo` + `geo_seo`

CLAUDE.md의 "파서 계약: blog_seo 메타 테이블 행 / FAQ / 해시태그, geo_seo의 한 줄 정의 / 구조화
데이터 표 / 엔티티 태그 / 팩트 / CTA는 `services/core/ai_metadata.py` 정규식과 1:1" 경고에
해당하는 전체 체인을 추적한다.

### blog_seo

- 프롬프트: `prompts/styles/blog_seo.py` → `STYLE_PROMPTS['blog_seo']` (`prompts/styles/__init__.py`)
- config: `config.py:310` `STYLE_OPTIONS`에 `('blog_seo', '🔍 블로그+SEO')`,
  `config.py:166` `STYLE_TEMPERATURE['blog_seo'] = 0.7`
- frontend: `frontend/lib/constants.ts:4` `{ id: 'blog_seo', label: '블로그+SEO', emoji: '🔍', ... }`
- 파서: `services/core/ai_metadata.py`
  - `extract_seo_metadata(content)` — meta 설명/키워드/추천 URL 테이블 파싱, `routes/blog_routes.py`·
    `services/core/ai_service.py`·`services/core/pipeline_service.py`에서 호출(`grep -rln
    "extract_seo_metadata" --include=*.py .`로 확인, `services/seo/`가 아니라 `services/core/`에 위치)
  - `extract_faq_schema(content)` — `**Q.**`/`A.` 파싱 → FAQPage JSON-LD. `routes/generation_helpers.py:702`에서
    `params['style'] in ('blog_seo', 'geo_seo')`일 때만 호출
  - `build_faqpage_schema(qa_pairs)` — `extract_faq_schema` 내부 헬퍼
- 응답 필드: `{"seo": {...}}` → 프론트 `frontend/components/result/SeoSection.tsx`가 소비,
  `ResultCard.tsx:914` `{report.seo && <SeoSection seo={report.seo} />}`로 실제 렌더 (dynamic import,
  `ResultCard.tsx:41`)
- **services/seo/ 연결**: 없음. blog_seo는 `services/core/ai_metadata.py`(정규식 파서)만 사용하고
  `services/seo/` 디렉토리의 26개 서비스는 blog_seo 응답 생성 경로에 전혀 관여하지 않는다
  (`services/seo/seo_metadata_service.py`는 geo_seo 전용, §1 #22 참조).

### geo_seo

- 프롬프트: `prompts/styles/geo_seo.py` → `STYLE_PROMPTS['geo_seo']`
- config: `config.py:322` `('geo_seo', '🤖 GEO (AI검색)')`,
  `config.py:165` `STYLE_TEMPERATURE['geo_seo'] = 0.4`
- frontend: `frontend/lib/constants.ts:16` `{ id: 'geo_seo', label: 'GEO 검색', emoji: '🤖', ... }`
- 파서: `services/core/ai_metadata.py`
  - `extract_geo_metadata(content)` — 한 줄 정의/구조화 데이터 표/엔티티 태그/`- ✓` 팩트 파싱
  - `extract_faq_schema(content)` — blog_seo와 공유
  - `extract_cta(content)` — `CTA_PRIMARY`/`SECONDARY` 파싱, `geo_seo`에서만 호출
    (`routes/generation_helpers.py:707` `if params['style'] == 'geo_seo'`)
- **services/seo/ 연결(유일하게 실사용)**: `routes/generation_helpers.py:713`에서
  `from services.seo.seo_metadata_service import generate_all_schemas` — geo_seo 스타일에서만
  JSON-LD 스키마(`json_ld_schemas` 응답 필드)를 생성. `services/agents/seo_agent.py:104`도
  같은 모듈의 `generate_video_object_schema`를 에이전트 모드 4단계에서 호출(스타일 무관, §1 참조)
- 응답 필드: `{"geo": {...}, "cta": {...}, "json_ld_schemas": {...}}` → 프론트
  `frontend/components/result/GeoSection.tsx`가 소비, `ResultCard.tsx:917-922`에서
  `{report.geo && <GeoSection geo={report.geo} cta={report.cta} json_ld_schemas={report.json_ld_schemas} />}`로 실제 렌더

### 무엇이 깨지는가 (제거 시나리오별)

1. **`services/seo/` 24개(§1 [SEO 전용-제거 후보])만 제거**: blog_seo/geo_seo 응답에 영향 없음
   (둘 다 이 24개를 참조하지 않음). agent toolset "seo"의 pkgutil 자동등록 대상이 없어지지만
   그 경로 자체가 비활성(§6)이라 런타임 영향 없음. **이 배치는 스타일 시스템과 독립적으로 안전**.
2. **`services/seo/seo_metadata_service.py` 제거**: `geo_seo` 응답의 `json_ld_schemas` 필드가
   사라짐(`generation_helpers.py:713` 호출부도 함께 제거해야 함) + 에이전트 모드의 `SEOAgent.json_ld`가
   항상 빈 dict가 됨(`seo_agent.py:104` try/except가 `ImportError`를 잡아 폴백하므로 크래시는 없지만
   기능 손실). `GeoSection.tsx`의 `json_ld_schemas` prop 렌더 분기도 항상 no-op이 됨 — **함께
   정리해야 할 목록**: `generation_helpers.py`의 json_ld 블록, `seo_agent.py`의 try 블록,
   `GeoSection.tsx`의 `json_ld_schemas` prop, `frontend/lib/types/api.ts`의 대응 타입.
3. **`blog_seo`/`geo_seo` 스타일 자체를 제거**: `config.STYLE_OPTIONS`/`STYLE_TEMPERATURE`,
   `frontend/lib/constants.ts`, `prompts/styles/__init__.py`의 `STYLE_PROMPTS` 등록, `ai_metadata.py`의
   4개 extract 함수 전부(다른 스타일이 안 쓰므로 고아화), `SeoSection.tsx`/`GeoSection.tsx`
   컴포넌트, `ResultCard.tsx`의 조건부 렌더 블록, `services/seo/seo_metadata_service.py`,
   `services/agents/seo_agent.py`의 JSON-LD 호출부(SEOAgent 자체는 존치 가능 — 메타 title/description/faq는
   스타일 무관 필드이므로) 전부를 **한 번에** 손대야 파서 계약 불일치가 남지 않는다.
   이것은 **15개 스타일 그리드에서 사용자 노출 기능을 제거하는 제품 결정**이므로 §3에서 별도 취급.

## 3. [사람] 제품 결정 플래그

이 정리는 두 층위가 섞여 있다. **혼동하지 말 것**:

### 지금 바로 제거 가능 (순수 죽은 코드, 제품 결정 불요)

- §1의 **24개 [SEO 전용-제거 후보]** 서비스 파일 + 전용 테스트 24개
- `services/agents/seo_optimize_agent.py` + `routes/utility/feedback_quality.py`의 `/api/seo-optimize`
  라우트 + `frontend/lib/api.ts`의 `seoOptimize()`/`SeoOptimizeResponse` (3단 모두 고아, §1 하단)
- 근거: blog_seo/geo_seo 응답 생성 경로도, 15개 스타일 UI 그리드도, 에이전트 파이프라인의
  필수 스텝도 아니다 — 순수하게 테스트만 참조하는 미사용 코드

### 사용자 결정 필요 (user-visible 기능 제거 여부)

- **`services/seo/search_service.py` 처리 방향** — 재검증 결과 `/api/search` 라우트는 등록돼
  있지만 (a) 인덱스를 채우는 `index_content()` 호출자가 없고 (b) 유일한 프론트 소비자로 지목했던
  `GlobalSearch.tsx`도 고아 컴포넌트임을 확인(§0-2) — 즉 "사용자가 오늘 쓸 수 있는 기능"이 아니라
  **라우트만 등록된 완전히 죽은 체인**이다. 그럼에도 [사람] 플래그를 유지하는 이유는 라우트
  삭제 자체가 (드물게) 외부에서 직접 `/api/search`를 호출하는 통합/스크립트가 있을 가능성을
  배제 못 하기 때문 — 옵션 A) `index_content` 훅을 실제로 연결해 기능을 고쳐 살린다(범위 확장,
  Dep-7 밖) 옵션 B) 죽은 체인이므로 `/api/search` + `search_service.py` + `GlobalSearch.tsx`를
  함께 제거한다 옵션 C) 이번 배치에서는 손대지 않고 별도 버그 티켓으로 분리.
  → **[사람]에게 옵션 선택 요청**. 죽은 코드라는 근거가 명확하므로 옵션 B를 권고하되 결정은
  위임하지 않음.
- **`blog_seo`/`geo_seo` 스타일을 15개 UI 그리드에서 제거할지 여부** — 제품 비전 문서가
  "발행/SEO/캠페인 계열은 단계적 정리 대상"이라고 명시하지만, 이 두 스타일은 여전히 사용자가
  선택 가능한 활성 콘텐츠 생성 옵션이다. 코드 정리(§1의 24개)와 달리 **사용자가 오늘 쓸 수 있는
  기능을 끄는 결정**이므로, 다음 중 사용자 선택이 필요: 1) 유지(SEO 메타데이터는 학습 노트의
  "출처 신뢰도/구조화" 관점에서도 유용할 수 있음) 2) UI 노출만 하향(그리드에서 숨기되 코드는
  존치 — 제품 비전의 "단계적" 1단계) 3) 완전 제거(스타일+파서+services/seo/seo_metadata_service.py+
  프론트 섹션 전부). **본 문서는 3)을 일방적으로 권고하지 않는다.**
- **`services/agents/seo_agent.py`(에이전트 모드 4단계) 존치 여부** — `agent_mode` 토글 자체가
  살아있는 기능이라 SEOAgent를 빼려면 오케스트레이터 재설계(3단계로 축소하거나 SEO 스텝을
  optional로 전환)가 필요. Dep-7의 "services/seo 정리"와는 결이 다른 별도 작업 — [사람]에게
  이번 배치 포함 여부 확인 필요.

## 4. 배치 분할 제안

각 배치 ≤40파일 캐스케이드(CLAUDE.md 원장 관례 준수), 배치 간 의존성 명시.

### 배치 A — 순수 고아 SEO 분석 서비스 24종 제거 (제품 결정 불요, 즉시 실행 가능)

- 대상: §1의 24개 [SEO 전용-제거 후보] `services/seo/*_service.py` + 전용 테스트 24개
  (`tests/test_{aeo_optimizer,anchor_text,cannibalization,competitor_analysis,
  content_freshness_indicator,content_performance_predictor,cta_optimizer,eeat_analyzer,
  engagement_scorer,entity_coverage,freshness_monitor,headline_optimizer,image_seo_auditor,
  internal_link,keyword_density,keyword_stuffing_detector,meta_description_quality,
  schema_opportunity,search_intent,serp_feature,title_tag_length,topic_cluster,topic_gap,
  url_health_checker}_service.py`)
  = 파일 **48개** (24 서비스 + 24 테스트) — 단일 배치로 40 상한을 **8개 초과**하므로 실무에서는
  A1(서비스 24개 삭제 커밋)·A2(테스트 24개 삭제 커밋)로 세분(각 24개, 40 상한 내)하는 것을
  권장하되, 과거 batch 3/5 사례처럼 "제거 대상 목록"만 40 상한 기준이라면 48 그대로도 무방(과거
  batch 5는 서비스+프론트+테스트 합산 46파일 이상을 한 배치로 처리한 전례 있음, CLAUDE.md 참조)
  — 지휘자 재량. 단, A1/A2로 나누더라도 24+24=48이라는 총량 자체는 변하지 않으므로 40 상한을
  "지킨다"고 보고할 때는 분할 기준(파일당 vs PR당)을 명확히 밝힐 것.
- 함께 확인할 것:
  1. `services/seo/__init__.py`에 이 24개를 재export하는 코드가 있는지
     (`cat services/seo/__init__.py` → 현재 빈 docstring만, 재export 없음 — 삭제 시 `__init__.py`
     수정 불필요)
  2. `agent/prompts/roles.py:106-118`의 `SEO_PROMPT` — `analyze_search_intent`(search_intent_service),
     `analyze_eeat`(eeat_analyzer_service), `analyze_aeo`(aeo_optimizer_service),
     `analyze_serp_features`(serp_feature_service), `find_link_opportunities`(internal_link_service),
     `cluster_contents`(topic_cluster_service) 6개 도구 이름이 이 배치 삭제 대상 모듈의 함수를
     프롬프트 텍스트로 하드코딩 참조한다. 삭제 후 `registry`에서 이 이름들을 찾지 못해도
     크래시는 나지 않지만(단순 미등록), 에이전트가 존재하지 않는 도구를 호출 시도하게 되는
     프롬프트 불일치가 남는다 — 이 배치 실행 시 해당 문구를 수정하거나(권장) 최소한 "실제 도구
     목록과 어긋남"을 코드 주석/커밋 메시지로 명시할 것
  3. `agent/core.py:32`의 `PARALLEL_SAFE_TOOLS`에 `check_keyword_density`(keyword_density_service
     계열 추정 이름)가 포함돼 있음 — 동일하게 registry 미스만 발생, 삭제 시 이 항목도 정리하거나
     문서화할 것
- 의존성: 없음(배치 B/C와 독립). 가장 먼저 실행 가능.
- 검증 기준:
  1. `python -m pytest tests/ -v` — 0 fail (삭제된 24개 테스트 자체는 함께 삭제되므로 수집 대상에서 제외)
  2. 삭제 후 `grep -rln "services\.seo\.\(aeo_optimizer\|anchor_text\|cannibalization\|competitor_analysis\|content_freshness_indicator\|content_performance_predictor\|cta_optimizer\|eeat_analyzer\|engagement_scorer\|entity_coverage\|freshness_monitor\|headline_optimizer\|image_seo_auditor\|internal_link\|keyword_density\|keyword_stuffing_detector\|meta_description_quality\|schema_opportunity\|search_intent\|serp_feature\|title_tag_length\|topic_cluster\|topic_gap\|url_health_checker\)" --include="*.py" .` → 0건
  3. `cd frontend && npx tsc --noEmit` — 0 error (이 배치는 프론트 무관이라 원래도 무영향 확인용)
  4. agent toolset 재확인: `AGENT_MODE_ENABLED=true`로 앱 기동 후 `discover_tools()` 로그에서
     이전 대비 등록 도구 수 감소만 확인(에러 없이 스킵되는지) — `agent/tools/seo_tools.py`의
     `pkgutil.iter_modules` 루프가 존재하지 않는 모듈을 참조하지 않으므로(디렉토리 스캔이라
     자동 갱신) 별도 코드 수정 불요, 런타임 에러 없음만 확인. (참고: `GET /api/agent/toolsets`는
     `name` 쿼리 파라미터를 지원하지 않는 목록 전체 반환 엔드포인트이므로 `?name=seo` 같은 필터링
     호출은 사용하지 말 것 — `routes/agent_routes.py:267` 시그니처 확인)

### 배치 B — 죽은 SEO 최적화 체인 제거 (제품 결정 불요)

- 대상: `services/agents/seo_optimize_agent.py`, `routes/utility/feedback_quality.py`의
  `/api/seo-optimize` 라우트(`api_seo_optimize` 함수, 3줄), `frontend/lib/api.ts`의 `seoOptimize()`
  함수 + `frontend/lib/types/api.ts:203`의 `SeoOptimizeResponse` 타입, 전용 테스트
  `tests/test_seo_optimize_agent.py` + `tests/test_utility_routes.py`의 `/api/seo-optimize` 관련
  케이스(`_CONTENT_ENDPOINTS` 목록의 `'/api/seo-optimize'` 항목 — 411번째 줄 부근 — 및 454번째
  줄 부근 `simple_services`의 `/api/seo-optimize` 서브테스트, 파일 전체 삭제가 아니라 해당
  엔드포인트 케이스만 목록에서 제거)
  = 파일 4~5개, 40 상한 내 여유
- 의존성: 배치 A와 독립. 순서 무관.
- 검증 기준:
  1. `python -m pytest tests/ -v` — 0 fail
  2. `grep -rln "seo_optimize_agent\|api_seo_optimize\|seoOptimize" --include="*.py" --include="*.ts" --include="*.tsx" .` → 0건.
     **주의**: 이 grep 패턴은 대소문자를 구분하므로 `SeoOptimizeResponse`(타입명, 파스칼케이스)를
     놓친다 — `frontend/lib/types/api.ts:203`의 타입 정의와 그 참조처를 별도로
     `grep -rln "SeoOptimizeResponse"`로 확인해 0건이어야 함
  3. `cd frontend && npx tsc --noEmit && npx next build` — 0 error

### 배치 C — `search_service.py` 처리 ([사람] 결정 후 실행)

- 선행 조건: §3의 "[사람] 결정 필요 — search_service 처리 방향" 응답 대기
- 옵션 C(범위 외 유지) 선택 시: 이번 Dep-7 사이클에서 **손대지 않음**, 별도 버그 트래킹 항목으로
  `plans/loop-board.md`에 별도 기록만 (Dep-7과 분리)
- 옵션 B(라우트까지 제거) 선택 시 대상: `services/seo/search_service.py`,
  `routes/integrations/content_workspace.py`의 `/api/search` 라우트(`search_content` 함수),
  `frontend/components/search/GlobalSearch.tsx`, `routes/integrations/__init__.py` docstring 갱신,
  전용 테스트 `tests/test_search_service.py`(파일 전체, 76줄) +
  `tests/test_integration_routes.py:317`(`@patch('services.seo.search_service.search')`로
  `/api/search` 라우트를 검증하는 케이스 — 파일 전체가 아니라 해당 테스트 메서드만 제거)
- 검증 기준(옵션 B 선택 시):
  1. `python -m pytest tests/ -v` — 0 fail
  2. `grep -rln "services\.seo\.search_service\|GlobalSearch" --include="*.py" --include="*.tsx" .` → 0건
  3. `cd frontend && npx tsc --noEmit && npx next build` — 0 error

### 배치 D — `blog_seo`/`geo_seo` 스타일 완전 제거 ([사람] 결정 후 실행, 배치 중 최대 범위)

- 선행 조건: §3의 "[사람] 결정 필요 — blog_seo/geo_seo 스타일 제거 여부" 응답에서 옵션 3)이
  선택된 경우에만 실행. 옵션 1)/2) 선택 시 이 배치는 보류.
- 대상(옵션 3 선택 시, 캐스케이드 전체):
  - 프롬프트: `prompts/styles/blog_seo.py`, `prompts/styles/geo_seo.py`,
    `prompts/styles/__init__.py`의 `STYLE_PROMPTS` 등록 제거
  - config: `config.py`의 `STYLE_OPTIONS`(2행), `STYLE_TEMPERATURE`(2키)
  - 파서: `services/core/ai_metadata.py`의 `extract_seo_metadata`, `extract_geo_metadata`,
    `extract_faq_schema`, `extract_cta`, `build_faqpage_schema` (다른 스타일이 이 함수들을
    쓰지 않는지 재확인 필요 — 현재 확인 결과 blog_seo/geo_seo 전용)
  - 호출부: `services/core/ai_service.py`, `services/core/pipeline_service.py`,
    `routes/blog_routes.py`, `routes/generation_helpers.py`의 해당 호출 블록
  - `services/seo/seo_metadata_service.py` 전체 + `services/agents/seo_agent.py`의 json_ld
    호출부(§2 시나리오 2번)
  - 프론트: `frontend/lib/constants.ts`의 2개 항목, `frontend/components/result/SeoSection.tsx`,
    `frontend/components/result/GeoSection.tsx`, `frontend/components/result/FaqCtaSection.tsx`
    (`ResultCard.tsx:926-927` `{(report.faq_schema || report.cta) && <FaqCtaSection
    faqSchema={report.faq_schema} cta={report.cta} content={report.content} />}` — blog_seo/geo_seo
    전용 FAQ+CTA 섹션, 스타일 제거 시 `faq_schema`가 항상 없으므로 이 섹션도 함께 정리 대상인지
    확인 필요: `cta`는 geo_seo 전용이지만 `faq_schema`는 blog_seo도 채우므로 두 스타일 모두 제거될
    때만 이 섹션 전체를 정리), `ResultCard.tsx`의 조건부 렌더 블록(SeoSection/GeoSection/
    FaqCtaSection 총 3곳), `frontend/lib/types/api.ts`의 `seo`/`geo`/`json_ld_schemas`/`cta` 타입
    + `faq_schema` 필드(`:38`, `:121` 두 인터페이스에 각각 선언)
  - 테스트: `tests/test_seo_metadata_service.py`, `tests/test_seo_agent.py`(SEOAgent 자체 존치라면
    json_ld 관련 케이스만 수정), ai_metadata 관련 테스트 중 extract_seo/geo/faq/cta 커버 케이스
  - 예상 파일 수: 16~21개 (40 상한 내)
- 의존성: 배치 A/B와 독립적으로 실행 가능하나, **배치 A 완료 후 실행 권장**
  (동일 디렉토리 `services/seo/` 변경이 겹치지 않도록 순서 분리 — 병합 충돌 최소화 목적,
  기능적 의존은 없음)
- 검증 기준:
  1. `python -m pytest tests/ -v` — 0 fail
  2. `grep -rln "blog_seo\|geo_seo" --include="*.py" --include="*.ts" --include="*.tsx" .` → 0건
     (docstring/주석 등 문서 언급 제외 시 별도 확인)
  3. `cd frontend && npx tsc --noEmit && npx next build` — 0 error
  4. 스타일 시스템 테스트: `python -m pytest tests/ -k "style" -v` — 0 fail
     (`_validate_style`, `STYLE_PROMPTS` 관련 테스트가 blog_seo/geo_seo를 하드코딩 참조하는지 확인)
  5. E2E 스모크(선택): `cd tests/e2e && npx playwright test --workers=1`로 스타일 그리드 렌더 확인

## 5. Out-of-scope 가드 리스트 (SEO처럼 보이지만 손대면 안 되는 것)

| 대상 | 왜 SEO처럼 보이는가 | 실제 근거 (유지 판정) |
|------|---------------------|----------------------|
| `frontend/components/result/ScoreCard.tsx` | `seo` 점수 필드를 표시 | 백엔드 `/api/content-score`(`routes/advanced_routes.py:517`)는 `services/quality/quality_service.calculate_comprehensive_score`를 쓰며 `services/seo/`를 전혀 import하지 않음. 컴포넌트 자체는 고아(§0-3)지만 **Dep-7 범위(services/seo) 밖** — 건드리려면 별도 quality 도메인 정리 이슈로 분리 |
| `services/core/ai_metadata.py`의 `extract_seo_metadata`/`extract_geo_metadata`/`extract_faq_schema`/`extract_cta` | 이름에 "seo"/"geo" 포함, `services/seo/`와 혼동하기 쉬움 | 물리적으로 `services/core/`에 위치하며 `services/seo/` 디렉토리와 무관. blog_seo/geo_seo 스타일의 **메인 생성 경로 파서**이므로 배치 D(스타일 자체 제거)를 실행하지 않는 한 절대 건드리지 않는다 |
| `services/agents/seo_agent.py`(SEOAgent 클래스 자체, meta_title/description/faq/keywords 생성 부분) | 파일명에 seo, `agent_mode` 4단계 고정 스텝 | `agent_mode`는 스타일 무관의 범용 "에이전트 모드" 기능(§1 하단)이라 SEO 스타일 제거와 독립. json_ld 호출부(`services/seo/seo_metadata_service` 의존 부분)만 배치 D에서 함께 정리하고, 나머지 메타데이터 생성 로직은 존치 — 오케스트레이터 재설계는 별도 작업 |
| `services/data/web_scraper_service.py`, `services/data/auto_tag_service.py` | `competitor_analysis_service.py`가 이 둘을 import(§1 #5) | 당시에는 범위 밖으로 보류. 이후 `auto_tag_service.py`는 프론트 소비 0 라우트(`/api/auto-tags`) 전용 고아로 재검증되어 별도 배치에서 제거됨. |
| `services/quality/qa_gate_service.py`(발행 전 QA 게이트) | "품질/게이트"라는 이름이 SEO 점검과 유사한 어휘 | `services/seo/`와 물리적으로 무관한 별도 도메인(`services/quality/`), CLAUDE.md에 별도 기능(`POST /api/qa-check`)으로 명시되어 있음 — Dep-7 범위 아님 |
| `services/rag/`(RAG 지식 참조, ChromaDB) | 제품 비전의 "지식 위키" 기둥과 혼동 가능 | SEO와 무관한 학습축 핵심 인프라, 이 문서의 어떤 배치에서도 대상이 아님 (명시적으로 out-of-scope) |

## 6. `AGENT_MODE_ENABLED` / pkgutil 스캔 활성 여부 상세 근거

- `config.py:73`: `AGENT_MODE_ENABLED: bool = os.getenv('AGENT_MODE_ENABLED', 'false').lower() == 'true'`
  — 기본값 `false`. `.env.example`에 이 변수의 문서화 여부는 이번 조사에서 별도 확인하지 않음(참고용).
- `app.py:230-238`: `if getattr(_cfg, 'AGENT_MODE_ENABLED', False): ... from agent.tools import
  discover_tools; discover_tools()` — 이 블록이 실행되어야 `agent/tools/seo_tools.py`의
  `_register_tools()`(모듈 import 시 즉시 실행되는 최하단 코드)가 `services/seo/`를 스캔한다.
- `agent/tools/seo_tools.py`가 import되는 것 자체는 `discover_tools()`가 `pkgutil.iter_modules`로
  `agent/tools/` 패키지를 스캔할 때 발생하므로, `AGENT_MODE_ENABLED=false`인 기본 상태에서는
  `agent/tools/seo_tools.py`가 아예 import되지 않고 따라서 `services/seo/*` 모듈도 로드되지 않는다.
- 프론트 노출(정정): `frontend/components/agent/AgentPipeline.tsx`는 `agent/tools/seo_tools.py`가
  자동 등록하는 "MCP 에이전트 도구 레지스트리"를 소비하는 게 **아니다** — 이 컴포넌트는 파이프라인
  단계 id로 `'seo'`(`{ id: 'seo', name: 'SEO', description: '메타데이터 최적화' }`)를 하드코딩
  나열하고, 실제 API 호출은 `fetch(apiUrl('/api/agent/pipeline'))`(60번째 줄)로 이루어진다. 이는
  `services/agents/orchestrator.py`의 `Orchestrator`(Research→Writer→Editor→SEO 4단계) 경로를
  의도한 것으로 보이나, `routes/agent_routes.py`에 등록된 라우트는 `/api/agent/{chat,chat/stream,
  sdk,sessions,tools,toolsets}` 6개뿐이고 `/api/agent/pipeline`은 **존재하지 않는 엔드포인트**다
  (`grep -n "@agent_bp.route" routes/agent_routes.py`로 전수 확인). 즉 이 컴포넌트는 (1) 어디서도
  마운트되지 않고 (2) 설령 마운트되어도 호출할 라우트가 없어 이중으로 죽어있다.
  `AGENT_MODE_ENABLED`/pkgutil 게이팅 논증(§6 상단)은 이 컴포넌트와 무관하게 `config.py:73` +
  `app.py:229-238`만으로 독립적으로 성립한다.
- 결론: 에이전트 도구 자동등록 경로(`agent/tools/seo_tools.py`)는 (1) 기본 비활성
  (`AGENT_MODE_ENABLED=false`)이라는 게이팅 근거만으로 충분히 비활성 판정이 서며,
  `AgentPipeline.tsx`의 이중 고아 상태는 별개의 보강 증거일 뿐이다. 완전한 배제 근거로 삼기엔
  `AGENT_MODE_ENABLED=true`로 운영자가 수동 설정했을 가능성이 이론상 남아있으므로 배치 A 실행
  후 반드시 런타임 재확인(§4 배치 A 검증 기준 4번)을 수행한다.

## 요약 (지휘자 보고용)

- 측정된 `services/seo/` 파일 수: **27개**(`__init__.py` 포함, 실서비스 26개)
- verdict 집계: 학습축 사용 **0** / SEO 전용-제거 후보 **24** / 판단 필요 **4**
  (`search_service.py`, `seo_metadata_service.py`, `services/agents/seo_agent.py`,
  `blog_seo`/`geo_seo` 스타일 자체 — 스타일은 services/seo 밖이지만 이 정리의 본질적 상위 결정이라 포함) /
  패키지 마커(비대상) **1**
- 제안 배치 수: **4개** (A: 순수 제거 즉시 가능(24 서비스+24 테스트=48파일, 40 상한 8개 초과 —
  A1/A2 세분 권장) / B: 죽은 체인 즉시 가능 / C: search_service, [사람] 결정 대기 / D: blog_seo·
  geo_seo 스타일 완전 제거, [사람] 결정 대기)
- 놀라운 발견: (1) `agent/tools/seo_tools.py`의 pkgutil 스캔(모듈당 첫 함수만 등록) — 기본
  비활성(`AGENT_MODE_ENABLED=false`)이라 안전하지만 존재를 몰랐다면 "제거 후보"를 죽은 코드로
  오판할 뻔했고, `agent/prompts/roles.py`·`agent/core.py`에 이 배치 대상 도구 이름을 하드코딩
  참조하는 잔재도 발견, (2) `search_service.py`는 애초 "고장난 활성 기능"으로 판단했으나 재검증
  결과 유일한 프론트 소비자 `GlobalSearch.tsx`도 고아임을 확인 — **완전히 죽은 체인**으로 정정,
  (3) `ScoreCard.tsx`가 SEO 필드를 갖지만 실제로는 `services/quality/`에 속해 Dep-7 범위 밖,
  (4) `AgentPipeline.tsx`는 고아 컴포넌트일 뿐 아니라 호출 대상 `/api/agent/pipeline` 라우트
  자체가 존재하지 않아 이중으로 죽어있음.
