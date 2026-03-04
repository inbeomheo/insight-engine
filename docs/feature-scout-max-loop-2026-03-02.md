# Feature Scout Max Loop Report (2026-03-02)

## 실행 요약

- 스카우팅 반복 라운드: 11+ 라운드
- GitHub 검색 쿼리: 33개
- 수집 레포(raw): 621개
- 중복 제거 레포: 511개
- 최근성 필터(2024-03-02 이후 업데이트): 490개
- README 기능 스니펫 직접 추출 레포: 14개

## 현재 프로젝트 기준(중복 제외용 베이스라인)

현재 이미 구현된 핵심 기능(README/라우트 기준):
- 다중 AI 프로바이더
- 13개 스타일 + 다국어 출력
- 배치/합치기/퓨전 분석
- Whisper 자막 폴백
- 파이프라인 자동화(SSE)
- MCP 발행(Naver/WordPress)
- 예약 캘린더
- 워크스페이스 협업
- RAG 업로드/참조
- 웹훅
- 마인드맵/실시간 스트리밍/커스텀 스타일

아래 추천은 위 기능과 겹치는 항목을 제외하고 정리함.

## 기능 추천

### 필수 기능 (우선순위: 높음)

1. **챕터 자동 분할 + 클릭 타임라인 네비게이션** - 난이도: 중  
   이유: 영상 요약 UX의 체감 품질을 크게 끌어올리고, 긴 영상 탐색 비용을 줄임.  
   근거: [S1], [S10]

2. **트랜스크립트 워크스페이스(문장 단위 탐색/수정/하이라이트)** - 난이도: 중  
   이유: 요약 결과 검증과 편집 품질 개선에 직접적 효과.  
   근거: [S1], [S6]

3. **채널/플레이리스트 단위 정기 요약 파이프라인** - 난이도: 중  
   이유: 단일 URL 처리에서 운영형 워크플로우로 확장 가능.  
   근거: [S2]

4. **YouTube 외 멀티소스 수집(파일 업로드/URL 다중 플랫폼)** - 난이도: 상  
   이유: 콘텐츠 입력 채널을 넓혀 재사용률과 리텐션 증가.  
   근거: [S4], [S3]

5. **핵심 구간 자동 클립 추출(실제 영상 컷 생성)** - 난이도: 상  
   이유: 현재 텍스트 중심 결과를 숏폼 제작까지 확장 가능.  
   근거: [S3], [W2], [W3]

6. **결과물 패키지 일괄 출력(MP4/MP3/VTT/TXT/MD/ZIP)** - 난이도: 중  
   이유: 후속 제작 툴 연동과 재편집 파이프라인 효율 개선.  
   근거: [S3], [S4]

7. **언어별 자막 선택 + 번역 요약 파이프라인** - 난이도: 중  
   이유: 다국어 출력은 이미 있지만 입력 자막 언어 제어를 강화하면 정확도 향상.  
   근거: [S5], [S6]

8. **발행 워크플로우 강화(즉시/예약/큐/재시도 정책)** - 난이도: 중  
   이유: 운영 중 실패율/누락률을 줄이는 실무 기능.  
   근거: [S7], [W1]

9. **워크스페이스 승인 플로우(작성→리뷰→승인→발행)** - 난이도: 중  
   이유: 팀 협업 기능의 실제 운영 완성도 상승.  
   근거: [S7]

10. **소스 신뢰도/근거 링크 포함 요약 모드** - 난이도: 상  
    이유: 생성물 검증 가능성 확보(특히 B2B/리서치형 사용처).  
    근거: [S6], [S5]

### 인기 기능 (우선순위: 중간)

11. **9:16/1:1/16:9 자동 리프레임** - 난이도: 상  
    이유: 플랫폼별 재가공 비용 감소.  
    근거: [W2]

12. **자동 자막 스타일링(키워드 강조/테마 프리셋)** - 난이도: 중  
    이유: 숏폼 완성도와 업로드 즉시성 향상.  
    근거: [W2]

