# Content/Library BC

## 책임
사용자가 생성한 콘텐츠(분석 히스토리)의 영속화. `ie_histories` 테이블이 단일 권위 저장소.

## 유비쿼터스 언어
- **HistoryEntry**: 한 번의 콘텐츠 생성 결과 (Aggregate Root) — URL/스타일/제목/본문/트랜스크립트/메타 보유
- **ReportId**: 클라이언트가 발급한 UUID 형태 식별자 (frontend `crypto.randomUUID()`)
- **OwnerId**: 소유 사용자 (Identity BC `AccountId`)

## Aggregate
**HistoryEntry** (루트) — 1 회 생성 결과의 모든 메타데이터를 한 단위로 묶음.

## 외부 ACL
- `IHistoryRepository` — HistoryEntry 영속화

## 유스케이스
- `SaveHistoryEntryUseCase` — 생성 직후 호출

## 의존 방향
- 다른 BC → Content/Library: `IHistoryRepository`, `SaveHistoryEntryUseCase`
- Content/Library → 다른 BC: Identity BC `AccountId` (VO 참조만)

## 마이그레이션 상태
- Phase 5-a: 골격 + 편의 함수 + `generation_helpers.py` 단일 마이그레이션 (현재)
- Phase 5-b: 나머지 라우트(`blog_routes.py`, `auth_routes.py`, `utility/external.py`) 마이그레이션 — 후속 PR
- Phase 5-c: 기존 `services/data/supabase_service.py`의 history 함수들 내부 위임 변경
