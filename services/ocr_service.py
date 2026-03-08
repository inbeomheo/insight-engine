"""
이미지 OCR 서비스

Gemini Vision API를 사용하여 이미지에서 텍스트를 추출합니다.
LiteLLM을 통해 호출하며, 추출된 텍스트를 콘텐츠 생성에 활용합니다.
"""
import base64
import logging
import os
from typing import Any, Dict

from litellm import completion

logger = logging.getLogger(__name__)

# 지원하는 이미지 MIME 타입
_SUPPORTED_MIMES = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
}

_OCR_PROMPT = "이미지에 포함된 모든 텍스트를 정확하게 추출해주세요. 레이아웃과 구조를 최대한 유지하세요."


def extract_text_from_image(image_path: str) -> Dict:
    """로컬 이미지 파일에서 텍스트를 추출합니다.

    Gemini Vision API를 LiteLLM을 통해 호출합니다.

    Args:
        image_path: 이미지 파일 경로

    Returns:
        {"title": "OCR 추출", "content": str, "source_type": "ocr"}

    Raises:
        ValueError: 지원하지 않는 파일 형식이거나 추출 실패
        FileNotFoundError: 파일이 존재하지 않는 경우
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    ext = os.path.splitext(image_path)[1].lstrip('.').lower()
    mime_type = _SUPPORTED_MIMES.get(ext)
    if not mime_type:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: .{ext} (지원: {', '.join(_SUPPORTED_MIMES.keys())})")

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    return _call_vision_api(image_data, mime_type)


def extract_from_upload(file_storage: Any) -> Dict:
    """업로드된 이미지(FileStorage)에서 텍스트를 추출합니다.

    Args:
        file_storage: Flask FileStorage 객체

    Returns:
        {"title": "OCR 추출", "content": str, "source_type": "ocr"}

    Raises:
        ValueError: 지원하지 않는 파일 형식이거나 추출 실패
    """
    filename = file_storage.filename or ''
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    mime_type = _SUPPORTED_MIMES.get(ext)
    if not mime_type:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: .{ext} (지원: {', '.join(_SUPPORTED_MIMES.keys())})")

    image_data = base64.b64encode(file_storage.read()).decode('utf-8')
    return _call_vision_api(image_data, mime_type)


def _call_vision_api(image_base64: str, mime_type: str) -> Dict:
    """Gemini Vision API를 호출하여 OCR을 수행합니다.

    Args:
        image_base64: base64 인코딩된 이미지 데이터
        mime_type: 이미지 MIME 타입

    Returns:
        {"title": "OCR 추출", "content": str, "source_type": "ocr"}

    Raises:
        ValueError: 텍스트 추출 실패
    """
    model = os.getenv('OCR_MODEL', 'gemini/gemini-2.5-flash-lite-preview-09-2025')
    messages = _build_vision_messages(image_base64, mime_type)

    try:
        response = completion(model=model, messages=messages, max_tokens=4000, timeout=60)
        content = response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Vision API OCR 실패: %s", e)
        raise ValueError(f"이미지 텍스트 추출에 실패했습니다: {e}")

    if not content.strip():
        raise ValueError("이미지에서 텍스트를 찾을 수 없습니다.")

    return {"title": "OCR 추출", "content": content.strip(), "source_type": "ocr"}


def _build_vision_messages(image_base64: str, mime_type: str) -> list:
    """Vision API 요청용 메시지를 구성합니다."""
    return [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
            {"type": "text", "text": _OCR_PROMPT},
        ],
    }]
