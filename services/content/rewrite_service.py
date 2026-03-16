"""플랫폼별 카피 변환 서비스"""
import logging
from services.core import ai_service
from config import PLATFORM_PRESETS


def get_platform_limits(platform: str) -> dict:
    """플랫폼의 글자 제한 정보를 반환합니다."""
    preset = PLATFORM_PRESETS.get(platform)
    if not preset:
        return {}
    return {
        'max_chars': preset['max_chars'],
        'tone': preset['tone'],
        'format': preset['format'],
    }


logger = logging.getLogger(__name__)

def rewrite_for_platform(content: str, platform: str, model: str) -> dict:
    """콘텐츠를 특정 플랫폼에 맞게 변환합니다.

    Returns:
        {'platform': str, 'text': str, 'char_count': int, 'max_chars': int}
    """
    try:
        preset = PLATFORM_PRESETS.get(platform)
        if not preset:
            return {'error': f'지원하지 않는 플랫폼: {platform}'}

        prompt = f"""다음 콘텐츠를 {platform} 플랫폼에 최적화하여 변환해주세요.

    ## 규칙
    - 최대 {preset['max_chars']}자
    - 톤: {preset['tone']}
    - 형식: {preset['format']}
    - 해시태그는 관련성 높은 것 3-5개만
    - 마크다운 없이 순수 텍스트로

    ## 원본 콘텐츠
    {content[:3000]}

    변환된 텍스트만 출력하세요 (다른 설명 없이):"""

        result = ai_service.create_content(prompt, model, style_prompt='', style_id='sns_post')
        text = result.get('content', '').strip()

        # max_chars 강제 적용
        if len(text) > preset['max_chars']:
            text = text[:preset['max_chars'] - 3] + '...'

        # 원본 대비 축약 비율 계산
        original_len = len(content)
        rewritten_len = len(text)
        compression_ratio = round(rewritten_len / original_len, 4) if original_len > 0 else 0.0

        return {
            'platform': platform,
            'text': text,
            'char_count': rewritten_len,
            'max_chars': preset['max_chars'],
            'compression_ratio': compression_ratio,
            'platform_limits': get_platform_limits(platform),
        }
    except Exception as e:
        logger.error(f"플랫폼 리라이트 처리 실패: {e}")
        return {'error': '리라이트 처리 중 오류가 발생했습니다.'}
