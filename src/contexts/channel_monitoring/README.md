# Channel Monitoring BC

## 책임
사용자가 등록한 YouTube 채널의 신규 업로드를 주기적으로 감지하고 등록/조회/삭제하는 도메인. `ie_channel_monitors` 테이블이 단일 권위 저장소.

## 유비쿼터스 언어
- **ChannelSubscription**: 한 사용자가 한 채널에 등록한 1 모니터 (Aggregate Root)
- **ChannelId**: YouTube 채널 식별자 (UCxxxxx)
- **Interval**: 폴링 간격 (분 단위, 최소 5분)
- **MonitorOwnerId**: 소유자 (Identity BC `AccountId`)

## Aggregate
**ChannelSubscription** — 1 등록 = 1 레코드. 활성/비활성, 폴링 간격, 자동 생성 스타일/모디파이어 보유.

## 외부 ACL
- `IChannelMonitorRepository` — 등록/조회/삭제 + 활성 상태 변경

## 유스케이스
- `RegisterChannelMonitorUseCase` — 신규 채널 등록
- `ListChannelMonitorsUseCase` — 사용자별 등록 목록 조회
- `DeleteChannelMonitorUseCase` — 등록 해제

## 의존 방향
- 다른 BC → Channel Monitoring: `IChannelMonitorRepository`, UseCase들
- Channel Monitoring → 다른 BC: Identity BC `AccountId` (VO 값만 참조)
- YouTube 채널 최신 영상 조회는 기존 `services/platform/channel_monitor_service.py`의 `get_latest_video()`를 그대로 사용 (별도 BC 도입 불필요)
