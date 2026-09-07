"""
EditorAgent — 초안 교정 및 품질 검증

파이프라인 3단계: WriterAgent가 작성한 초안을 검토하고,
문법/일관성/가독성을 개선합니다.
"""
import json
import re
import logging

from .base_agent import BaseAgent
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

_EDITOR_PROMPT = """당신은 전문 편집자입니다. 아래 콘텐츠 초안을 교정하세요.

[원본 자막 요약]
{summary}

[초안]
{draft}

교정 지침:
1. 문법 오류 및 맞춤법 수정
2. 문장 가독성 개선 (너무 긴 문장 분리)
3. 구조 일관성 확인 (헤딩 계층, 단락 흐름)
4. 아래 금지 표현 제거:
   놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운,
   드디어, 탁월한, 인상적, 뛰어난, 강력한
5. 자막에 없는 내용 추가 금지 (사실 확인)
6. 첫 줄 H1 제목 유지

교정된 콘텐츠 전체를 마크다운 형식으로 출력하세요.
추가 설명 없이 교정된 본문만 출력하세요."""

_FEEDBACK_PROMPT = """아래 콘텐츠의 품질을 평가하세요.

[콘텐츠]
{content}

JSON 형식으로 출력하세요 (설명 없이 JSON만):
{{
  "grade": "A/B/C/D 중 하나",
  "readability": 1에서 10 사이 점수,
  "accuracy": 1에서 10 사이 점수,
  "issues": ["발견된 문제점 1", "발견된 문제점 2"],
  "summary": "평가 한 줄 요약"
}}"""


class EditorAgent(BaseAgent):
    """콘텐츠 교정 및 품질 검증 에이전트."""

    @property
    def name(self) -> str:
        return 'editor'

    @property
    def role(self) -> str:
        return '콘텐츠 교정 및 품질 검증'

    def execute(self, context: dict) -> dict:
        """초안을 교정하고 품질 평가를 수행합니다.

        Args:
            context: {
                'draft': WriterAgent가 생성한 초안 (str),
                'summary': ResearchAgent의 자막 요약 (str),
                ...
            }

        Returns:
            {
                'agent': 'editor',
                'edited_content': str,   # 교정된 콘텐츠
                'title': str,            # 교정된 콘텐츠의 제목
                'quality': dict,         # 품질 평가 결과 (grade, readability, accuracy, issues, summary)
            }
        """
        draft = context.get('draft', '')
        summary = context.get('summary', '')

        if not draft:
            self._logger.warning('[EditorAgent] 초안 없음 — 빈 결과 반환')
            return {
                'agent': self.name,
                'edited_content': '',
                'title': '',
                'quality': {'grade': 'D', 'readability': 0, 'accuracy': 0, 'issues': ['초안 없음'], 'summary': '초안이 없습니다.'},
            }

        # 1단계: 교정
        edit_prompt = _EDITOR_PROMPT.format(
            summary=summary[:500] if summary else '요약 없음',
            draft=draft,
        )
        from config import DETAIL_PRESETS, LENGTH_MAX_TOKENS
        detail = DETAIL_PRESETS.get(context.get('detail_level'), DETAIL_PRESETS['standard'])
        length = (context.get('modifiers') or {}).get('length', 'medium')
        # 긴 초안을 작성한 뒤 더 작은 교정 상한으로 끝부분을 잃지 않게 한다.
        max_tokens = max(12000, int(LENGTH_MAX_TOKENS.get(length, 8000)
                                    * detail['max_tokens_multiplier']))

        try:
            edited = self._call_ai(edit_prompt, temperature=0.3, max_tokens=max_tokens)
        except UsageLockUnavailable:
            raise
        except Exception as e:
            self._logger.error(f'[EditorAgent] 교정 실패: {e}')
            # 교정 실패 시 원본 초안 사용
            edited = draft

        # 2단계: 품질 평가 (가벼운 모델로 별도 호출)
        quality = self._evaluate_quality(edited)

        title = self._extract_title(edited)

        return {
            'agent': self.name,
            'edited_content': edited,
            'title': title,
            'quality': quality,
        }

    def _evaluate_quality(self, content: str) -> dict:
        """콘텐츠 품질을 평가합니다. 실패 시 기본값 반환."""
        try:
            feedback_prompt = _FEEDBACK_PROMPT.format(content=content[:3000])
            raw = self._call_ai(feedback_prompt, temperature=0.1, max_tokens=500)
            return self._parse_json(raw)
        except UsageLockUnavailable:
            raise
        except Exception as e:
            self._logger.warning(f'[EditorAgent] 품질 평가 실패 (무시): {e}')
            return {
                'grade': 'B',
                'readability': 7,
                'accuracy': 7,
                'issues': [],
                'summary': '품질 평가를 수행할 수 없습니다.',
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
            return {'grade': 'B', 'readability': 7, 'accuracy': 7, 'issues': [], 'summary': 'JSON 파싱 실패'}

    def _extract_title(self, markdown: str) -> str:
        """마크다운에서 H1 제목을 추출합니다."""
        for line in markdown.split('\n'):
            stripped = line.strip()
            if stripped.startswith('# '):
                return stripped[2:].strip()
        return 'AI 생성 콘텐츠'
