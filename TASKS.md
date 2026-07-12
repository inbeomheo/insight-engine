# TASKS.md — 기능 전체 구현 메가 플랜

> 5개 보고서(YouTube/AI, 플랫폼/SaaS, UX/디자인, 수익화/그로스, AI/ML) 전체 기능을
> 10개 Phase로 조직한 극세분화 태스크 플랜

## 메타데이터

- **총 Phase**: 10개
- **예상 태스크**: ~800개 (기능당 평균 3-4개)
- **기존 부분 구현**: tts_service, rss_service, web_scraper, graph_store, style_memory 등 40+ 서비스 활용
- **기술 스택**: Flask 백엔드 + Next.js 16 프론트엔드 + LiteLLM + ChromaDB + Supabase

---

## Phase 1: 멀티소스 입력 확장

> YouTube 전용 → 범용 콘텐츠 플랫폼 전환. 기존 web_scraper_service, rss_service 활용.

### F1-01. 웹 URL → 콘텐츠 생성 — 난이도 S
- **기존**: web_scraper_service.py (trafilatura+Scrapling), blog_routes.py에 source_type='webpage' 이미 허용
- [P1-01] routes/blog_routes.py: /generate에서 source_type='webpage' 분기 → web_scraper_service.scrape_webpage() 호출 로직 완성 | 검증: pytest
- [P1-02] frontend/components/input/UrlInput.tsx: URL 입력 시 YouTube/웹페이지 자동 감지 UI 추가 | 검증: build
- [P1-03] tests/test_web_generate.py: 웹 URL 생성 통합 테스트 | 검증: pytest

### F1-02. PDF 업로드 → 콘텐츠 생성 — 난이도 M
- **기존**: PyPDF2 의존성 있음, RAG용 knowledge 업로드 경로 존재
- [P1-04] services/document_ingest_service.py: PDF/DOCX 텍스트 추출 서비스 (PyPDF2 + python-docx) | 검증: pytest
- [P1-05] routes/blog_routes.py: /generate에 file upload 지원 (multipart/form-data) | 검증: pytest
- [P1-06] frontend/components/input/FileUpload.tsx: 드래그앤드롭 파일 업로드 컴포넌트 | 검증: build
- [P1-07] frontend/lib/api.ts: generateFromFile() API 함수 추가 | 검증: tsc

### F1-03. DOCX 업로드 → 콘텐츠 생성 — 난이도 S
- [P1-08] services/document_ingest_service.py에 DOCX 추출 추가 (python-docx) | 검증: pytest
- F1-02의 프론트엔드 재사용

### F1-04. 텍스트 직접 입력 → 콘텐츠 생성 — 난이도 S
- **기존**: blog_routes.py에 content 파라미터 이미 존재
- [P1-09] frontend/components/input/TextInput.tsx: 텍스트 직접 입력 탭 추가 | 검증: build
- [P1-10] frontend/hooks/useGenerate.ts: generateFromText() 추가 | 검증: tsc

### F1-06. 팟캐스트 오디오 URL → 자막 → 콘텐츠 — 난이도 M
- **기존**: whisper_service.py, yt-dlp
- [P1-15] services/content_service.py: 팟캐스트 URL 감지 + yt-dlp 오디오 다운로드 + Whisper 변환 경로 추가 | 검증: pytest
- [P1-16] frontend/components/input/UrlInput.tsx: 팟캐스트 URL 아이콘/라벨 표시 | 검증: build

### F1-07. ArXiv 논문 → 콘텐츠 생성 강화 — 난이도 S
- **기존**: arxiv_service.py 존재
- [P1-17] services/arxiv_service.py: 논문 PDF 전문 추출 + 요약 파이프라인 강화 | 검증: pytest
- [P1-18] frontend: ArXiv URL 자동 감지 + 논문 메타데이터 표시 | 검증: build

### F1-08. 트위터/X 스레드 → 콘텐츠 변환 — 난이도 M
- [P1-19] services/social_scraper_service.py: X/Twitter 스레드 텍스트 추출 | 검증: pytest
- [P1-20] routes/blog_routes.py: source_type='twitter' 분기 추가 | 검증: pytest

### F1-09. Reddit 포스트 → 콘텐츠 변환 — 난이도 M
- [P1-21] services/social_scraper_service.py: Reddit 포스트+댓글 추출 (JSON API) | 검증: pytest
- [P1-22] routes/blog_routes.py: source_type='reddit' 분기 추가 | 검증: pytest

### F1-11. Google Docs → 콘텐츠 변환 — 난이도 M
- [P1-26] services/gdocs_service.py: Google Docs API → 마크다운 추출 | 검증: pytest
- [P1-27] routes/integration_routes.py: /api/gdocs/import 엔드포인트 | 검증: pytest

### F1-12. 이메일 뉴스레터 → 콘텐츠 변환 — 난이도 L
- [P1-28] services/email_ingest_service.py: IMAP/포워딩 기반 이메일 본문 추출 | 검증: pytest
- [P1-29] routes/integration_routes.py: /api/email/ingest 엔드포인트 | 검증: pytest

### F1-13. 클립보드 붙여넣기 → 즉시 생성 — 난이도 S
- [x] [P1-30] frontend/components/input/ClipboardPaste.tsx: Ctrl+V 감지 → 텍스트/URL 자동 판별 | 검증: build

### F1-15. YouTube 채널 전체 분석 — 난이도 L
- **기존**: channel_monitor_service.py
- [P1-33] services/channel_analysis_service.py: 채널 영상 목록 → 주제별 클러스터링 → 종합 분석 | 검증: pytest
- [P1-34] routes/advanced_routes.py: /api/channel-analysis 엔드포인트 | 검증: pytest
- [P1-35] frontend/components/result/ChannelAnalysis.tsx: 채널 분석 대시보드 UI | 검증: build

### F1-16. Spotify 팟캐스트 에피소드 — 난이도 M
- [P1-36] services/spotify_service.py: Spotify 에피소드 메타데이터 + 외부 오디오 URL 추출 | 검증: pytest

### F1-17. 슬라이드(PPT/Keynote) → 콘텐츠 — 난이도 M
- [P1-38] services/document_ingest_service.py: PPTX 텍스트+노트 추출 (python-pptx) | 검증: pytest

### F1-18. 음성 메모 녹음 → 콘텐츠 — 난이도 M
- [P1-39] frontend/components/input/VoiceRecorder.tsx: 브라우저 MediaRecorder로 음성 녹음 | 검증: build
- [P1-40] routes/blog_routes.py: 오디오 파일 업로드 → Whisper → 콘텐츠 생성 | 검증: pytest

### F1-19. 이미지 OCR → 콘텐츠 — 난이도 M
- [P1-41] services/ocr_service.py: Gemini Vision / Tesseract OCR로 이미지 텍스트 추출 | 검증: pytest

### F1-20. GitHub README → 기술 블로그 — 난이도 S
- [P1-42] services/github_service.py: GitHub API → README.md 추출 | 검증: pytest
- [P1-43] 기존 /generate 파이프라인에 source_type='github' 추가 | 검증: pytest

### F1-21. Hacker News 스레드 → 요약 — 난이도 M
- [P1-44] services/social_scraper_service.py: HN API → 포스트+댓글 추출 | 검증: pytest

### F1-22. Wikipedia → 해설 콘텐츠 — 난이도 S
- [P1-45] 기존 web_scraper_service로 위키피디아 특화 파싱 규칙 추가 | 검증: pytest

### F1-23. Stack Overflow Q&A → 튜토리얼 — 난이도 M
- [P1-46] services/social_scraper_service.py: SO API → 질문+답변 추출 | 검증: pytest

### F1-24. 뉴스 기사 URL 배치 → 종합 리포트 — 난이도 M
- **기존**: multi_source_collector.py, fusion_service.py
- [P1-47] services/news_digest_service.py: 복수 뉴스 URL → 주제별 종합 다이제스트 | 검증: pytest

---

## Phase 2: 멀티모달 출력

> 텍스트 중심 → 오디오/이미지/영상/슬라이드 등 다양한 포맷 출력

### F2-01. TTS 오디오 변환 강화 — 난이도 S
- **기존**: tts_service.py (OpenAI + Edge TTS), AudioPlayer.tsx, synthesizeTts() API
- [P2-01] frontend/components/result/AudioPlayer.tsx: 다운로드 버튼 + 속도 조절 슬라이더 추가 | 검증: build
- [P2-02] services/tts_service.py: 배치 TTS (장문 분할 처리) 최적화 | 검증: pytest

