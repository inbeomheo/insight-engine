"""YouTube watch 페이지 HTML 파싱 기반 자막 폴백 (2단계 폴백)."""
from __future__ import annotations

import html as html_module
import json
import re
from typing import Any, Dict, List, Optional

from defusedxml import ElementTree

import requests

from services.transcript._shared import (
    CaptionTrack,
    HTTP_TIMEOUT,
    PREFERRED_LANGUAGES,
    TIMEOUT_CONNECT,
    TIMEOUT_READ_SHORT,
    TranscriptResult,
    USER_AGENT,
    log_warning,
)


def extract_yt_initial_player_response(html_text: str) -> Optional[Dict[str, Any]]:
    """HTML에서 ytInitialPlayerResponse를 추출합니다."""
    if not isinstance(html_text, str) or not html_text:
        return None

    patterns = [
        r"ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;",
        r"var\s+ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;",
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


def extract_caption_tracks(player_response: Optional[Dict[str, Any]]) -> List[CaptionTrack]:
    """플레이어 응답에서 자막 트랙을 추출합니다."""
    try:
        captions = (player_response or {}).get('captions', {})
        renderer = captions.get('playerCaptionsTracklistRenderer', {})
        tracks = renderer.get('captionTracks', [])
        return tracks if isinstance(tracks, list) else []
    except Exception:
        return []


def pick_caption_track(
    tracks: List[CaptionTrack],
    preferred: tuple[str, ...] = PREFERRED_LANGUAGES
) -> Optional[CaptionTrack]:
    """우선순위에 따라 자막 트랙을 선택합니다."""
    if not isinstance(tracks, list) or not tracks:
        return None

    pref_list = list(preferred or ())

    def score(track: CaptionTrack) -> tuple[int, int]:
        lang = (track or {}).get('languageCode', '')
        is_asr = (track or {}).get('kind') == 'asr'
        try:
            lang_idx = pref_list.index(lang)
        except ValueError:
            lang_idx = len(pref_list) + 10
        return (lang_idx, 1 if is_asr else 0)

    return min(tracks, key=score)


def parse_vtt(vtt_text: str) -> str:
    """VTT 형식의 자막을 파싱합니다."""
    if not isinstance(vtt_text, str) or not vtt_text.strip():
        return ""

    lines: List[str] = []
    for raw in vtt_text.splitlines():
        line = raw.strip('﻿').strip()
        if not line or line.upper().startswith('WEBVTT') or '-->' in line:
            continue
        if re.match(r'^\d+$', line):
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()
        if line:
            lines.append(line)

    return " ".join(lines)


def parse_timedtext_xml(xml_text: str) -> str:
    """TimedText XML을 파싱합니다."""
    if not isinstance(xml_text, str) or not xml_text.strip():
        return ""

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return ""

    texts: List[str] = []
    for node in root.findall('.//text'):
        if node.text:
            texts.append(html_module.unescape(node.text).replace('\n', ' ').strip())

    return " ".join(filter(None, texts))


def is_safe_caption_url(url: str) -> bool:
    """자막 URL이 YouTube 도메인인지 검증합니다 (SSRF 방지)."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        host = (parsed.hostname or '').lower()
        return host.endswith('.youtube.com') or host.endswith('.google.com') or host.endswith('.googlevideo.com')
    except Exception:
        return False


def download_caption_from_url(base_url: str) -> str:
    """자막 URL에서 자막을 다운로드합니다."""
    if not isinstance(base_url, str) or not base_url:
        return ""

    if not is_safe_caption_url(base_url):
        log_warning(f"안전하지 않은 자막 URL 차단: {base_url[:60]}")
        return ""

    url = base_url
    if 'fmt=' not in url:
        url += ('&' if '?' in url else '?') + 'fmt=vtt'

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=(TIMEOUT_CONNECT, TIMEOUT_READ_SHORT),
                                allow_redirects=False)
        response.raise_for_status()
        text = response.text or ""

        if text.lstrip().startswith('WEBVTT'):
            return parse_vtt(text)
        if '<transcript' in text or '<text' in text:
            return parse_timedtext_xml(text)

        return text.strip()

    except requests.exceptions.Timeout:
        log_warning(f"Caption download timeout: {url[:50]}...")
        return ""
    except requests.exceptions.HTTPError as e:
        log_warning(f"Caption download HTTP error: {e.response.status_code if e.response else 'unknown'}")
        return ""
    except requests.exceptions.RequestException as e:
        log_warning(f"Caption download failed: {str(e)[:100]}")
        return ""


def get_transcript_from_watch_page(video_id: str) -> TranscriptResult:
    """Watch 페이지에서 직접 자막을 가져옵니다."""
    if not video_id:
        return {'error': '유효하지 않은 YouTube video_id입니다.'}

    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        }
        watch_url = f"https://www.youtube.com/watch?v={video_id}"

        response = requests.get(watch_url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()

        player = extract_yt_initial_player_response(response.text)
        tracks = extract_caption_tracks(player)
        track = pick_caption_track(tracks)

        if not track:
            return {'error': 'watch 페이지에서 자막 트랙(captionTracks)을 찾지 못했습니다.'}

        text = download_caption_from_url(track.get('baseUrl', ''))
        if not text:
            return {'error': 'watch 페이지 자막 다운로드에 실패했습니다.'}

        return text

    except Exception as e:
        return {'error': f'watch 페이지 자막 폴백 실패: {str(e)}'}
