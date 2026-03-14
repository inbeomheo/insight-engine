"""
썸네일/배너 자동 생성 서비스
제목+키워드 → 이미지 프롬프트 생성 → AI 이미지 생성
"""
import base64
import logging
from typing import Dict, List

from services.media.image_gen_service import generate_image, IMAGE_GEN_API_KEY

logger = logging.getLogger(__name__)


def _build_image_prompt(title: str, keywords: List[str]) -> str:
    """제목과 키워드로 이미지 생성 프롬프트를 만듭니다.

    영어 프롬프트로 변환하여 DALL-E 품질 극대화.
    """
    kw_text = ', '.join(keywords[:5]) if keywords else ''
    prompt = (
        f'Create a modern, professional YouTube thumbnail or blog banner image. '
        f'Topic: "{title}". '
    )
    if kw_text:
        prompt += f'Keywords: {kw_text}. '
    prompt += (
        'Style: clean, vibrant colors, minimal text, eye-catching design. '
        'No watermarks or logos. High quality digital illustration.'
    )
    return prompt


def generate_thumbnail(title: str, keywords: List[str] = None,
                       size: str = '1792x1024') -> Dict:
    """제목+키워드로 썸네일 이미지를 생성합니다.

    Args:
        title: 콘텐츠 제목
        keywords: 키워드 리스트 (선택)
        size: 이미지 크기 (기본 1792x1024 = 16:9 배너)

    Returns:
        {
            'success': True,
            'image_base64': str,  # base64 인코딩된 PNG
            'prompt': str,        # 사용된 프롬프트
            'size': str,
        }
    """
    if not title or not title.strip():
        return {'success': False, 'error': '제목이 필요합니다.'}

    if not IMAGE_GEN_API_KEY:
        return {'success': False, 'error': '이미지 생성 API 키가 설정되지 않았습니다.'}

    keywords = keywords or []
    prompt = _build_image_prompt(title, keywords)

    try:
        image_bytes = generate_image(prompt, size)
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            'success': True,
            'image_base64': image_b64,
            'prompt': prompt,
            'size': size,
        }
    except (ValueError, RuntimeError) as e:
        logger.error('썸네일 생성 실패: %s', e)
        return {'success': False, 'error': str(e)}
