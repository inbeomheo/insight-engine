"""플랫폼별 카피 변환 서비스"""
from services import ai_service
from config import PLATFORM_PRESETS


def rewrite_for_platform(content: str, platform: str, model: str) -> dict:
    """콘텐츠를 특정 플랫폼에 맞게 변환합니다.

    Returns:
        {'platform': str, 'text': str, 'char_count': int, 'max_chars': int}
    """
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

    return {
        'platform': platform,
        'text': text,
        'char_count': len(text),
        'max_chars': preset['max_chars'],
    }
