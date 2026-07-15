"""
실시간 번역 서비스 (F10-23)
LiteLLM 기반 AI 번역 + DeepL API 폴백
언어: ko ↔ en ↔ ja (3언어 쌍 지원)
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DEEPL_API_KEY = os.getenv('DEEPL_API_KEY', '')

# DeepL 언어 코드 매핑
_DEEPL_LANG_MAP = {
    'ko': 'KO',
    'en': 'EN-US',
    'ja': 'JA',
    'zh': 'ZH',
    'fr': 'FR',
    'de': 'DE',
    'es': 'ES',
}

# AI 번역 프롬프트 (언어별)
_TRANSLATE_PROMPTS = {
    'ko': "다음 텍스트를 자연스러운 한국어로 번역하세요. 원문의 의미와 뉘앙스를 최대한 살려주세요. 번역문만 출력하세요.",
    'en': "Translate the following text to natural English. Preserve the original meaning and nuance. Output only the translation.",
    'ja': "以下のテキストを自然な日本語に翻訳してください。原文の意味とニュアンスを最大限に살려주세요。翻訳文のみを出力してください。",
}


def _translate_with_deepl(text: str, target_lang: str) -> Optional[str]:
    """DeepL API로 번역"""
    if not DEEPL_API_KEY:
        return None

    try:
        import httpx

        deepl_lang = _DEEPL_LANG_MAP.get(target_lang)
        if not deepl_lang:
            return None

        base_url = (
            "https://api-free.deepl.com/v2/translate"
            if DEEPL_API_KEY.endswith(':fx')
            else "https://api.deepl.com/v2/translate"
        )

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                base_url,
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                data={
                    "text": text,
                    "target_lang": deepl_lang,
                }
            )
        resp.raise_for_status()
        return resp.json()['translations'][0]['text']
    except Exception as e:
        logger.warning("DeepL 번역 실패: %s", e)
        return None


def _translate_with_ai(text: str, target_lang: str, model: Optional[str] = None) -> str:
    """LiteLLM AI 번역"""
    from services.core.ai_service import call_litellm

    prompt = _TRANSLATE_PROMPTS.get(target_lang, _TRANSLATE_PROMPTS['en'])
    target_model = model or os.getenv('TRANSLATION_MODEL', 'chatmock/gpt-5.3-codex-spark')

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    result = call_litellm(messages, model=target_model, max_tokens=4000, temperature=0.3)
    return result.choices[0].message.content.strip()


class RealtimeTranslateService:
    """
    실시간 번역 서비스

    번역 우선순위:
    1. DeepL API (DEEPL_API_KEY 설정 시, 품질 최고)
    2. LiteLLM AI 번역 (폴백)
    """

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        use_ai_only: bool = False,
        model: Optional[str] = None,
    ) -> dict:
        """
        텍스트 번역

        Args:
            text: 번역할 텍스트
            target_lang: 목표 언어 코드 (ko/en/ja)
            source_lang: 원본 언어 코드 (None이면 자동 감지)
            use_ai_only: True면 AI 번역만 사용
            model: AI 번역 모델 (없으면 기본값)

        Returns:
            {'translated': str, 'source': 'deepl'|'ai', 'target_lang': str}
        """
        if not text or not text.strip():
            return {'translated': '', 'source': 'none', 'target_lang': target_lang}

        if target_lang not in _DEEPL_LANG_MAP and target_lang not in _TRANSLATE_PROMPTS:
            raise ValueError(f"지원하지 않는 언어: {target_lang} (지원: {list(_TRANSLATE_PROMPTS.keys())})")

        # DeepL 우선 시도
        if not use_ai_only:
            deepl_result = _translate_with_deepl(text, target_lang)
            if deepl_result:
                return {
                    'translated': deepl_result,
                    'source': 'deepl',
                    'target_lang': target_lang,
                }

        # AI 번역
        try:
            ai_result = _translate_with_ai(text, target_lang, model=model)
            return {
                'translated': ai_result,
                'source': 'ai',
                'target_lang': target_lang,
            }
        except Exception as e:
            logger.error("AI 번역 실패: %s", e)
            raise RuntimeError(f"번역 실패: {e}") from e

    def translate_content(
        self,
        content: str,
        target_lang: str,
        chunk_size: int = 2000,
    ) -> str:
        """
        장문 콘텐츠 번역 (단락 단위 청크 처리)

        Args:
            content: 번역할 전체 콘텐츠
            target_lang: 목표 언어
            chunk_size: 청크 크기 (문자 수)

        Returns:
            번역된 전체 콘텐츠
        """
        paragraphs = content.split('\n\n')
        translated_paragraphs = []
        current_chunk = []
        current_len = 0

        def flush_chunk() -> None:
            if not current_chunk:
                return
            chunk_text = '\n\n'.join(current_chunk)
            result = self.translate(chunk_text, target_lang)
            translated_paragraphs.append(result['translated'])

        for para in paragraphs:
            if current_len + len(para) > chunk_size and current_chunk:
                flush_chunk()
                current_chunk = []
                current_len = 0
            current_chunk.append(para)
            current_len += len(para)

        if current_chunk:
            flush_chunk()

        return '\n\n'.join(translated_paragraphs)
