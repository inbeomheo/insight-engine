"""Supadata API 자막 폴백 (4단계 폴백 중 마지막 단계 — 유료 API)."""
from __future__ import annotations

from typing import Optional

import requests

from services.transcript._shared import (
    HTTP_TIMEOUT,
    SUPADATA_API_URL,
    TranscriptResult,
    log_warning,
)


def get_transcript_via_supadata(video_id: str, api_key: str) -> Optional[TranscriptResult]:
    """Supadata API를 통해 YouTube 자막을 가져옵니다."""
    if not api_key:
        return None

    try:
        response = requests.get(
            SUPADATA_API_URL,
            params={"videoId": video_id, "text": "true"},
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