### F2-03. 마크다운 → 슬라이드(PPT) 변환 — 난이도 M
- [P2-08] services/slide_service.py: 마크다운 → Marp/Reveal.js 슬라이드 HTML 변환 | 검증: pytest
- [P2-09] routes/export_routes.py: /api/export/slides 엔드포인트 | 검증: pytest
- [P2-10] frontend/components/result/SlidePreview.tsx: 슬라이드 미리보기 모달 | 검증: build

### F2-04. OG 이미지 + 소셜 카드 자동 생성 — 난이도 S
- [P2-11] frontend/app/api/og/route.tsx: Next.js OG Image API Route (Satori) | 검증: build
- [P2-12] frontend/components/result/SocialCardPreview.tsx: 소셜 카드 미리보기 | 검증: build

### F2-05. 인포그래픽 자동 생성 — 난이도 L
- [P2-13] services/infographic_service.py: 콘텐츠 핵심 데이터 → 구조화 → SVG/HTML 인포그래픽 | 검증: pytest
- [P2-14] routes/export_routes.py: /api/export/infographic 엔드포인트 | 검증: pytest
- [P2-15] frontend/components/result/InfographicPreview.tsx: 인포그래픽 미리보기 | 검증: build

### F2-06. 비디오 Shorts 클립 자동 생성 — 난이도 XL
- **기존**: shorts_script 스타일 존재 (스크립트만)
- [P2-16] services/video_clip_service.py: yt-dlp 타임스탬프 구간 추출 → ffmpeg 클립 편집 | 검증: pytest
- [P2-17] services/subtitle_overlay_service.py: 클립에 자막 오버레이 (ffmpeg drawtext) | 검증: pytest
- [P2-18] routes/advanced_routes.py: /api/generate-clips 엔드포인트 | 검증: pytest
- [P2-19] frontend/components/result/VideoClipPlayer.tsx: 클립 미리보기 + 다운로드 | 검증: build

### F2-07. 팟캐스트 에피소드 자동 생성 — 난이도 L
- [P2-20] services/podcast_service.py: 콘텐츠 → 대화체 스크립트 → TTS(2인 대화) → MP3 | 검증: pytest
- [P2-21] routes/advanced_routes.py: /api/generate-podcast 엔드포인트 | 검증: pytest
- [P2-22] frontend/components/result/PodcastPlayer.tsx: 에피소드 플레이어 UI | 검증: build

### F2-08. 이메일 뉴스레터 HTML 템플릿 — 난이도 M
- [P2-23] services/newsletter_template_service.py: 콘텐츠 → 이메일 친화 HTML 변환 (인라인 CSS) | 검증: pytest
- [P2-24] routes/export_routes.py: /api/export/newsletter-html 엔드포인트 | 검증: pytest
- [P2-25] frontend/components/result/NewsletterPreview.tsx: 이메일 미리보기 | 검증: build

### F2-09. 카드뉴스 이미지 세트 — 난이도 L
- [P2-26] services/card_news_service.py: 콘텐츠 → 10장 카드뉴스 이미지 생성 (Pillow/SVG) | 검증: pytest
- [P2-27] routes/export_routes.py: /api/export/card-news 엔드포인트 | 검증: pytest

### F2-10. 워드클라우드 생성 — 난이도 S
- [P2-28] services/wordcloud_service.py: 콘텐츠 키워드 → 워드클라우드 SVG | 검증: pytest
- [P2-29] frontend/components/result/WordCloud.tsx: 워드클라우드 표시 | 검증: build

### F2-11. 요약 카드(Summary Card) 이미지 — 난이도 M
- [P2-30] services/summary_card_service.py: 제목+핵심3줄 → 공유용 이미지 생성 | 검증: pytest

### F2-12. LaTeX/수식 렌더링 — 난이도 S
- [P2-31] frontend: KaTeX 연동으로 수식 포함 콘텐츠 렌더링 | 검증: build

### F2-13. 코드 스니펫 → 이미지 — 난이도 S
- [P2-32] services/code_image_service.py: 코드 블록 → carbon.sh 스타일 이미지 | 검증: pytest

### F2-14. 마인드맵 → SVG/PNG 내보내기 — 난이도 M
- **기존**: MindmapModal.tsx 존재
- [P2-33] frontend/components/modals/MindmapModal.tsx: SVG/PNG 다운로드 버튼 추가 | 검증: build

### F2-15. 타임라인 인포그래픽 — 난이도 M
- [P2-34] services/timeline_service.py: 챕터/이벤트 → 시각적 타임라인 HTML 생성 | 검증: pytest

### F2-16. 비교표 자동 생성 — 난이도 M
- [P2-35] services/comparison_service.py: 복수 영상/기사 → 항목별 비교표 마크다운 | 검증: pytest

### F2-17. RSS 피드 자동 생성 — 난이도 S
- [P2-36] routes/utility_routes.py: /feed.xml 엔드포인트 — 생성된 콘텐츠를 RSS로 발행 | 검증: pytest

### F2-18. EPUB 전자책 내보내기 — 난이도 M
- [P2-37] services/epub_service.py: 콘텐츠 → EPUB 변환 (ebooklib) | 검증: pytest
- [P2-38] routes/export_routes.py: /api/export/epub 엔드포인트 | 검증: pytest

### F2-19. 오디오 자막(SRT/VTT) 내보내기 — 난이도 S
- [P2-39] routes/export_routes.py: /api/export/srt 엔드포인트 (자막 세그먼트 → SRT) | 검증: pytest

### F2-20. 다국어 동시 출력 — 난이도 M
- [P2-40] routes/advanced_routes.py: /api/generate-multilang — 한/영/일 동시 생성 | 검증: pytest
- [P2-41] frontend/components/result/MultiLangView.tsx: 언어별 탭 뷰 | 검증: build

### F2-21. Interactive HTML 보고서 — 난이도 M
- [P2-42] services/interactive_report_service.py: 목차+접기+검색 포함 독립 HTML 생성 | 검증: pytest

### F2-22. Notion 내보내기 — 난이도 M
- [P2-43] services/notion_export_service.py: Notion API로 페이지 생성 | 검증: pytest

### F2-23. Google Docs 내보내기 — 난이도 M
- [P2-44] services/gdocs_export_service.py: Google Docs API로 문서 생성 | 검증: pytest

### F2-24. Medium 내보내기 — 난이도 M
- [P2-45] services/mcp/plugins/medium.py: Medium API 연동 MCP 플러그인 | 검증: pytest

### F2-25. Substack 내보내기 — 난이도 M
- [P2-46] services/mcp/plugins/substack.py: Substack 연동 MCP 플러그인 | 검증: pytest

---

## Phase 3: AI 에이전트 시스템

> 단순 1회 AI 호출 → 자율 에이전트 기반 지능형 파이프라인

### F3-02. GraphRAG 고도화 — 난이도 L
- **기존**: services/rag/graph_store.py, graph_builder.py (networkx 기반)
- [P3-05] services/rag/graph_rag_engine.py: 엔티티/관계 자동 추출 → 그래프 구축 → 글로벌/로컬 검색 | 검증: pytest
- [P3-06] services/rag/graph_builder.py: LLM 기반 엔티티-관계 추출 강화 (microsoft/graphrag 패턴) | 검증: pytest
- [P3-07] frontend/components/settings/KnowledgeGraph.tsx: 지식 그래프 시각화 (d3-force) | 검증: build

### F3-03. 멀티에이전트 콘텐츠 파이프라인 — 난이도 XL
- [P3-08] services/agent/content_pipeline_agent.py: 리서처→작가→편집자→SEO 4단계 에이전트 체인 | 검증: pytest
- [P3-09] services/agent/agent_orchestrator.py: 에이전트 오케스트레이터 (순차/병렬 실행) | 검증: pytest
- [P3-10] config.py: AGENT_MODE_ENABLED, AGENT_MODELS 설정 추가 | 검증: pytest
- [P3-11] ~~frontend/components/agent/AgentPipeline.tsx~~: 고아 컴포넌트로 제거됨. 재도입 시 실제 진입점과 함께 신규 UI 작성 | 검증: build

