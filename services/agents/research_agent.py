"""
ResearchAgent — 자막 분석 + 핵심 토픽 추출 + 웹 검색 보강

파이프라인 1단계: 원시 자막을 분석하여 주요 토픽, 핵심 포인트,
웹 검색 보강 컨텍스트를 생성합니다.
"""
import json
import re
import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

_RESEARCH_PROMPT = """당신은 전문 리서처입니다. 아래 YouTube 영상 자막을 분석하세요.

[자막]
{transcript}

다음을 JSON 형식으로 출력하세요 (설명 없이 JSON만):
{{
  "main_topic": "영상의 핵심 주제 (한 문장)",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
  "target_audience": "대상 시청자 (한 문장)",
  "tone": "영상 톤 (예: 교육적, 실용적, 비판적, 열정적 등)",
  "search_query": "이 주제를 보강할 최적의 웹 검색 쿼리 (영어 또는 한국어 1개)",
  "summary": "자막 핵심 내용 요약 (200자 이내)"
}}"""


class ResearchAgent(BaseAgent):
    """자막 분석 및 리서치 에이전트."""

    @property
    def name(self) -> str:
        return 'research'

    @property
    def role(self) -> str:
        return '자막 분석 및 핵심 토픽 추출'

    def execute(self, context: dict) -> dict:
        """자막을 분석하고 웹 검색으로 보강합니다.

        Args:
            context: {
                'transcript': YouTube 자막 텍스트 (str),
                'style': 콘텐츠 스타일 ID (str),
                ...기타 공통 파라미터
            }

        Returns:
            {
                'agent': 'research',
                'main_topic': str,
                'key_points': list[str],
                'target_audience': str,
                'tone': str,
                'summary': str,
                'web_results': list[dict],  # 웹 검색 결과 (없으면 빈 리스트)
                'web_context': str,         # 프롬프트 주입용 포맷된 웹 컨텍스트
            }
        """
        transcript = context.get('transcript', '')
        if not transcript:
            self._logger.warning('[ResearchAgent] 자막 없음 — 빈 결과 반환')
            return {
                'agent': self.name,
                'main_topic': '',
                'key_points': [],
                'target_audience': '',
                'tone': '',
                'summary': '',
                'web_results': [],
                'web_context': '',
            }

        # 자막 길이 제한 (리서치는 핵심 부분만 분석)
        truncated = transcript[:6000]

        prompt = _RESEARCH_PROMPT.format(transcript=truncated)

        research_data = {}
        try:
            raw = self._call_ai(prompt, temperature=0.3, max_tokens=1000)
            research_data = self._parse_json(raw)
        except Exception as e:
            self._logger.error(f'[ResearchAgent] AI 분석 실패: {e}')
            research_data = {
                'main_topic': '알 수 없음',
                'key_points': [],
                'target_audience': '일반 시청자',
                'tone': '정보 제공',
                'search_query': '',
                'summary': transcript[:200],
            }

        # 웹 검색 보강 (Tavily 키가 있을 때만)
        web_results = []
        web_context = ''
        search_query = research_data.get('search_query', '')
        if search_query:
            try:
                from services import web_search_service
                web_results = web_search_service.search(search_query, max_results=3)
                if web_results:
                    web_context = self._format_web_context(web_results)
            except Exception as e:
                self._logger.warning(f'[ResearchAgent] 웹 검색 실패 (무시): {e}')

        return {
            'agent': self.name,
            'main_topic': research_data.get('main_topic', ''),
            'key_points': research_data.get('key_points', []),
            'target_audience': research_data.get('target_audience', ''),
            'tone': research_data.get('tone', ''),
            'summary': research_data.get('summary', ''),
            'web_results': web_results,
            'web_context': web_context,
        }

    def _parse_json(self, raw: str) -> dict:
        """AI 응답에서 JSON을 파싱합니다."""
        # ```json ... ``` 블록 제거
        text = re.sub(r'```json\s*', '', raw)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # JSON 객체 추출
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _format_web_context(self, results: list) -> str:
        """웹 검색 결과를 프롬프트 주입 형식으로 변환합니다."""
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get('title', '')
            content = r.get('content', '')[:300]
            url = r.get('url', '')
            lines.append(f"{i}. {title}\n   {content}\n   출처: {url}")
        return '\n\n'.join(lines)
