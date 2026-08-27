"""Supadata API 자막 폴백 (4단계 폴백 중 마지막 단계 — 유료 API)."""
from __future__ import annotations

from typing import Callable, Optional

import requests

from services.transcript._shared import (
    HTTP_TIMEOUT,
    SUPADATA_API_URL,
    TranscriptResult,
    log_warning,
)


def get_transcript_via_supadata(
    video_id: str,
    api_key: str,
    preferred_language: Optional[str] = None,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Optional[TranscriptResult]:
    """Supadata API를 통해 YouTube 자막을 가져옵니다.

    Args:
        video_id: YouTube 비디오 ID
        api_key: Supadata API 키
        preferred_language: 요청 언어 코드(예: 'ko'). Supadata API의 `lang` 파라미터로 전달.
            해당 언어 자막이 없으면 Supadata가 자체적으로 기본 자막을 반환한다(요청 실패로 이어지지 않음).
        on_cost_start: Supadata 외부 할당량 요청 직전에 실행할 선택 콜백.
    """
    if not api_key:
        return None

    try:
        params = {"videoId": video_id, "text": "true"}
        if preferred_language:
            params["lang"] = preferred_language
        # API key 확인과 요청 조립은 무비용이다. 실제 Supadata
        # 할당량을 소모할 수 있는 HTTP 요청 직전에만 확정한다.
        # 콜백 예외은 requests 예외이 아니므로 아래 폴백 처리가
        # 삼키지 않고 호출자까지 전파된다(fail closed).
        if on_cost_start is not None:
            on_cost_start()
        response = requests.get(
            SUPADATA_API_URL,
            params=params,
            headers={"x-api-key": api_key},
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            if content:
                return content

            transcript = data.get("transcript", [])
            if transcript:
                texts = [item.get("text", "") for item in transcript if item.get("text")]
                return " ".join(texts)
            log_warning(f"Supadata returned empty content for video_id={video_id}")
            return None

        if response.status_code == 401:
            return {'error': 'Supadata API 키가 유효하지 않습니다.'}
        if response.status_code == 402:
            return {'error': 'Supadata API 사용량이 초과되었습니다. 플랜을 업그레이드하세요.'}

        log_warning(f"Supadata API returned status {response.status_code} for video_id={video_id}")
        return None

    except requests.exceptions.Timeout:
        log_warning(f"Supadata API timeout for video_id={video_id}")
        return None
    except requests.exceptions.RequestException as e:
        log_warning(f"Supadata API request failed for video_id={video_id}: {str(e)}")
        return None