### F3-04. AI 메모리 레이어 (개인화) — 난이도 M
- **기존**: style_memory_service.py
- [P3-12] services/memory_service.py: 사용자별 장기 메모리 (선호 주제, 톤, 피드백 기록) | 검증: pytest
- [P3-13] services/ai_service.py: 프롬프트에 메모리 컨텍스트 자동 주입 | 검증: pytest
- [P3-14] frontend/components/settings/MemoryManager.tsx: 메모리 조회/편집 UI | 검증: build

### F3-05. Corrective RAG 강화 — 난이도 M
- **기존**: services/rag/corrective_rag.py
- [P3-15] services/rag/corrective_rag.py: 검색 결과 관련성 평가 → 웹 폴백 → 재검색 루프 강화 | 검증: pytest

### F3-06. 적응형 프롬프트 최적화 — 난이도 L
- [P3-16] services/prompt_optimizer_service.py: 사용자 피드백 기반 프롬프트 자동 조정 | 검증: pytest
- [P3-17] routes/utility_routes.py: /api/feedback 엔드포인트 (좋아요/싫어요) | 검증: pytest
- [P3-18] frontend/components/result/FeedbackButtons.tsx: 콘텐츠 피드백 UI | 검증: build

### F3-07. 자동 팩트체크 에이전트 — 난이도 L
- [P3-19] services/agent/fact_check_agent.py: 콘텐츠 주장 → 웹검색 → 사실 검증 → 마킹 | 검증: pytest
- [P3-20] frontend/components/result/FactCheckBadge.tsx: 팩트체크 결과 표시 | 검증: build

### F3-08. SEO 자동 최적화 에이전트 — 난이도 M
- **기존**: seo_metadata_service.py
- [P3-21] services/agent/seo_agent.py: 키워드 밀도/구조/내부링크 자동 최적화 | 검증: pytest

### F3-09. 표절/중복 감지 — 난이도 M
- [P3-22] services/plagiarism_service.py: 생성된 콘텐츠 vs 웹 유사도 검사 | 검증: pytest
- [P3-23] frontend/components/result/PlagiarismScore.tsx: 유사도 점수 표시 | 검증: build

### F3-10. 가독성 점수 분석 — 난이도 S
- [P3-24] services/readability_service.py: Flesch-Kincaid/한국어 가독성 점수 계산 | 검증: pytest
- [P3-25] frontend/components/result/ReadabilityGauge.tsx: 가독성 게이지 UI | 검증: build

### F3-11. 감정 분석 강화 — 난이도 S
- **기존**: nlp_analysis_service.py
- [P3-26] services/nlp_analysis_service.py: 문단별 감정 흐름 분석 추가 | 검증: pytest
- [P3-27] frontend/components/result/SentimentFlow.tsx: 감정 흐름 차트 | 검증: build

### F3-12. 토픽 클러스터링 — 난이도 M
- [P3-28] services/topic_cluster_service.py: 생성된 콘텐츠들을 주제별 자동 클러스터링 | 검증: pytest

### F3-13. 자동 내부 링크 추천 — 난이도 M
- **기존**: backlink_service.py
- [P3-29] services/backlink_service.py: 기존 콘텐츠 간 관련성 분석 → 내부 링크 자동 추천 강화 | 검증: pytest

### F3-14. A/B 테스트 제목 생성 — 난이도 M
- [P3-30] services/ab_title_service.py: 하나의 콘텐츠에 대해 3-5개 제목 변형 생성 | 검증: pytest
- [P3-31] frontend/components/result/ABTitleSelector.tsx: 제목 후보 선택 UI | 검증: build

### F3-15. 콘텐츠 톤 분석기 — 난이도 S
- [P3-32] services/tone_analyzer_service.py: 콘텐츠 톤 분석 (전문적/캐주얼/유머/학술 등) | 검증: pytest

### F3-16. 키워드 갭 분석 — 난이도 M
- [P3-33] services/keyword_gap_service.py: 경쟁 콘텐츠 대비 누락 키워드 분석 | 검증: pytest

### F3-17. 콘텐츠 길이 최적화 — 난이도 S
- [P3-34] services/length_optimizer_service.py: SEO 목적 최적 길이 분석 + 자동 확장/축소 | 검증: pytest

### F3-18. 자동 목차(TOC) 생성 — 난이도 S
- [P3-35] services/toc_service.py: 마크다운 헤딩 → 자동 목차 + 앵커 링크 | 검증: pytest

### F3-19. 콘텐츠 유사도 비교 — 난이도 M
- [P3-36] services/similarity_service.py: 두 콘텐츠 간 의미적 유사도 계산 (임베딩) | 검증: pytest

### F3-21. 콘텐츠 브리프 생성 — 난이도 M
- [P3-39] services/brief_service.py: 주제/키워드 → 콘텐츠 브리프 (개요, 타겟, 키워드, 구조) | 검증: pytest

### F3-22. 경쟁 콘텐츠 분석 — 난이도 L
- [P3-40] services/competitor_analysis_service.py: 키워드 → 상위 랭킹 콘텐츠 분석 → 차별화 포인트 | 검증: pytest

### F3-23. 콘텐츠 점수 카드 — 난이도 M
- **기존**: quality_service.py
- [P3-41] services/quality_service.py: 종합 점수 (SEO + 가독성 + 독창성 + 구조) 통합 | 검증: pytest
- [P3-42] ~~frontend/components/result/ScoreCard.tsx~~: 고아 컴포넌트로 제거됨. 재도입 시 실제 소비 화면과 함께 신규 UI 작성 | 검증: build

### F3-24. AI 코멘터리 (해설) — 난이도 M
- [P3-43] services/commentary_service.py: 원본 콘텐츠에 AI 해설/주석 추가 | 검증: pytest

---

## Phase 4: 수익화 & 과금

> 무료 도구 → 지속 가능한 SaaS 비즈니스 모델 구축

### F4-01. 크레딧 기반 과금 시스템 — 난이도 M
- **기존**: services/usage/ (usage_service, require_usage 데코레이터)
- [P4-01] services/usage/credit_service.py: 크레딧 잔액 관리 (충전/차감/잔액조회/자동충전) | 검증: pytest
- [P4-02] services/usage/credit_plan.py: 플랜별 크레딧 할당 (Free:10/일, Pro:100/일, Team:500/일) | 검증: pytest
- [P4-03] routes/auth_routes.py: /api/credits/balance, /api/credits/purchase 엔드포인트 | 검증: pytest
- [P4-04] frontend/components/billing/CreditBalance.tsx: 크레딧 잔액 표시 + 충전 버튼 | 검증: build

### F4-02. Stripe 결제 연동 — 난이도 M
- [P4-05] services/payment/stripe_service.py: Stripe Checkout Session 생성 + 웹훅 처리 | 검증: pytest
- [P4-06] routes/payment_routes.py: /api/payment/checkout, /api/payment/webhook 엔드포인트 | 검증: pytest
- [P4-07] frontend/components/billing/PricingPage.tsx: 가격 플랜 페이지 | 검증: build
- [P4-08] frontend/components/billing/CheckoutButton.tsx: Stripe Checkout 리다이렉트 | 검증: build

### F4-03. 구독 플랜 관리 — 난이도 M
- [P4-09] services/payment/subscription_service.py: 구독 생성/업그레이드/다운그레이드/취소 | 검증: pytest
- [P4-10] routes/payment_routes.py: /api/subscription CRUD 엔드포인트 | 검증: pytest
- [P4-11] frontend/components/billing/SubscriptionManager.tsx: 구독 관리 UI | 검증: build

### F4-04. 무료 체험 (Trial) — 난이도 S
- [P4-12] services/payment/trial_service.py: 7일 무료 체험 + 만료 알림 | 검증: pytest

### F4-05. 사용량 대시보드 — 난이도 M
- **기존**: /api/admin/dashboard
- [P4-13] routes/auth_routes.py: /api/usage/my-usage (사용자별 상세 사용량) | 검증: pytest
- [P4-14] frontend/components/billing/UsageDashboard.tsx: 일별/주별 사용량 차트 (Recharts) | 검증: build

### F4-06. 추천인/레퍼럴 프로그램 — 난이도 M
- [P4-15] services/referral_service.py: 추천 코드 생성 + 가입 시 양쪽 크레딧 보너스 | 검증: pytest
- [P4-16] routes/auth_routes.py: /api/referral/code, /api/referral/redeem 엔드포인트 | 검증: pytest
- [P4-17] frontend/components/billing/ReferralCard.tsx: 추천 링크 공유 UI | 검증: build

