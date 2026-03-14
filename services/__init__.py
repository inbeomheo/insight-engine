"""
서비스 모듈 패키지 — 도메인별 서브디렉토리 구조

- core/: AI, 콘텐츠 생성, 파이프라인, 캐시
- analysis/: 텍스트/NLP 분석 (가독성, 구조, 문장, 감정)
- seo/: 검색 최적화 (키워드, 메타, SERP, E-E-A-T)
- quality/: 품질 검증 (QA, 표절, 팩트체크)
- media/: 미디어 생성 (썸네일, 이미지, 비디오, TTS)
- export/: 내보내기 (DOCX, EPUB, Google Docs)
- transcript/: 자막/음성 (Whisper, 챕터, 번역)
- content/: 콘텐츠 관리 (인용, 리라이트, FAQ, 요약)
- platform/: 외부 플랫폼 (웹훅, RSS, GitHub, SNS)
- data/: 데이터/인프라 (Supabase, 스케줄, 알림, 버전)
- agents/: 멀티에이전트 파이프라인
- auth/: 인증/OAuth
- analytics/: 분석 대시보드
- integrations/: 외부 서비스 연동 (Slack, Discord, Telegram)
- mcp/: MCP 플러그인
- payment/: 결제/구독
- rag/: RAG 벡터 스토어
- usage/: 사용량 관리
- finetune/: AI 파인튜닝
- exceptions/: 에러 처리
"""
