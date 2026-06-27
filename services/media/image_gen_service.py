"""
AI 이미지 생성 서비스
DALL-E (OpenAI) API를 통한 이미지 생성
"""
import base64
import logging
import os

import requests

logger = logging.getLogger(__name__)

# 환경변수에서 설정 로드
IMAGE_GEN_PROVIDER = os.getenv('IMAGE_GEN_PROVIDER', 'openai')
IMAGE_GEN_API_KEY = os.getenv('IMAGE_GEN_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')


def generate_image(prompt: str, size: str = '1024x1024') -> bytes:
    """AI 이미지를 생성합니다.

    Args:
        prompt: 이미지 생성 프롬프트 (영어 권장)
        size: 이미지 크기 ('1024x1024', '1792x1024', '1024x1792')

    Returns:
        PNG 이미지 바이트

    Raises:
        ValueError: API 키 미설정 또는 잘못된 파라미터
        RuntimeError: API 호출 실패
    """
    if not IMAGE_GEN_API_KEY:
        raise ValueError('이미지 생성 API 키가 설정되지 않았습니다. IMAGE_GEN_API_KEY 환경변수를 확인하세요.')

    valid_sizes = {'1024x1024', '1792x1024', '1024x1792'}
    if size not in valid_sizes:
        raise ValueError(f'지원하지 않는 이미지 크기: {size}. 사용 가능: {valid_sizes}')

    if IMAGE_GEN_PROVIDER == 'openai':
        return _generate_openai(prompt, size)

    raise ValueError(f'지원하지 않는 이미지 생성 프로바이더: {IMAGE_GEN_PROVIDER}')


def _generate_openai(prompt: str, size: str) -> bytes:
    """OpenAI DALL-E API로 이미지를 생성합니다."""
    try:
        resp = requests.post(
            'https://api.openai.com/v1/images/generations',
            headers={
                'Authorization': f'Bearer {IMAGE_GEN_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'dall-e-3',
                'prompt': prompt,
                'n': 1,
                'size': size,
                'response_format': 'b64_json',
            },
            timeout=60,
            allow_redirects=False,
        )
        status_code = getattr(resp, 'status_code', 0)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            raise RuntimeError(f'이미지 생성 API 리다이렉트 차단: {resp.status_code}')
        resp.raise_for_status()
        data = resp.json()
        b64_str = data['data'][0]['b64_json']
        return base64.b64decode(b64_str)

    except requests.exceptions.HTTPError as e:
        logger.error('OpenAI 이미지 생성 API 오류: %s', e)
        raise RuntimeError(f'이미지 생성 실패: {e.response.status_code} {e.response.text[:200]}') from e
    except Exception as e:
        logger.error('이미지 생성 중 오류: %s', e)
        raise RuntimeError(f'이미지 생성 중 오류: {e}') from e