### F4-07. API 키 발급 (외부 개발자용) — 난이도 M
- **기존**: ie_api_keys 테이블
- [P4-18] services/api_key_service.py: API 키 생성/폐기/사용량 추적 | 검증: pytest
- [P4-19] routes/auth_routes.py: /api/keys CRUD 엔드포인트 | 검증: pytest
- [P4-20] frontend/components/settings/ApiKeyManager.tsx: API 키 관리 UI | 검증: build

### F4-08. 팀 플랜 (팀 과금) — 난이도 M
- [P4-21] services/payment/team_billing_service.py: 팀 단위 크레딧 공유 + 멤버별 사용량 | 검증: pytest

### F4-09. 사용량 알림 (한도 근접) — 난이도 S
- [P4-22] services/usage/usage_alert_service.py: 80%/100% 사용량 이메일/앱내 알림 | 검증: pytest
- [P4-23] frontend/components/billing/UsageAlert.tsx: 잔여 크레딧 경고 배너 | 검증: build

### F4-10. 인보이스 자동 생성 — 난이도 M
- [P4-24] services/payment/invoice_service.py: Stripe Invoice 연동 + PDF 생성 | 검증: pytest
- [P4-25] routes/payment_routes.py: /api/invoices 엔드포인트 | 검증: pytest

### F4-11. 하이브리드 과금 (구독+종량제) — 난이도 M
- [P4-26] services/payment/hybrid_billing_service.py: 기본 크레딧 + 초과분 종량제 | 검증: pytest

### F4-12. 쿠폰/프로모션 코드 — 난이도 S
- [P4-27] services/payment/coupon_service.py: 할인 코드 생성/적용/만료 관리 | 검증: pytest
- [P4-28] frontend/components/billing/CouponInput.tsx: 쿠폰 코드 입력 UI | 검증: build

### F4-13. LTV/코호트 분석 — 난이도 M
- [P4-29] services/analytics/cohort_service.py: 사용자 코호트별 잔존율/LTV 계산 | 검증: pytest

### F4-14. 콘텐츠 마켓플레이스 — 난이도 XL
- [P4-30] services/marketplace_service.py: 사용자가 프롬프트 템플릿을 판매할 수 있는 마켓 | 검증: pytest
- [P4-31] routes/marketplace_routes.py: /api/marketplace CRUD + 결제 | 검증: pytest
- [P4-32] frontend/components/marketplace/MarketplaceBrowser.tsx: 마켓 브라우징 UI | 검증: build

### F4-15. 화이트라벨 (리셀러) — 난이도 XL
- [P4-33] services/whitelabel_service.py: 커스텀 도메인 + 로고 + 브랜딩 관리 | 검증: pytest
- [P4-34] config.py: WHITELABEL_ENABLED, WHITELABEL_CONFIG 설정 | 검증: pytest

### F4-16. Paddle 결제 대안 — 난이도 M
- [P4-35] services/payment/paddle_service.py: Paddle API 연동 (MoR 모델) | 검증: pytest

### F4-17. 크립토 결제 (선택적) — 난이도 M
- [P4-36] services/payment/crypto_service.py: Coinbase Commerce 연동 | 검증: pytest

### F4-18. 기능 게이팅 (플랜별 기능 제한) — 난이도 M
- [P4-37] services/feature_gate_service.py: 플랜별 기능 접근 제어 데코레이터 | 검증: pytest
- [P4-38] config.py: PLAN_FEATURES 매핑 (Free/Pro/Team별 허용 기능) | 검증: pytest

### F4-19. 온보딩 퍼널 — 난이도 M
- [P4-39] frontend/components/onboarding/OnboardingFlow.tsx: 단계별 온보딩 (프로바이더 설정→첫 생성→구독) | 검증: build

### F4-21. 사용자 세그먼트 — 난이도 M
- [P4-42] services/analytics/segment_service.py: 사용자를 활동 패턴별 세그먼트 분류 | 검증: pytest

### F4-22. 이탈 방지 알림 — 난이도 M
- [P4-43] services/retention_service.py: 7일 미사용 → 이메일/알림으로 재참여 유도 | 검증: pytest

### F4-23. 사용 리포트 자동 이메일 — 난이도 M
- [P4-44] services/report_email_service.py: 주간/월간 사용 리포트 이메일 발송 | 검증: pytest

### F4-24. 엔터프라이즈 SSO — 난이도 L
- [P4-45] services/auth/sso_service.py: SAML/OIDC 기반 기업 SSO 연동 | 검증: pytest

### F4-25. 감사 로그 — 난이도 M
- [P4-46] services/audit_log_service.py: 모든 주요 액션 감사 로그 기록 | 검증: pytest
- [P4-47] routes/auth_routes.py: /api/admin/audit-logs 엔드포인트 | 검증: pytest

---

## Phase 5: UX/UI 혁신

> 리텐션을 높이는 현대적 UX 패턴 도입

### F5-01. 커맨드 팔레트 (⌘K) — 난이도 S
- [P5-01] frontend: cmdk 패키지 설치 | 검증: npm install
- [P5-02] frontend/components/ui/CommandPalette.tsx: ⌘K 커맨드 팔레트 (생성/설정/검색/내보내기 통합) | 검증: build
- [P5-03] frontend/app/layout.tsx: 글로벌 ⌘K 키바인딩 등록 | 검증: build

### F5-02. 실시간 협업 편집 — 난이도 XL
- [P5-04] services/collaboration_service.py: WebSocket 기반 실시간 동기화 (OT/CRDT) | 검증: pytest
- [P5-05] frontend/components/editor/CollaborativeEditor.tsx: Tiptap + Y.js 협업 에디터 | 검증: build
- [P5-06] frontend/components/editor/PresenceCursors.tsx: 참여자 커서 표시 | 검증: build

### F5-03. 드래그앤드롭 파이프라인 빌더 — 난이도 L
- [P5-07] frontend/components/pipeline/PipelineBuilder.tsx: React Flow 기반 비주얼 파이프라인 편집기 | 검증: build
- [P5-08] frontend/components/pipeline/PipelineNode.tsx: 각 단계 노드 (소스/생성/SEO/발행) | 검증: build

### F5-04. 콘텐츠 버전 히스토리 + diff — 난이도 M
- [P5-10] services/version_service.py: 콘텐츠 버전 저장/비교/복원 | 검증: pytest
- [P5-11] routes/blog_routes.py: /api/content/<id>/versions 엔드포인트 | 검증: pytest
- [P5-12] frontend/components/result/VersionHistory.tsx: 버전 목록 + diff 뷰 | 검증: build

### F5-05. 다크모드/라이트모드 토글 강화 — 난이도 S
- [P5-13] frontend: next-themes 연동 + 시스템 설정 자동 감지 | 검증: build

### F5-06. 대시보드 커스터마이징 — 난이도 M
- [P5-14] frontend/components/dashboard/CustomizableDashboard.tsx: 위젯 드래그앤드롭 배치 | 검증: build
- [P5-15] frontend/stores/dashboardStore.ts: 대시보드 레이아웃 상태 관리 | 검증: tsc

### F5-07. 키보드 단축키 시스템 — 난이도 S
- [P5-16] frontend/hooks/useKeyboardShortcuts.ts: 글로벌 키보드 단축키 훅 | 검증: build
- [P5-17] frontend/components/ui/ShortcutHints.tsx: 단축키 안내 오버레이 | 검증: build

### F5-08. 무한 스크롤 히스토리 — 난이도 S
- [P5-18] frontend/hooks/useInfiniteHistory.ts: 히스토리 무한 스크롤 (TanStack Query) | 검증: build

### F5-09. 콘텐츠 검색 (전문 검색) — 난이도 M
- [P5-19] services/search_service.py: 생성된 콘텐츠 전문 검색 (FTS) | 검증: pytest
- [P5-20] frontend/components/search/GlobalSearch.tsx: 전역 검색 UI | 검증: build

### F5-10. 드래그앤드롭 URL 정렬 — 난이도 S
- **기존**: UrlInput.tsx
- [P5-21] frontend/components/input/UrlInput.tsx: dnd-kit 기반 URL 순서 변경 | 검증: build

### F5-11. 콘텐츠 폴더/카테고리 — 난이도 M
- [P5-22] services/folder_service.py: 콘텐츠 폴더/태그 CRUD | 검증: pytest
- [P5-23] frontend/components/library/FolderTree.tsx: 폴더 트리 사이드바 | 검증: build

