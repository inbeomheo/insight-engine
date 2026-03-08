"""
AI 에디터 Copilot 서비스 (F10-16)
텍스트 선택 영역에 대한 AI 보조 편집 (이미 inline_edit과 유사하지만 Copilot 전용 기능 추가)
- 자동완성 제안 (completion)
- 문단 재작성 (rewrite)
- 스타일 맞춤 편집 (style-aware edit)
- 오류 교정 (grammar/spelling)
"""
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


class CopilotService:
    """
    AI 에디터 Copilot 서비스

    inline_edit보다 넓은 컨텍스트 인식:
    - 전체 문서 스타일 파악
    - 커서 앞뒤 문단 컨텍스트 활용
    - 스타일 일관성 유지
    """

    DEFAULT_MODEL = os.getenv(
        'COPILOT_MODEL',
        'gemini/gemini-2.5-flash-lite-preview-09-2025'
    )

    def complete(
        self,
        prefix: str,
        context: str = '',
        max_tokens: int = 200,
        style_id: str = 'blog_seo',
    ) -> str:
        """
        자동완성: 커서 위치 이후 텍스트 제안

        Args:
            prefix: 커서 앞 텍스트
            context: 전체 문서 컨텍스트 (일부)
            max_tokens: 최대 생성 토큰

        Returns:
            완성 제안 텍스트
        """
        system_prompt = (
            f"당신은 {style_id} 스타일의 콘텐츠 작성을 도와주는 AI 코파일럿입니다. "
            "텍스트의 자연스러운 계속을 제안하세요. 제안 텍스트만 출력하세요."
        )

        user_prompt = f"다음 텍스트를 자연스럽게 계속 작성하세요:\n\n{prefix[-1000:]}"
        if context:
            user_prompt = f"[문서 컨텍스트]\n{context[:500]}\n\n{user_prompt}"

        return self._call_ai(system_prompt, user_prompt, max_tokens=max_tokens)

    def rewrite(
        self,
        text: str,
        instruction: str,
        context: str = '',
        style_id: str = 'blog_seo',
    ) -> str:
        """
        선택 영역 재작성

        Args:
            text: 재작성할 텍스트
            instruction: 재작성 지시 ('더 간결하게', '전문적으로', '예시 추가' 등)
            context: 주변 문맥
        """
        system_prompt = (
            f"당신은 {style_id} 스타일의 콘텐츠 편집 전문가입니다. "
            "지시에 따라 텍스트를 수정하세요. 수정된 텍스트만 출력하세요. "
            "금지 표현(놀라운, 혁신적, 획기적 등)은 절대 사용하지 마세요."
        )

        user_prompt = (
            f"[편집 지시] {instruction}\n\n"
            f"[원본 텍스트]\n{text}"
        )
        if context:
            user_prompt = f"[문서 컨텍스트]\n{context[:300]}\n\n{user_prompt}"

        return self._call_ai(system_prompt, user_prompt, max_tokens=len(text) * 2 + 500)

    def correct_grammar(self, text: str, language: str = 'ko') -> str:
        """문법/맞춤법 교정"""
        lang_name = {'ko': '한국어', 'en': '영어', 'ja': '일본어'}.get(language, language)
        system_prompt = (
            f"당신은 {lang_name} 문법 및 맞춤법 교정 전문가입니다. "
            "오류를 수정하되 내용과 문체는 최대한 유지하세요. 교정된 텍스트만 출력하세요."
        )
        return self._call_ai(system_prompt, text, max_tokens=len(text) + 200)

    def suggest_improvements(self, text: str, style_id: str = 'blog_seo') -> List[str]:
        """콘텐츠 개선 제안 목록 반환"""
        system_prompt = (
            f"{style_id} 스타일 콘텐츠의 개선점을 3-5개 간단히 나열하세요. "
            "각 제안은 한 줄로, '-'로 시작하세요."
        )

        result = self._call_ai(system_prompt, text[:2000], max_tokens=500)
        suggestions = [
            line.lstrip('- ').strip()
            for line in result.split('\n')
            if line.strip().startswith('-')
        ]
        return suggestions[:5]

    def expand(self, text: str, context: str = '', ratio: float = 1.5) -> str:
        """텍스트 확장 (길이 늘리기)"""
        target_len = int(len(text) * ratio)
        instruction = f"약 {target_len}자로 내용을 풍부하게 확장하세요. 구체적 예시와 설명을 추가하세요."
        return self.rewrite(text, instruction, context)

    def compress(self, text: str, ratio: float = 0.5) -> str:
        """텍스트 압축 (길이 줄이기)"""
        target_len = int(len(text) * ratio)
        instruction = f"약 {target_len}자로 핵심 내용만 남겨 간결하게 요약하세요."
        return self.rewrite(text, instruction)

    def _call_ai(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """AI 호출 공통 메서드"""
        try:
            from services.ai_service import call_litellm
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            response = call_litellm(
                messages,
                model=self.DEFAULT_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Copilot AI 호출 실패: %s", e)
            raise RuntimeError(f"Copilot 오류: {e}") from e