13. **클립 후보 점수화(훅/완결성/길이 기준)** - 난이도: 중  
    이유: 수작업 선별 시간을 절감.  
    근거: [W2], [W3]

14. **트랜스크립트 기반 편집 UI(문장 삭제=영상 컷 반영)** - 난이도: 상  
    이유: 비전문 사용자도 편집 가능.  
    근거: [W3]

15. **필러워드/침묵 구간 자동 정리 옵션** - 난이도: 중  
    이유: 자동 생성 영상/오디오 품질 개선.  
    근거: [W3], [S3]

16. **요약 상세도 프리셋(초간단/표준/심층) + 토큰 예산 제어** - 난이도: 하  
    이유: 비용/속도/품질 트레이드오프를 사용자에게 노출.  
    근거: [S10], [S1]

17. **채널 신규 업로드 감지 후 자동 작업 트리거** - 난이도: 중  
    이유: 반복 작업 자동화의 핵심 루프.  
    근거: [S2], [W1]

18. **스니펫 라이브러리(인트로/CTA/해시태그) 재사용** - 난이도: 하  
    이유: 다채널 운영 시 카피 생산성 향상.  
    근거: [W1], [W5]

19. **플랫폼별 카피 리라이트(톤/길이/포맷 자동 변환)** - 난이도: 중  
    이유: 동일 원천 콘텐츠의 재가공 자동화.  
    근거: [W5]

20. **게시 목표 기반 추천(빈도/도달/캠페인 목표)** - 난이도: 중  
    이유: 단순 생성 도구에서 운영 성과 도구로 확장.  
    근거: [W5], [W6]

### 차별화 기능 (우선순위: 선택)

21. **퍼포먼스 피드백 루프(게시 성과→다음 생성 전략 반영)** - 난이도: 상  
    이유: 장기적으로 품질이 자동 개선되는 구조.  
    근거: [W5], [S7]

22. **캠페인 팩 원클릭 생성(블로그+뉴스레터+숏폼+SNS 스레드)** - 난이도: 상  
    이유: 현재 다중 스타일을 실무 패키지로 승격.  
    근거: [S1], [W1]

23. **콘텐츠 운영 대시보드(큐 상태, 실패율, 채널별 처리량)** - 난이도: 중  
    이유: 대량 운영에서 필수인 가시성 확보.  
    근거: [S7], [W1]

24. **발행 전 QA 게이트(사실성/중복/금칙어/브랜드 규칙)** - 난이도: 중  
    이유: 자동 생성물 리스크 감소.  
    근거: [S6], [W5]

25. **프롬프트/템플릿 A/B 실험과 승자 자동 반영** - 난이도: 상  
    이유: 스타일 품질을 데이터 기반으로 개선 가능.  
    근거: [W5]

26. **헤드리스 퍼블리싱 API 확장(외부 워크플로우 친화)** - 난이도: 중  
    이유: SaaS/내부툴 연동성 강화.  
    근거: [S7]

27. **MCP 발행 채널 확장 마켓플레이스 구조** - 난이도: 상  
    이유: 기존 MCP 기반을 제품 확장 축으로 활용 가능.  
    근거: [S5], [S7]

28. **업로드 에셋 자동 정책 검사(저작권/길이/포맷 제약)** - 난이도: 상  
    이유: 멀티채널 자동 발행 시 운영 리스크 감소.  
    근거: [W1], [W2]

29. **AI 에디터 코파일럿(“이 문단 톤만 바꿔줘” 등 인라인 명령)** - 난이도: 중  
    이유: 최종 편집 시간을 줄이고 사용자 체감 품질 상승.  
    근거: [W3], [W5]

30. **자동 콘텐츠 갭 분석(최근 생성물/주제 중복 회피 추천)** - 난이도: 중  
    이유: 장기 운영 시 반복 콘텐츠 문제 완화.  
    근거: [W6], [S2]