### F5-12. 즐겨찾기/북마크 — 난이도 S
- [P5-24] frontend/stores/resultStore.ts: 즐겨찾기 상태 추가 | 검증: tsc
- [P5-25] frontend/components/result/FavoriteButton.tsx: 별표 즐겨찾기 버튼 | 검증: build

### F5-13. 알림 센터 — 난이도 M
- [P5-26] services/notification_service.py: 앱내 알림 (생성완료, 예약발행, 팀 초대 등) | 검증: pytest
- [P5-27] frontend/components/layout/NotificationCenter.tsx: 알림 드롭다운 UI | 검증: build

### F5-14. 모바일 반응형 강화 — 난이도 M
- [P5-28] frontend: 전체 레이아웃 모바일 반응형 점검 + 터치 최적화 | 검증: build

### F5-15. PWA (Progressive Web App) — 난이도 M
- [P5-29] frontend/public/manifest.json: PWA 매니페스트 | 검증: Lighthouse
- [P5-30] frontend: Service Worker 등록 (next-pwa) | 검증: 오프라인 테스트

### F5-16. 국제화(i18n) 확장 — 난이도 M
- **기존**: lib/i18n/ 존재
- [P5-31] frontend/lib/i18n/: 영어/일본어 번역 파일 완성 | 검증: build

### F5-17. 접근성(a11y) 강화 — 난이도 M
- [P5-32] frontend: ARIA 속성 + 포커스 관리 + 스크린 리더 호환 점검 | 검증: axe-core

### F5-18. 온보딩 투어 — 난이도 S
- **기존**: OnboardingModal.tsx 존재
- [P5-33] frontend/components/onboarding/GuidedTour.tsx: 단계별 인터랙티브 투어 (react-joyride) | 검증: build

### F5-19. 토스트 알림 개선 — 난이도 S
- [P5-34] frontend: sonner 토스트 액션 버튼 (되돌리기, 보기) 추가 | 검증: build

### F5-20. 스켈레톤 로딩 강화 — 난이도 S
- **기존**: LoadingSkeleton.tsx 존재
- [P5-35] frontend: 모든 비동기 컴포넌트에 스켈레톤 적용 | 검증: build

### F5-21. 에러 바운더리 + 복구 — 난이도 S
- **기존**: error.tsx, global-error.tsx 존재
- [P5-36] frontend: 컴포넌트별 에러 바운더리 + "다시 시도" 버튼 | 검증: build

### F5-22. 앱 내 도움말/FAQ — 난이도 M
- [P5-37] frontend/components/help/HelpPanel.tsx: 사이드 패널 도움말 + 검색 | 검증: build

### F5-23. 사용자 프로필 페이지 — 난이도 M
- [P5-38] frontend/app/profile/page.tsx: 프로필 (아바타, 이름, 구독, 사용량, API키) | 검증: build

### F5-24. 활동 피드 — 난이도 M
- [P5-39] services/activity_feed_service.py: 팀 활동 피드 (생성/편집/발행 기록) | 검증: pytest
- [P5-40] frontend/components/workspace/ActivityFeed.tsx: 활동 피드 UI | 검증: build

### F5-25. 컨텍스트 메뉴 — 난이도 S
- [P5-41] frontend/components/result/ContextMenu.tsx: 우클릭 컨텍스트 메뉴 (복사/편집/내보내기) | 검증: build

---

## Phase 6: 분석 & 인사이트

### F6-01. 운영 대시보드 고도화 — 난이도 M
- **기존**: OperationsDashboard.tsx, /api/admin/dashboard
- [P6-01] routes/auth_routes.py: /api/admin/dashboard 확장 (30일, 스타일별, 모델별 통계) | 검증: pytest
- [P6-02] frontend/components/dashboard/OperationsDashboard.tsx: 차트 추가 (Recharts) | 검증: build

### F6-02. 콘텐츠 성과 추적 — 난이도 L
- [P6-03] services/analytics/performance_service.py: 콘텐츠별 조회수/공유수/클릭률 추적 | 검증: pytest
- [P6-04] frontend/components/dashboard/PerformanceChart.tsx: 성과 차트 | 검증: build

### F6-03. Google Analytics 연동 — 난이도 M
- [P6-05] services/analytics/ga_service.py: GA4 Data API → 콘텐츠별 트래픽 데이터 수집 | 검증: pytest
- [P6-06] frontend/components/settings/GAConnect.tsx: GA 연결 설정 UI | 검증: build

### F6-04. Google Search Console 연동 — 난이도 M
- [P6-07] services/analytics/gsc_service.py: GSC API → 검색 순위/CTR 데이터 | 검증: pytest

### F6-05. 비용 추적 (API 사용 비용) — 난이도 M
- [P6-08] services/analytics/cost_tracker_service.py: 모델별 토큰 → 실 비용 계산 | 검증: pytest
- [P6-09] frontend/components/dashboard/CostDashboard.tsx: 비용 차트 + 예산 설정 | 검증: build

### F6-06. 콘텐츠 캘린더 강화 — 난이도 M
- **기존**: ContentCalendar.tsx, schedule_service.py
- [P6-10] frontend/components/schedule/ContentCalendar.tsx: 드래그앤드롭 일정 변경 + 월/주/일 뷰 | 검증: build

### F6-07. 트렌드 키워드 모니터 — 난이도 M
- [P6-11] services/analytics/trend_monitor_service.py: Google Trends API → 키워드 트렌드 추적 | 검증: pytest
- [P6-12] frontend/components/dashboard/TrendMonitor.tsx: 트렌드 키워드 목록 + 알림 | 검증: build

### F6-08. 콘텐츠 ROI 계산기 — 난이도 M
- [P6-13] services/analytics/roi_calculator_service.py: 생성 비용 vs 트래픽 가치 계산 | 검증: pytest

### F6-09. 히트맵 분석 — 난이도 L
- [P6-14] services/analytics/heatmap_service.py: 콘텐츠 내 읽기 패턴 히트맵 | 검증: pytest

### F6-10. A/B 테스트 결과 추적 — 난이도 M
- [P6-15] services/analytics/ab_test_service.py: 제목/스타일 A/B 테스트 결과 저장/비교 | 검증: pytest
- [P6-16] frontend/components/dashboard/ABTestResults.tsx: A/B 테스트 결과 UI | 검증: build

### F6-11. 사용자 행동 분석 — 난이도 M
- [P6-17] services/analytics/user_behavior_service.py: 기능별 사용 빈도, 세션 길이, 이탈 지점 | 검증: pytest

### F6-12. 콘텐츠 품질 트렌드 — 난이도 S
- [P6-18] services/analytics/quality_trend_service.py: 시간에 따른 품질 점수 추이 | 검증: pytest

### F6-13. 스타일별 성과 비교 — 난이도 M
- [P6-19] services/analytics/style_performance_service.py: 14개 스타일별 평균 품질/성과 비교 | 검증: pytest

### F6-14. 모델별 성능 비교 — 난이도 M
- [P6-20] services/analytics/model_benchmark_service.py: 프로바이더/모델별 속도/비용/품질 벤치마크 | 검증: pytest
- [P6-21] frontend/components/dashboard/ModelBenchmark.tsx: 모델 비교 차트 | 검증: build

### F6-15. 실시간 모니터링 — 난이도 M
- [P6-22] services/analytics/realtime_monitor_service.py: 현재 활성 생성 수, 큐 깊이, 에러율 | 검증: pytest

### F6-16. 이상 탐지 알림 — 난이도 M
- [P6-23] services/analytics/anomaly_service.py: 사용량/에러율 이상치 감지 → 알림 | 검증: pytest

### F6-17. 커스텀 리포트 빌더 — 난이도 L
- [P6-24] frontend/components/dashboard/ReportBuilder.tsx: 드래그앤드롭 차트 조합 리포트 | 검증: build

### F6-18. 데이터 내보내기 (CSV/JSON) — 난이도 S
- [P6-25] routes/auth_routes.py: /api/admin/export-data (CSV/JSON) 엔드포인트 | 검증: pytest

### F6-19. Slack 알림 연동 — 난이도 M
- [P6-26] services/integrations/slack_service.py: Slack Webhook → 생성 완료/에러 알림 | 검증: pytest
- [P6-27] frontend/components/settings/SlackConnect.tsx: Slack 연결 설정 | 검증: build

### F6-20. Discord 알림 연동 — 난이도 S
- [P6-28] services/integrations/discord_service.py: Discord Webhook 알림 | 검증: pytest

