"""
WriterAgent — 리서치 결과 기반 콘텐츠 초안 작성

파이프라인 2단계: ResearchAgent 결과와 스타일 프롬프트를 조합하여
초안 콘텐츠를 생성합니다.
"""
import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

_WRITER_SYSTEM_CONTEXT = """당신은 전문 콘텐츠 작성자입니다. 아래 정보를 바탕으로 콘텐츠를 작성하세요.

[리서치 결과]
- 핵심 주제: {main_topic}
- 핵심 포인트: {key_points}
- 대상 독자: {target_audience}
- 톤: {tone}

[영상 자막]
{transcript}
{web_context_block}
[스타일 가이드]
{style_prompt}

위 정보를 바탕으로 마크다운 형식의 콘텐츠를 작성하세요.
첫 줄은 반드시 '# 제목' 형식의 H1 제목으로 시작하세요.
결과는 반드시 한국어로 작성하세요.
"""


class WriterAgent(BaseAgent):
    """콘텐츠 초안 작성 에이전트."""

    @property
    def name(self) -> str:
        return 'writer'

    @property
    def role(self) -> str:
        return '콘텐츠 초안 작성'

    def execute(self, context: dict) -> dict:
        """리서치 결과를 기반으로 콘텐츠 초안을 작성합니다.

        Args:
            context: {
                'transcript': 자막 텍스트,
                'style': 스타일 ID,
                'style_prompt': 스타일 프롬프트 (str),
                'modifiers': 모디파이어 dict,
                # ResearchAgent 결과
                'main_topic': str,
                'key_points': list[str],
                'target_audience': str,
                'tone': str,
                'web_context': str,
                ...
            }

        Returns:
            {
                'agent': 'writer',
                'draft': str,     # 마크다운 초안
                'title': str,     # 추출한 제목
            }
        """
        transcript = context.get('transcript', '')
        style_prompt = context.get('style_prompt', '')
        modifiers = context.get('modifiers') or {}

        # ResearchAgent 결과
        main_topic = context.get('main_topic', '')
        key_points = context.get('key_points', [])
        target_audience = context.get('target_audience', '일반 독자')
        tone = context.get('tone', '정보 제공')
        web_context = context.get('web_context', '')

        # 자막 길이 제한
        max_transcript = 8000
        truncated_transcript = transcript[:max_transcript]

        # 웹 컨텍스트 블록
        web_context_block = ''
        if web_context:
            web_context_block = f"\n[웹 검색 참고자료]\n{web_context}\n"

        # key_points 포맷
        key_points_str = '\n'.join(f'  - {p}' for p in key_points) if key_points else '  (없음)'

        prompt = _WRITER_SYSTEM_CONTEXT.format(
            main_topic=main_topic or '(분석 없음)',
            key_points=key_points_str,
            target_audience=target_audience,
            tone=tone,
            transcript=truncated_transcript,
            web_context_block=web_context_block,
            style_prompt=style_prompt or '블로그 형식으로 자연스럽게 작성하세요.',
        )

        # 길이 모디파이어에 따른 max_tokens
        from config import LENGTH_MAX_TOKENS
        length = modifiers.get('length', 'medium')
        max_tokens = LENGTH_MAX_TOKENS.get(length, 8000)

        try:
            draft = self._call_ai(prompt, temperature=0.7, max_tokens=max_tokens)
        except Exception as e:
            self._logger.error(f'[WriterAgent] 콘텐츠 작성 실패: {e}')
            raise

        title = self._extract_title(draft)

        return {
            'agent': self.name,
            'draft': draft,
            'title': title,
        }

    def _extract_title(self, markdown: str) -> str:
        """마크다운에서 H1 제목을 추출합니다."""
        for line in markdown.split('\n'):
            stripped = line.strip()
            if stripped.startswith('# '):
                return stripped[2:].strip()
        return 'AI 생성 콘텐츠'
