class TranscriptException(Exception):
    """Transcript BC 공통 베이스."""


class ExtractionFailed(TranscriptException):
    """모든 폴백 시도 실패."""

    def __init__(self, video_id, attempted_sources, last_error):
        self.video_id = video_id
        self.attempted_sources = attempted_sources
        self.last_error = last_error
        super().__init__(
            f"Transcript 추출 실패: {video_id} (시도: {attempted_sources}, 마지막: {last_error})"
        )


class UnsupportedVideo(TranscriptException):
    """비디오가 비공개/삭제/연령제한."""


class ProviderUnavailable(TranscriptException):
    """특정 Provider가 일시적으로 불가 (네트워크/SDK 미설치 등) — 폴백 진행."""