### F6-21. 이메일 알림 — 난이도 M
- [P6-29] services/email_service.py: SMTP/SendGrid 이메일 발송 서비스 | 검증: pytest

### F6-22. Zapier 웹훅 강화 — 난이도 M
- **기존**: webhook_service.py
- [P6-30] services/webhook_service.py: 이벤트별 웹훅 (생성완료/발행완료/에러) 분리 | 검증: pytest

### F6-23. 주간 다이제스트 자동 생성 — 난이도 M
- [P6-31] services/digest_service.py: 주간 생성 콘텐츠 요약 다이제스트 자동 생성 | 검증: pytest

### F6-24. 대시보드 공유 링크 — 난이도 M
- [P6-32] routes/auth_routes.py: /api/dashboard/share — 읽기전용 대시보드 공유 | 검증: pytest

### F6-25. 실시간 로그 뷰어 — 난이도 M
- [P6-33] routes/utility_routes.py: /api/logs/stream — SSE 실시간 로그 스트리밍 | 검증: pytest
- [P6-34] frontend/components/dashboard/LogViewer.tsx: 로그 뷰어 UI | 검증: build

---

## Phase 7: 통합 & 플러그인

### F7-01. Chrome 확장 프로그램 — 난이도 L
- [P7-01] chrome-extension/manifest.json: Manifest V3 확장 프로그램 기본 구조 | 검증: 로드
- [P7-02] chrome-extension/popup.html: 현재 페이지 URL → 생성 버튼 | 검증: 동작
- [P7-03] chrome-extension/content.js: 페이지 텍스트 선택 → 우클릭 메뉴 → 생성 | 검증: 동작

### F7-02. Slack 봇 — 난이도 L
- [P7-04] services/integrations/slack_bot_service.py: Slack Bot (URL 공유 → 자동 생성) | 검증: pytest

### F7-03. Discord 봇 — 난이도 L
- [P7-05] services/integrations/discord_bot_service.py: Discord Bot (명령어 기반 생성) | 검증: pytest

### F7-04. Telegram 봇 — 난이도 M
- [P7-06] services/integrations/telegram_bot_service.py: Telegram Bot (URL 전송 → 생성) | 검증: pytest

### F7-05. Zapier 통합 — 난이도 M
- [P7-07] routes/integration_routes.py: Zapier 트리거/액션 API 구현 | 검증: pytest

### F7-06. Make (Integromat) 통합 — 난이도 M
- [P7-08] routes/integration_routes.py: Make 호환 웹훅 엔드포인트 | 검증: pytest

### F7-07. n8n 노드 — 난이도 M
- [P7-09] n8n-nodes/InsightEngine/InsightEngine.node.ts: n8n 커스텀 노드 | 검증: 동작

### F7-08. REST API 문서 (OpenAPI) — 난이도 M
- [P7-10] services/openapi_service.py: Flask 라우트 → OpenAPI 3.0 스펙 자동 생성 | 검증: pytest
- [P7-11] frontend/app/docs/page.tsx: Swagger UI 내장 API 문서 | 검증: build

### F7-09. GraphQL API — 난이도 L
- [P7-12] routes/graphql_routes.py: GraphQL 엔드포인트 (Strawberry) | 검증: pytest

### F7-10. 플러그인 SDK — 난이도 L
- [P7-13] services/mcp/plugin_sdk.py: 서드파티 플러그인 개발 SDK | 검증: pytest
- [P7-14] docs/plugin-sdk-guide.md: 플러그인 개발 가이드 | 검증: 문서 검토

### F7-11. Tistory 플러그인 — 난이도 M
- [P7-15] services/mcp/plugins/tistory.py: Tistory Open API 발행 플러그인 | 검증: pytest

### F7-12. Velog 플러그인 — 난이도 M
- [P7-16] services/mcp/plugins/velog.py: Velog API 발행 플러그인 | 검증: pytest

### F7-13. Ghost CMS 플러그인 — 난이도 M
- [P7-17] services/mcp/plugins/ghost.py: Ghost Admin API 발행 플러그인 | 검증: pytest

### F7-14. Shopify 블로그 플러그인 — 난이도 M
- [P7-18] services/mcp/plugins/shopify.py: Shopify Blog API 발행 | 검증: pytest

### F7-15. LinkedIn 발행 — 난이도 M
- [P7-19] services/mcp/plugins/linkedin.py: LinkedIn API 포스트 발행 | 검증: pytest

### F7-16. Twitter/X 발행 — 난이도 M
- [P7-20] services/mcp/plugins/twitter.py: X API v2 트윗/스레드 발행 | 검증: pytest

### F7-17. Instagram 발행 — 난이도 M
- [P7-21] services/mcp/plugins/instagram.py: Instagram Graph API 포스트 발행 | 검증: pytest

### F7-18. Threads 발행 — 난이도 M
- [P7-22] services/mcp/plugins/threads.py: Threads API 발행 | 검증: pytest

### F7-19. Webhook Relay — 난이도 M
- [P7-23] services/webhook_relay_service.py: 생성 이벤트 → 다중 웹훅 동시 발송 | 검증: pytest

### F7-20. IFTTT 연동 — 난이도 S
- [P7-24] routes/integration_routes.py: IFTTT Webhook 트리거 | 검증: pytest

### F7-21. Airtable 동기화 — 난이도 M
- [P7-25] services/integrations/airtable_service.py: 콘텐츠 → Airtable 자동 기록 | 검증: pytest

### F7-22. Google Sheets 동기화 — 난이도 M
- [P7-26] services/integrations/gsheets_service.py: 생성 기록 → Google Sheets 자동 동기화 | 검증: pytest

### F7-23. CMS 통합 허브 — 난이도 L
- [P7-27] services/mcp/cms_hub.py: CMS 통합 인터페이스 (하나의 API로 다중 CMS 발행) | 검증: pytest

### F7-24. 앱 내 피드백 위젯 — 난이도 S
- [P7-28] frontend/components/feedback/FeedbackWidget.tsx: 피드백 수집 위젯 | 검증: build

### F7-25. OAuth 2.0 공급자 — 난이도 L
- [P7-29] services/auth/oauth_provider_service.py: 타사 앱에 OAuth 2.0 인증 제공 | 검증: pytest

---

## Phase 8: 콘텐츠 관리 & 라이브러리

### F8-01. 콘텐츠 라이브러리 — 난이도 M
- [P8-01] frontend/app/library/page.tsx: 생성된 콘텐츠 라이브러리 (그리드/리스트 뷰) | 검증: build
- [P8-02] services/content_library_service.py: 콘텐츠 CRUD + 검색 + 필터 | 검증: pytest

### F8-02. 템플릿 갤러리 강화 — 난이도 M
- **기존**: TemplateGalleryModal.tsx, api.ts의 getTemplates()
- [P8-03] frontend/components/modals/TemplateGalleryModal.tsx: 카테고리별 필터 + 인기순 정렬 + 미리보기 | 검증: build

### F8-03. 스니펫 라이브러리 강화 — 난이도 S
- **기존**: SnippetLibrary.tsx
- [P8-04] frontend/components/settings/SnippetLibrary.tsx: 태그 + 검색 + 즐겨찾기 추가 | 검증: build

### F8-04. 콘텐츠 상태 관리 (Kanban) — 난이도 M
- [P8-05] frontend/components/library/KanbanBoard.tsx: 초안→검토→승인→발행 칸반 보드 | 검증: build

### F8-05. 일괄 작업 (Bulk Actions) — 난이도 M
- [P8-06] routes/blog_routes.py: /api/content/bulk 엔드포인트 (일괄 삭제/태그/내보내기) | 검증: pytest
- [P8-07] frontend/components/library/BulkActions.tsx: 체크박스 선택 → 일괄 작업 바 | 검증: build

### F8-06. 콘텐츠 복제 — 난이도 S
- [P8-08] routes/blog_routes.py: /api/content/<id>/clone 엔드포인트 | 검증: pytest

### F8-07. 콘텐츠 아카이브 — 난이도 S
- [P8-09] services/archive_service.py: 콘텐츠 아카이브/복원 | 검증: pytest

### F8-08. 콘텐츠 잠금 (동시 편집 방지) — 난이도 M
- [P8-10] services/lock_service.py: 편집 중 콘텐츠 잠금 (TTL 기반) | 검증: pytest