## 분석에 사용한 대표 프로젝트

1. [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app)
2. [DevRico003/youtube_summarizer](https://github.com/DevRico003/youtube_summarizer)
3. [akashe/YoutubeSummarizer](https://github.com/akashe/YoutubeSummarizer)
4. [sidedwards/ai-video-summarizer](https://github.com/sidedwards/ai-video-summarizer)
5. [liang121/video-summarizer](https://github.com/liang121/video-summarizer)
6. [nabid-pf/youtube-video-summarizer-mcp](https://github.com/nabid-pf/youtube-video-summarizer-mcp)
7. [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
8. [AIAfterDark/youtube-summarizer-app](https://github.com/AIAfterDark/youtube-summarizer-app)
9. [siddharthsky/AI-Video-Summarizer](https://github.com/siddharthsky/AI-Video-Summarizer)
10. [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)

## 참고 자료

- [W1] https://help.repurpose.io/en/articles/10613821-workflow-overview
- [W2] https://www.opusclip.io/features
- [W3] https://www.descript.com/features/ai-clip-generator
- [W4] https://www.repurpose.io/small-business
- [W5] https://www.buffer.com/resources/ai-assistant
- [W6] https://www.buffer.com/resources/best-time-to-post-on-social-media/
- [S1] https://github.com/DevRico003/youtube_summarizer
- [S2] https://github.com/akashe/YoutubeSummarizer
- [S3] https://github.com/sidedwards/ai-video-summarizer
- [S4] https://github.com/liang121/video-summarizer
- [S5] https://github.com/nabid-pf/youtube-video-summarizer-mcp
- [S6] https://github.com/jdepoix/youtube-transcript-api
- [S7] https://github.com/gitroomhq/postiz-app
- [S8] https://github.com/AIAfterDark/youtube-summarizer-app
- [S9] https://github.com/siddharthsky/AI-Video-Summarizer
- [S10] https://github.com/harry0703/MoneyPrinterTurbo

---

## Round 2 델타 (추가 반복 실행)

추가 실행량:
- 누적 쿼리: 33개+
- 추가 라운드 후보(candidates_round2): 38개
- 추가 README 직접 수집: 15개
- 스니펫 통합 분석 대상: 25개 레포

빈도 상위 클러스터(README 신호 기준):
- API/Headless 연동
- 전체 트랜스크립트 가시화
- 멀티 LLM 프로바이더
- 자막/Whisper 폴백
- 다국어 출력
- Export 패키지
- 타임스탬프/챕터 내비게이션

### Round 2 추가 우선 후보 (기존 30개 대비 델타)

31. **Summary/Transcript 듀얼 모드 토글 고도화** - 난이도: 하  
    이유: 사용자 의도(요약 vs 원문 탐색) 전환을 빠르게 지원.  
    참고: [S1], [S8], [S11]

32. **톤 프리셋(전문/친근/압축/학습용) + 길이 프리셋 결합** - 난이도: 하  
    이유: 스타일 선택의 실사용 생산성 향상.  
    참고: [S11], [S1]

33. **브라우저 확장(YouTube 페이지 내 요약 버튼) 연동 채널** - 난이도: 중  
    이유: 유입 경로 확대 및 즉시 사용성 강화.  
    참고: [S12], [S13]

34. **요약 결과의 Compact/Full/Timeline 3단 뷰 표준화** - 난이도: 중  
    이유: 길이/맥락/탐색성을 동시에 제공 가능.  
    참고: [S1]

35. **출력 포맷 확장(DOCX 외 MD/TXT/ZIP 묶음)** - 난이도: 중  
    이유: 후속 편집 파이프라인의 범용성 증가.  
    참고: [S4], [S11], [S3]

36. **에이전트 친화 CLI/Headless 워크플로우 엔드포인트** - 난이도: 중  
    이유: 외부 자동화(에이전트/n8n) 연동성 강화.  
    참고: [S14], [S7], [S15]

37. **게시 후 분석 연결 보정(미매핑 콘텐츠 수동 연결 UI)** - 난이도: 중  
    이유: 자동발행 후 분석 누락 케이스를 운영적으로 복구 가능.  
    참고: [S14]

38. **요약 API의 품질 파라미터 표준화(percent/algorithm/detail)** - 난이도: 하  
    이유: UI/자동화 양쪽에서 예측 가능한 제어 제공.  
    참고: [S16], [S8]

39. **플러그인형 LLM 제공자 설정 UX(키 검증 + fallback 우선순위)** - 난이도: 중  
    이유: 다중 프로바이더 환경의 장애 복원력 향상.  
    참고: [S1], [S11], [S15]

40. **자막 소스 품질 메타(수동/자동/번역본) 노출 후 사용자가 선택** - 난이도: 중  
    이유: 요약 정확도 편차를 사용자에게 통제권으로 전환.  
    참고: [S6], [S5], [S4]

## Round 2 추가 참고 레포

- [S11] https://github.com/uncogeek/youtube-summarizer
- [S12] https://github.com/avarayr/youtube-summarizer-oss
- [S13] https://github.com/shobhit10058/Youtube_transcript_summarizer
- [S14] https://github.com/gitroomhq/postiz-agent
- [S15] https://github.com/n8n-io/n8n
- [S16] https://github.com/AnujK2901/yt-sum-flask

---

## Round 3 델타 (요청한 추가 10회 + 보정 10회)

실행 요약:
- 추가 10회 쿼리(`q37~q46`)는 GitHub 결과가 대부분 0건
- 동일 목적 보정 10회(`q47~q56`) 재실행으로 유효 후보 확보
- 누적 쿼리: 56개
- 누적 raw 레포: 722개
- 누적 중복 제거: 676개
- 최근성(2024-03-02 이후): 594개
- round4 후보: 43개

Round 3에서 강해진 신호:
- **Transcript Editor 계열**(교정/정렬/타임코드 복원/고성능 편집)
- **Headless/API 우선 워크플로우**
- **요약 후 편집 단계 분리**(생성 품질보다 후편집 생산성에 초점)

### Round 3 추가 우선 후보 (기존 40개 대비 델타)

41. **타임드 트랜스크립트 교정 에디터(단축키/문장 병합/분할)** - 난이도: 상  
    이유: 자동 자막 품질 편차를 운영 단계에서 빠르게 보정 가능.  
    참고: [S17], [S18], [S19]

42. **타임코드 재정렬(align) 엔진 내장 + 서버사이드 오프로드 옵션** - 난이도: 상  
    이유: 편집 후 자막/스크립트 타임코드 무결성 유지에 중요.  
    참고: [S18]

43. **교정 워크플로우 분리(초안 생성자 vs 교정자 역할 모델)** - 난이도: 중  
    이유: 팀 운영 시 생성/검수 병렬화로 처리량 증가.  
    참고: [S17], [S20]

44. **장문 미디어(1시간+) 편집 성능 최적화 모드** - 난이도: 중  
    이유: 실무 입력 길이 증가 시 UX 붕괴를 방지.  
    참고: [S18]

45. **에디터 기반 다중 Export 프로파일(docx/txt/timed json)** - 난이도: 중  
    이유: 게시 채널/편집툴별 포맷 요구 대응력 증가.  
    참고: [S18], [S17]

46. **교정 로그/변경이력 추적(누가 무엇을 수정했는지)** - 난이도: 중  
    이유: 품질 책임 추적과 팀 협업 감사성 강화.  
    참고: [S17], [S20]

## Round 3 추가 참고 레포

- [S17] https://github.com/bbc/react-transcript-editor
- [S18] https://github.com/pietrop/slate-transcript-editor
- [S19] https://github.com/alexnorton/transcript-editor
- [S20] https://github.com/pietrop/fact2_transcription_editor
- [S21] https://github.com/Ravi-Teja-konda/Surveillance_Video_Summarizer
