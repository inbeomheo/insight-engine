# Transcript BC

## 책임
YouTube 영상에서 자막을 추출하는 단일 권위 BC. 4단계 폴백 전략으로 안정성 확보.

## 유비쿼터스 언어
- **Transcript**: 한 영상의 자막 전체 (Aggregate Root)
- **TranscriptSegment**: 자막 한 줄 (시작 시간 + 길이 + 텍스트)
- **SourceType**: 추출 출처 — YOUTUBE_API / WATCH_PAGE / SUPADATA / WHISPER
- **SourceMeta**: 출처 + 품질 점수 + 자동/수동 자막 여부

## 4단계 폴백 전략
1. **YOUTUBE_API**: youtube-transcript-api 라이브러리 (가장 빠름, 무료)
2. **WATCH_PAGE**: YouTube watch 페이지 파싱 (API 차단 시)
3. **SUPADATA**: Supadata API (유료, 최후 폴백 전)
4. **WHISPER**: faster-whisper 로컬 음성인식 (오디오 다운로드 후 STT)

## Aggregate
**Transcript** (루트) — TranscriptSegment[], SourceMeta.

## 외부 ACL
- `ITranscriptProvider` — 4단계 폴백의 각 단계 (어댑터별 구현)
- `ITranscriptRepository` — Transcript 영속화 (캐시/DB)
- `ITranscriptCache` — 짧은 수명 인메모리 캐시

## 유스케이스
- **ExtractTranscriptUseCase**: 4단계 폴백 조정 — 우선순위 순으로 시도, 캐시 적용

## 의존 방향
- 다른 BC → Transcript: `ITranscriptProvider`, `ExtractTranscriptUseCase`
- Transcript → 다른 BC: 없음 (단방향)

## 현재 진척 (Phase 3)
- 도메인 모델 + 포트 + UseCase 골격 완료 (이 파일들)
- 어댑터 4종 구현: 다음 작업 (Y)
- 단위 테스트: 다음 작업 (Z)
- ContentGeneration 흐름 마이그레이션: 다음 PR