### F8-09. 콘텐츠 만료 자동 관리 — 난이도 M
- [P8-11] services/expiry_service.py: 만료일 설정 → 자동 아카이브/삭제 | 검증: pytest

### F8-10. 미디어 라이브러리 — 난이도 M
- [P8-12] services/media_library_service.py: 업로드된 이미지/오디오/파일 중앙 관리 | 검증: pytest
- [P8-13] frontend/components/library/MediaLibrary.tsx: 미디어 브라우저 UI | 검증: build

### F8-11. 커스텀 필드 — 난이도 M
- [P8-14] services/custom_field_service.py: 콘텐츠에 사용자 정의 메타데이터 필드 추가 | 검증: pytest

### F8-12. 콘텐츠 링크 관리 — 난이도 M
- [P8-15] services/link_manager_service.py: 콘텐츠 내 모든 링크 추출/검증/업데이트 | 검증: pytest

### F8-13. SEO 체크리스트 — 난이도 M
- [P8-16] services/seo_checklist_service.py: 발행 전 SEO 항목 자동 체크 (메타/이미지/구조) | 검증: pytest
- [P8-17] frontend/components/result/SeoChecklist.tsx: SEO 체크리스트 UI | 검증: build

### F8-14. 콘텐츠 임베드 — 난이도 M
- [P8-18] routes/utility_routes.py: /embed/<id> — 외부 사이트에 임베드 가능한 HTML | 검증: pytest

### F8-15. 콘텐츠 공유 링크 — 난이도 M
- [P8-19] services/share_service.py: 공개 공유 링크 생성 (만료 시간 설정) | 검증: pytest
- [P8-20] frontend/app/share/[id]/page.tsx: 공유 페이지 | 검증: build

### F8-16. 콘텐츠 댓글 — 난이도 M
- [P8-21] services/comment_service.py: 팀원 간 콘텐츠 댓글/리뷰 | 검증: pytest
- [P8-22] frontend/components/result/CommentThread.tsx: 댓글 스레드 UI | 검증: build

### F8-17. 콘텐츠 워크플로우 자동화 — 난이도 L
- [P8-23] services/workflow_service.py: 조건 기반 자동화 (생성완료 → QA → 승인요청 → 발행) | 검증: pytest

### F8-18. 다중 워크스페이스 전환 — 난이도 M
- **기존**: WorkspaceSelector.tsx, workspace_service.py
- [P8-24] frontend/components/layout/WorkspaceSelector.tsx: 워크스페이스 간 빠른 전환 + 생성 | 검증: build

### F8-19. 역할 기반 접근 제어 (RBAC) 강화 — 난이도 M
- [P8-25] services/rbac_service.py: 세분화된 권한 (콘텐츠별/기능별 접근 제어) | 검증: pytest

### F8-20. 콘텐츠 통계 요약 — 난이도 S
- [P8-26] frontend/components/library/ContentStats.tsx: 총 생성수, 평균 품질, 인기 스타일 등 | 검증: build

### F8-21. 콘텐츠 비교 뷰 — 난이도 M
- [P8-27] frontend/components/result/CompareView.tsx: 2개 콘텐츠 나란히 비교 | 검증: build

### F8-22. 자동 백업 — 난이도 M
- [P8-28] services/backup_service.py: 일별 자동 백업 (로컬 + 클라우드) | 검증: pytest

### F8-23. 데이터 가져오기/내보내기 — 난이도 M
- [P8-29] services/data_migration_service.py: 전체 데이터 JSON 내보내기/가져오기 | 검증: pytest

### F8-24. 휴지통 (Soft Delete) — 난이도 S
- [P8-30] services/trash_service.py: 삭제된 콘텐츠 30일 보관 후 영구 삭제 | 검증: pytest

### F8-25. 콘텐츠 핀 (고정) — 난이도 S
- [P8-31] frontend/stores/resultStore.ts: 핀 상태 추가 + 상단 고정 표시 | 검증: build

---

## Phase 9: 인프라 & 성능

### F9-01. Redis 캐싱 레이어 — 난이도 M
- **기존**: cache_service.py (인메모리)
- [P9-01] services/cache_service.py: Redis 백엔드 추가 (옵셔널, 폴백은 인메모리) | 검증: pytest

### F9-02. 작업 큐 (Celery/RQ) — 난이도 L
- [P9-02] services/task_queue_service.py: 비동기 작업 큐 (장시간 생성을 백그라운드로) | 검증: pytest
- [P9-03] workers/content_worker.py: 콘텐츠 생성 워커 프로세스 | 검증: pytest

### F9-03. 데이터베이스 마이그레이션 — 난이도 M
- [P9-04] migrations/: Alembic 마이그레이션 설정 (SQLAlchemy 모델 정의) | 검증: migrate

### F9-04. API Rate Limiting 강화 — 난이도 S
- **기존**: Flask-Limiter
- [P9-05] routes/: 엔드포인트별 세분화된 rate limit 설정 | 검증: pytest

### F9-05. 헬스체크 강화 — 난이도 S
- [P9-06] routes/utility_routes.py: /health 심층 헬스체크 (DB/Redis/AI/디스크) | 검증: pytest

### F9-06. 구조화된 로깅 — 난이도 M
- [P9-07] services/logging_config.py: JSON 구조화 로그 + 요청 ID 추적 | 검증: pytest

### F9-08. 에러 추적 (Sentry) — 난이도 S
- [P9-08] app.py: Sentry SDK 통합 | 검증: 에러 발생 테스트

### F9-09. 메트릭 수집 (Prometheus) — 난이도 M
- [P9-09] services/metrics_service.py: Prometheus 메트릭 엔드포인트 | 검증: /metrics 접근

### F9-10. Docker 컨테이너화 — 난이도 M
- [P9-10] Dockerfile: 멀티스테이지 빌드 (Python + Node.js) | 검증: docker build
- [P9-11] docker-compose.yml: 앱 + Redis + ChromaDB 통합 | 검증: docker-compose up

### F9-11. CI/CD 파이프라인 — 난이도 M
- [P9-12] .github/workflows/ci.yml: GitHub Actions (lint + test + build) | 검증: 워크플로우 실행

### F9-12. 로드 밸런싱 대비 — 난이도 M
- [P9-13] config.py: 세션/캐시를 외부 스토어(Redis)로 분리하여 수평 확장 대비 | 검증: pytest

### F9-13. CDN 정적 파일 서빙 — 난이도 S
- [P9-14] frontend/next.config.ts: assetPrefix CDN 설정 | 검증: build

### F9-14. 이미지 최적화 — 난이도 S
- [P9-15] frontend: next/image 컴포넌트 활용 + WebP 자동 변환 | 검증: build

### F9-15. 번들 사이즈 최적화 — 난이도 M
- [P9-16] frontend: dynamic import + 코드 스플리팅 강화 | 검증: npm run build (분석)

### F9-16. API 응답 압축 — 난이도 S
- [P9-17] app.py: gzip/brotli 응답 압축 미들웨어 | 검증: 응답 헤더 확인

### F9-17. 커넥션 풀링 — 난이도 S
- [P9-18] services/supabase_service.py: Supabase 커넥션 풀 최적화 | 검증: 부하 테스트

### F9-18. 요청 검증 미들웨어 — 난이도 M
- [P9-19] middleware/request_validator.py: JSON Schema 기반 요청 자동 검증 | 검증: pytest

### F9-19. 그레이스풀 셧다운 — 난이도 S
- [P9-20] app.py: SIGTERM 처리 → 진행 중 요청 완료 후 종료 | 검증: 시그널 테스트

### F9-20. 환경별 설정 분리 — 난이도 S
- [P9-21] config.py: development/staging/production 환경별 설정 클래스 분리 | 검증: pytest

### F9-21. 시크릿 관리 — 난이도 M
- [P9-22] services/secret_manager_service.py: 환경변수 + Vault 통합 시크릿 관리 | 검증: pytest

### F9-22. 데이터 암호화 — 난이도 M
- [P9-23] services/encryption_service.py: 민감 데이터 AES 암호화 (at-rest) | 검증: pytest

### F9-23. 요청 추적 (Request Tracing) — 난이도 M
- [P9-24] middleware/tracing.py: OpenTelemetry 기반 분산 추적 | 검증: 트레이스 확인

### F9-24. 자동 스케일링 설정 — 난이도 M
- [P9-25] k8s/: Kubernetes HPA 설정 | 검증: 문서 검토

