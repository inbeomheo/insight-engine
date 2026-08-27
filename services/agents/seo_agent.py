"""
SEOAgent — SEO 최적화 및 메타데이터 생성

파이프라인 4단계: 교정된 콘텐츠에 SEO 메타데이터(키워드, 메타 설명,
FAQ, 구조화 데이터)를 추가합니다.
"""
import json
import re
import logging

from .base_agent import BaseAgent
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

_SEO_PROMPT = """당신은 SEO 전문가입니다. 아래 콘텐츠의 SEO 메타데이터를 생성하세요.

[콘텐츠 제목]
{title}

[콘텐츠 요약]
{summary}

[핵심 주제]
{main_topic}

JSON 형식으로 출력하세요 (설명 없이 JSON만):
{{
  "meta_title": "검색엔진 최적화 제목 (60자 이내, 핵심 키워드 포함)",
  "meta_description": "메타 설명 (150자 이내, 클릭 유도)",
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "faq": [
    {{"question": "자주 묻는 질문 1", "answer": "답변 1 (100자 이내)"}},
    {{"question": "자주 묻는 질문 2", "answer": "답변 2 (100자 이내)"}}
  ],
  "og_title": "Open Graph 제목 (SNS 공유용)",
  "og_description": "Open Graph 설명 (100자 이내, SNS 공유용)"
}}"""


class SEOAgent(BaseAgent):
    """SEO 최적화 및 메타데이터 생성 에이전트."""

    @property
    def name(self) -> str:
        return 'seo'

    @property
    def role(self) -> str:
        return 'SEO 최적화 및 메타데이터 생성'

    def execute(self, context: dict) -> dict:
        """SEO 메타데이터와 FAQ를 생성합니다.

        Args:
            context: {
                'edited_content': EditorAgent가 교정한 콘텐츠 (str),
                'title': 콘텐츠 제목 (str),
                'main_topic': ResearchAgent의 핵심 주제 (str),
                'summary': ResearchAgent의 요약 (str),
                'url': YouTube 영상 URL (str, 옵션),
                ...
            }

        Returns:
            {
                'agent': 'seo',
                'meta_title': str,
                'meta_description': str,
                'keywords': list[str],
                'faq': list[dict],
                'og_title': str,
                'og_description': str,
                'json_ld': dict,    # VideoObject JSON-LD 스키마
            }
        """
        edited_content = context.get('edited_content', '')
        title = context.get('title', '')
        main_topic = context.get('main_topic', '')
        summary = context.get('summary', '')
        url = context.get('url', '')

        if not edited_content:
            self._logger.warning('[SEOAgent] 교정된 콘텐츠 없음')
            return self._empty_result()

        seo_prompt = _SEO_PROMPT.format(
            title=title or 'AI 생성 콘텐츠',
            summary=summary[:300] if summary else edited_content[:300],
            main_topic=main_topic or title,
        )

        seo_data = {}
        try:
            raw = self._call_ai(seo_prompt, temperature=0.4, max_tokens=1500)
            seo_data = self._parse_json(raw)
        except UsageLockUnavailable:
            raise
        except Exception as e:
            self._logger.error(f'[SEOAgent] SEO 메타데이터 생성 실패: {e}')
            seo_data = self._fallback_seo(title, summary)

        # JSON-LD VideoObject 스키마 생성
        json_ld = {}
        if url:
            try:
                from services.seo.seo_metadata_service import generate_video_object_schema
                json_ld = generate_video_object_schema(
                    video_url=url,
                    title=seo_data.get('meta_title', title),
                    description=seo_data.get('meta_description', ''),
                )
            except Exception as e:
                self._logger.warning(f'[SEOAgent] JSON-LD 생성 실패 (무시): {e}')

        return {
            'agent': self.name,
            'meta_title': seo_data.get('meta_title', title),
            'meta_description': seo_data.get('meta_description', ''),
            'keywords': seo_data.get('keywords', []),
            'faq': seo_data.get('faq', []),
            'og_title': seo_data.get('og_title', title),
            'og_description': seo_data.get('og_description', ''),
            'json_ld': json_ld,
        }

    def _parse_json(self, raw: str) -> dict:
        """AI 응답에서 JSON을 파싱합니다."""
        text = re.sub(r'```json\s*', '', raw)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

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

    def _fallback_seo(self, title: str, summary: str) -> dict:
        """SEO 생성 실패 시 기본값을 반환합니다."""
        return {
            'meta_title': title[:60] if title else 'AI 생성 콘텐츠',
            'meta_description': summary[:150] if summary else '',
            'keywords': [],
            'faq': [],
            'og_title': title,
            'og_description': summary[:100] if summary else '',
        }

    def _empty_result(self) -> dict:
        """빈 결과를 반환합니다."""
        return {
            'agent': self.name,
            'meta_title': '',
            'meta_description': '',
            'keywords': [],
            'faq': [],
            'og_title': '',
            'og_description': '',
            'json_ld': {},
        }
