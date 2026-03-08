"""
자동 자막 생성+번역 서비스 (F10-07)
영상 URL에서 자막 추출 후 다국어 번역
Whisper 로컬 + YouTube 자막 + 번역 파이프라인
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# 간단 구조체 대신 dict 사용


def _format_vtt(entries: List[Dict]) -> str:
    """WebVTT 포맷으로 변환"""
    lines = ["WEBVTT", ""]
    for i, entry in enumerate(entries, 1):
        start = _seconds_to_vtt_time(entry.get('start', 0))
        end = _seconds_to_vtt_time(entry.get('end', entry.get('start', 0) + 3))
        text = entry.get('text', '').strip()
        lines += [f"{i}", f"{start} --> {end}", text, ""]
    return "\n".join(lines)


def _format_srt(entries: List[Dict]) -> str:
    """SRT 포맷으로 변환"""
    lines = []
    for i, entry in enumerate(entries, 1):
        start = _seconds_to_srt_time(entry.get('start', 0))
        end = _seconds_to_srt_time(entry.get('end', entry.get('start', 0) + 3))
        text = entry.get('text', '').strip()
        lines += [f"{i}", f"{start} --> {end}", text, ""]
    return "\n".join(lines)


def _seconds_to_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class AutoSubtitleService:
    """
    자동 자막 생성 + 번역 서비스

    파이프라인:
    1. YouTube 자막 추출 (API/파싱)
    2. Whisper 폴백 (자막 없는 경우)
    3. 다국어 번역 (DeepL/AI)
    4. VTT/SRT 포맷 내보내기
    """

    def extract_and_translate(
        self,
        video_url: str,
        target_languages: List[str] = None,
        output_format: str = 'vtt',
    ) -> Dict[str, Any]:
        """
        영상에서 자막 추출 후 번역

        Args:
            video_url: YouTube URL
            target_languages: 번역 언어 목록 ['ko', 'en', 'ja']
            output_format: 출력 포맷 ('vtt', 'srt', 'text')

        Returns:
            {
                'original': str,              # 원본 자막
                'original_lang': str,         # 원본 언어
                'translations': {
                    'ko': str,               # 한국어 번역 자막
                    'en': str,               # 영어 번역 자막
                },
                'source': str,               # 자막 소스
            }
        """
        target_languages = target_languages or ['ko', 'en']

        # 자막 추출
        from services.content_service import ContentService
        content_svc = ContentService()

        transcript_result = content_svc.get_transcript(video_url)
        raw_transcript = transcript_result.get('transcript', '')
        source_type = transcript_result.get('source_type', 'unknown')

        if not raw_transcript:
            raise ValueError("자막을 추출할 수 없습니다")

        # 자막 세그먼트 파싱 (타임스탬프 기반)
        segments = self._parse_to_segments(raw_transcript)

        result = {
            'original': self._format_output(segments, output_format),
            'original_lang': transcript_result.get('language', 'auto'),
            'source': source_type,
            'translations': {},
            'segment_count': len(segments),
        }

        # 번역
        from services.realtime_translate_service import RealtimeTranslateService
        translator = RealtimeTranslateService()

        for lang in target_languages:
            if lang == result['original_lang']:
                continue
            try:
                translated_text = translator.translate_content(raw_transcript, lang)
                translated_segments = self._parse_to_segments(translated_text, copy_timing=segments)
                result['translations'][lang] = self._format_output(translated_segments, output_format)
            except Exception as e:
                logger.warning("언어 %s 번역 실패: %s", lang, e)
                result['translations'][lang] = None

        return result

    def _parse_to_segments(
        self,
        transcript: str,
        copy_timing: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        자막 텍스트를 시간 세그먼트로 파싱
        [MM:SS] 형식 타임스탬프가 있으면 활용, 없으면 균등 분할
        """
        # [MM:SS] 타임스탬프 파싱
        pattern = re.compile(r'\[(\d{1,2}):(\d{2})\]\s*(.+?)(?=\[\d|$)', re.DOTALL)
        matches = pattern.findall(transcript)

        if matches:
            segments = []
            for i, (mm, ss, text) in enumerate(matches):
                start = int(mm) * 60 + int(ss)
                end = start + 5  # 기본 5초
                if i + 1 < len(matches):
                    next_mm, next_ss, _ = matches[i + 1]
                    end = int(next_mm) * 60 + int(next_ss)
                segments.append({'start': start, 'end': end, 'text': text.strip()})
            return segments

        # 타임스탬프 없음 → 문장 단위 균등 분할
        sentences = [s.strip() for s in re.split(r'[.!?。]\s+', transcript) if s.strip()]
        segments = []
        duration_per_sentence = 4.0

        for i, sentence in enumerate(sentences):
            start = i * duration_per_sentence
            end = start + duration_per_sentence
            if copy_timing and i < len(copy_timing):
                start = copy_timing[i].get('start', start)
                end = copy_timing[i].get('end', end)
            segments.append({'start': start, 'end': end, 'text': sentence})

        return segments

    def _format_output(self, segments: List[Dict], fmt: str) -> str:
        if fmt == 'vtt':
            return _format_vtt(segments)
        elif fmt == 'srt':
            return _format_srt(segments)
        else:
            return '\n'.join(s['text'] for s in segments)