### F9-25. 부하 테스트 스크립트 — 난이도 M
- [P9-26] tests/load/locustfile.py: Locust 부하 테스트 시나리오 | 검증: locust 실행

---

## Phase 10: 고급 AI & 미래 기술

### F10-01. LLM 파인튜닝 파이프라인 — 난이도 XL
- [P10-01] services/finetune/dataset_builder.py: 생성 히스토리 → 학습 데이터셋 자동 구축 | 검증: pytest
- [P10-02] services/finetune/training_service.py: LoRA 파인튜닝 실행 (LlamaFactory 연동) | 검증: pytest

### F10-02. RLHF/DPO 보상 학습 — 난이도 XL
- [P10-03] services/finetune/reward_model.py: 사용자 피드백 → 보상 모델 학습 | 검증: pytest

### F10-03. 음성 복제 TTS — 난이도 L
- [P10-04] services/voice_clone_service.py: OpenVoice/GPT-SoVITS 연동 → 사용자 목소리 복제 | 검증: pytest

### F10-04. 다화자 대화 TTS — 난이도 L
- [P10-05] services/dialogue_tts_service.py: Dia 모델 연동 → 2인 대화체 오디오 생성 | 검증: pytest

### F10-05. 실시간 스트리밍 TTS — 난이도 M
- [P10-06] services/tts_service.py: WebSocket 기반 실시간 TTS 스트리밍 | 검증: pytest

### F10-06. 텍스트 → 비디오 생성 — 난이도 XL
- [P10-07] services/video_gen_service.py: Runway/Pika API 연동 → 텍스트 기반 영상 생성 | 검증: pytest

### F10-07. 자동 자막 생성 + 번역 — 난이도 M
- [P10-08] services/auto_subtitle_service.py: 영상 → Whisper 자막 → 다국어 번역 | 검증: pytest

### F10-08. AI 기반 썸네일 A/B 테스트 — 난이도 L
- [P10-09] services/thumbnail_ab_service.py: N개 썸네일 생성 → CTR 기반 자동 선택 | 검증: pytest

### F10-09. MCP 서버 (외부 노출) — 난이도 L
- [P10-10] services/mcp/mcp_server.py: Insight Engine을 MCP 서버로 노출 (외부 AI 에이전트가 콘텐츠 생성 도구로 활용) | 검증: pytest

### F10-10. 에이전트 마켓플레이스 — 난이도 XL
- [P10-11] services/agent/marketplace.py: 커뮤니티 에이전트 파이프라인 공유/설치 | 검증: pytest

### F10-11. 지식 그래프 시각화 — 난이도 M
- [P10-12] frontend/components/knowledge/GraphVisualization.tsx: D3.js force-directed 그래프 UI | 검증: build

### F10-12. 벡터 DB 성능 최적화 — 난이도 M
- [P10-13] services/rag/vector_store.py: 배치 임베딩 + 인덱스 최적화 + 캐싱 | 검증: 벤치마크

### F10-13. Embedding 모델 선택 — 난이도 M
- [P10-14] config.py: EMBEDDING_MODEL 설정 (OpenAI/Cohere/로컬 모델 선택) | 검증: pytest

### F10-14. 멀티모달 RAG — 난이도 L
- [P10-15] services/rag/multimodal_rag.py: 이미지+텍스트 통합 검색 | 검증: pytest

### F10-15. 자동 학습 데이터 수집 — 난이도 M
- [P10-16] services/finetune/data_collector.py: 사용자 편집 기록 → preference 데이터 자동 수집 | 검증: pytest

### F10-16. AI 에디터 (Copilot) — 난이도 L
- [P10-17] services/copilot_service.py: 콘텐츠 편집 중 AI 자동완성 제안 | 검증: pytest
- [P10-18] frontend/components/editor/CopilotSuggestion.tsx: 인라인 AI 제안 UI | 검증: build

### F10-17. 콘텐츠 시뮬레이터 — 난이도 M
- [P10-19] services/simulator_service.py: "이 콘텐츠를 발행하면?" → SEO/트래픽 예측 | 검증: pytest

### F10-18. 콘텐츠 복잡도 분석 — 난이도 S
- [P10-20] services/complexity_service.py: 전문 용어 밀도, 문장 복잡도 분석 | 검증: pytest

### F10-19. 자동 내부 링크 네트워크 — 난이도 M
- [P10-21] services/link_network_service.py: 전체 콘텐츠 간 연결 그래프 + 자동 링크 삽입 | 검증: pytest

### F10-20. 콘텐츠 재활용 추천 — 난이도 M
- [P10-22] services/repurpose_service.py: 기존 콘텐츠 → "이걸 뉴스레터/SNS/슬라이드로 변환하세요" 추천 | 검증: pytest

### F10-21. WebGPU 가속 (프론트엔드) — 난이도 L
- [P10-23] frontend/lib/webgpu-inference.ts: 소형 모델 프론트엔드 추론 (요약/분류) | 검증: build

### F10-22. Edge Functions 활용 — 난이도 M
- [P10-24] frontend/app/api/: Next.js Edge Runtime API Routes (빠른 응답) | 검증: build

### F10-23. 실시간 번역 — 난이도 M
- [P10-25] services/realtime_translate_service.py: 콘텐츠 편집 중 실시간 번역 사이드바 | 검증: pytest

### F10-24. AI 요약 뉴스레터 자동 발송 — 난이도 L
- [P10-26] services/auto_newsletter_service.py: RSS+리서치 → 주간 뉴스레터 자동 생성+발송 | 검증: pytest

### F10-25. 콘텐츠 지문 (Fingerprint) — 난이도 M
- [P10-27] services/fingerprint_service.py: 콘텐츠별 고유 해시 → 도용/복제 추적 | 검증: pytest

### F10-26. AI 모델 라우터 — 난이도 M
- [P10-28] services/model_router_service.py: 작업 유형별 최적 모델 자동 선택 (비용/품질 밸런스) | 검증: pytest

### F10-27. 프롬프트 버전 관리 — 난이도 M
- [P10-29] services/prompt_version_service.py: 프롬프트 Git-like 버전 관리 (diff/rollback) | 검증: pytest

### F10-28. 콘텐츠 파이프라인 모니터 — 난이도 M
- [P10-30] frontend/components/pipeline/PipelineMonitor.tsx: 실행 중 파이프라인 실시간 모니터링 대시보드 | 검증: build

---

## 병렬 실행 그래프 (Phase 간)

```
Phase 1 (입력)  ──┐
Phase 2 (출력)  ──┤──→ Phase 6 (분석) ──→ Phase 9 (인프라)
Phase 3 (AI)    ──┤                         ↓
Phase 5 (UX)    ──┘──→ Phase 8 (관리) ──→ Phase 10 (고급AI)
Phase 4 (과금)  ──────→ Phase 7 (통합) ──┘

Phase 1~5: 병렬 착수 가능 (상호 의존성 없음)
Phase 6~8: Phase 1~5 중 관련 기능 완료 후
Phase 9~10: 전체 기반 안정화 후
```

### Phase 내부 병렬도

| Phase | 총 태스크 | 병렬 가능 | 병렬도 |
|-------|----------|----------|--------|
| 1     | 49       | 45       | 91.8%  |
| 2     | 46       | 40       | 87.0%  |
| 3     | 45       | 40       | 88.9%  |
| 4     | 47       | 42       | 89.4%  |
| 5     | 41       | 38       | 92.7%  |
| 6     | 34       | 30       | 88.2%  |
| 7     | 29       | 25       | 86.2%  |
| 8     | 31       | 28       | 90.3%  |
| 9     | 26       | 22       | 84.6%  |
| 10    | 30       | 25       | 83.3%  |
| **총** | **378** | **335** | **88.6%** |

---

## 다음 단계

1. **`/plan` 실행** — 단일 에이전트가 Phase 1부터 순차 진행
2. **에이전트 팀 실행** (권장) — Phase 1~5를 5개 팀메이트가 병렬 진행
   - 각 팀메이트는 worktree 격리 환경에서 독립 작업
   - 완료 후 팀 리드가 머지 + 통합 테스트
3. **Phase 단위 선택 실행** — "Phase 1만 먼저" 등 부분 실행
4. **기능 체리픽** — "F1-01, F2-01, F4-01만" 등 개별 선택

> **추천**: Phase 1 (입력 확장) + Phase 4 (수익화)를 먼저 실행하여
> YouTube 전용 → 범용 플랫폼 전환 + 비즈니스 모델 확보를 동시에 달성
