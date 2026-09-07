"""
콘텐츠 재활용 추천 서비스 (F10-20)
기존 콘텐츠를 다양한 포맷/플랫폼으로 변환 제안
"""
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)


REPURPOSE_PROMPTS = {
    'twitter_thread': (
        "다음 콘텐츠를 Twitter/X 스레드로 변환하세요. "
        "각 트윗은 280자 이내, 5-10개 트윗으로 구성, 번호 매기기. "
        "핵심 인사이트 중심으로 작성하세요."
    ),
    'linkedin_post': (
        "다음 콘텐츠를 LinkedIn 전문가 포스트로 변환하세요. "
        "전문성을 드러내되 친근한 톤, 3-5개 핵심 포인트, 해시태그 3개 포함."
    ),
    'youtube_shorts_script': (
        "다음 콘텐츠를 60초 YouTube Shorts 대본으로 변환하세요. "
        "훅(0-5초), 핵심 내용(5-50초), CTA(50-60초) 구조로 작성."
    ),
    'email_newsletter': (
        "다음 콘텐츠를 이메일 뉴스레터 형식으로 변환하세요. "
        "제목, 인트로(2문장), 핵심 섹션 3개, 마무리 CTA로 구성."
    ),
    'podcast_outline': (
        "다음 콘텐츠를 팟캐스트 에피소드 아웃라인으로 변환하세요. "
        "에피소드 제목, 5-7개 토픽 포인트, 예상 논의 시간 포함."
    ),
    'infographic_points': (
        "다음 콘텐츠에서 인포그래픽용 핵심 포인트 7-10개를 추출하세요. "
        "각 포인트는 짧고 임팩트 있게, 가능한 수치나 데이터 포함."
    ),
    'quiz': (
        "다음 콘텐츠를 기반으로 퀴즈 5문제를 만드세요. "
        "각 문제: 질문, 4개 선택지 (a~d), 정답, 간단한 해설."
    ),
}


def _build_system_prompt(target_format: str, language: str) -> str:
    """대상 포맷과 언어에 맞는 시스템 프롬프트를 조합합니다."""
    if target_format not in REPURPOSE_PROMPTS:
        raise ValueError(
            f"지원하지 않는 포맷: {target_format}. "
            f"지원 목록: {list(REPURPOSE_PROMPTS.keys())}"
        )
    base_prompt = REPURPOSE_PROMPTS[target_format]
    lang_suffix = {
        'en': " Write in English.",
        'ja': " 日本語で作成してください。",
    }.get(language, "")
    return base_prompt + lang_suffix + " 금지 표현(놀라운, 혁신적 등)은 사용하지 마세요."


class RepurposeService:
    """
    콘텐츠 재활용 변환 서비스

    기존 콘텐츠를 다양한 포맷으로 자동 변환:
    - Twitter 스레드
    - LinkedIn 포스트
    - YouTube Shorts 대본
    - 이메일 뉴스레터
    - 팟캐스트 아웃라인
    - 인포그래픽 포인트
    - 퀴즈
    """

    DEFAULT_MODEL = os.getenv(
        'REPURPOSE_MODEL',
        'cliproxyapi/gpt-5.5'
    )

    def repurpose(
        self,
        content: str,
        target_format: str,
        language: str = 'ko',
        model: Optional[str] = None,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """
        콘텐츠를 특정 포맷으로 변환

        Args:
            content: 원본 콘텐츠 (마크다운)
            target_format: 변환 대상 포맷 (REPURPOSE_PROMPTS 키)
            language: 출력 언어
            model: AI 모델 (없으면 기본값)

        Returns:
            {'format': str, 'content': str, 'character_count': int}
        """
        system_prompt = _build_system_prompt(target_format, language)

        try:
            from services.core.ai_service import call_litellm, resolve_public_model
            target_model = resolve_public_model(model, self.DEFAULT_MODEL)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"[원본 콘텐츠]\n{content[:5000]}"},
            ]
            response = call_litellm(
                messages,
                model=target_model,
                max_tokens=3000,
                temperature=0.7,
                on_cost_start=on_cost_start,
            )
            result_content = response.choices[0].message.content.strip()

            return {
                'format': target_format,
                'content': result_content,
                'character_count': len(result_content),
                'language': language,
            }

        except UsageLockUnavailable:
            raise
        except Exception as exc:
            logger.error(
                "재활용 변환 실패: format=%s, type=%s",
                target_format,
                type(exc).__name__,
            )
            raise RuntimeError("콘텐츠 재활용 변환에 실패했습니다.") from exc

    def repurpose_all(
        self,
        content: str,
        formats: Optional[List[str]] = None,
        language: str = 'ko',
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """
        다중 포맷 동시 변환

        Args:
            content: 원본 콘텐츠
            formats: 변환할 포맷 목록 (None이면 인기 5개 포맷)
            language: 출력 언어

        Returns:
            포맷별 변환 결과 dict
        """
        if not formats:
            formats = ['twitter_thread', 'linkedin_post', 'email_newsletter',
                       'youtube_shorts_script', 'infographic_points']

        results = {}
        errors = {}

        for fmt in formats:
            try:
                repurpose_kwargs = {}
                if callable(on_cost_start):
                    repurpose_kwargs['on_cost_start'] = on_cost_start
                results[fmt] = self.repurpose(
                    content,
                    fmt,
                    language,
                    **repurpose_kwargs,
                )
                logger.info("재활용 변환 완료: %s", fmt)
            except UsageLockUnavailable:
                raise
            except Exception as exc:
                errors[fmt] = "변환 실패"
                logger.warning(
                    "재활용 변환 실패: %s (type=%s)",
                    fmt,
                    type(exc).__name__,
                )

        return {
            'results': results,
            'errors': errors,
            'success_count': len(results),
            'total_formats': len(formats),
        }

    @staticmethod
    def get_available_formats() -> List[Dict[str, str]]:
        """지원 포맷 목록 반환"""
        labels = {
            'twitter_thread': 'Twitter 스레드',
            'linkedin_post': 'LinkedIn 포스트',
            'youtube_shorts_script': 'YouTube Shorts 대본',
            'email_newsletter': '이메일 뉴스레터',
            'podcast_outline': '팟캐스트 아웃라인',
            'infographic_points': '인포그래픽 포인트',
            'quiz': '퀴즈',
        }
        return [{'format': k, 'label': v} for k, v in labels.items()]
