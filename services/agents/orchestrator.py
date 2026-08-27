"""
오케스트레이터 — 멀티에이전트 파이프라인 조율

Research → Writer → Editor → SEO 에이전트를 순서대로 실행하며
각 단계 결과를 다음 에이전트 컨텍스트에 전달합니다.

Flask는 동기 방식이므로 ThreadPoolExecutor를 사용합니다.
"""
import html as html_lib
import logging
import time
from typing import Callable, Optional

import markdown

from services.usage.usage_lock import UsageLockUnavailable

from .research_agent import ResearchAgent
from .writer_agent import WriterAgent
from .editor_agent import EditorAgent
from .seo_agent import SEOAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """멀티에이전트 파이프라인을 조율하는 오케스트레이터.

    파이프라인 흐름:
        ResearchAgent → WriterAgent → EditorAgent → SEOAgent

    Writer와 Editor는 순차적으로, Research + (Writer+Editor+SEO)는
    Research 완료 후 순차 실행합니다.
    """

    def __init__(
        self,
        model: str = None,
        on_cost_start: Optional[Callable[[], None]] = None,
    ):
        """
        Args:
            model: 모든 에이전트가 공유할 모델 ID. None이면 자동 선택.
        """
        self.model = model
        self._research = ResearchAgent(model=model, on_cost_start=on_cost_start)
        self._writer = WriterAgent(model=model, on_cost_start=on_cost_start)
        self._editor = EditorAgent(model=model, on_cost_start=on_cost_start)
        self._seo = SEOAgent(model=model, on_cost_start=on_cost_start)

    def run(self, transcript: str, style: str, style_prompt: str,
            url: str = '', modifiers: dict = None, user_id: str = None) -> dict:
        """전체 파이프라인을 실행합니다.

        Args:
            transcript: YouTube 자막 텍스트
            style: 콘텐츠 스타일 ID (예: 'blog_seo')
            style_prompt: 스타일 프롬프트 문자열
            url: YouTube 영상 URL (SEO 스키마 생성용, 옵션)
            modifiers: 모디파이어 dict (length, writing_style 등)
            user_id: 사용자 ID (로깅용, 옵션)

        Returns:
            {
                'title': str,
                'content': str,          # 마크다운
                'html': str,             # HTML 변환본
                'usage': dict,           # 토큰 사용량 (에이전트 합산)
                'agent_results': dict,   # 각 에이전트 개별 결과
                'quality': dict,         # EditorAgent 품질 평가
                'seo': dict,             # SEOAgent 메타데이터
                'elapsed_time': float,   # 전체 실행 시간(초)
            }
        """
        start_time = time.time()
        modifiers = modifiers or {}

        logger.info(f'[Orchestrator] 파이프라인 시작: style={style}, url={url[:50] if url else ""}')

        # 공통 컨텍스트 초기값
        context = {
            'transcript': transcript,
            'style': style,
            'style_prompt': style_prompt,
            'url': url,
            'modifiers': modifiers,
            'user_id': user_id,
        }

        agent_results = {}

        # 1단계: Research (웹 검색 포함)
        try:
            logger.info('[Orchestrator] 1단계: Research 시작')
            research_result = self._research.execute(context)
            agent_results['research'] = research_result
            context.update(research_result)
            logger.info(f'[Orchestrator] 1단계: Research 완료 — topic={research_result.get("main_topic", "")}')
        except UsageLockUnavailable:
            raise
        except Exception as e:
            logger.error(f'[Orchestrator] Research 실패: {e}')
            # Research 실패 시 빈 결과로 계속 진행
            context.update({
                'main_topic': '', 'key_points': [], 'target_audience': '',
                'tone': '', 'summary': '', 'web_results': [], 'web_context': '',
            })

        # 2단계: Writer (초안 작성)
        try:
            logger.info('[Orchestrator] 2단계: Writer 시작')
            writer_result = self._writer.execute(context)
            agent_results['writer'] = writer_result
            context.update(writer_result)
            logger.info('[Orchestrator] 2단계: Writer 완료')
        except UsageLockUnavailable:
            raise
        except Exception as e:
            logger.error(f'[Orchestrator] Writer 실패: {e}')
            raise RuntimeError(f'콘텐츠 작성 실패: {e}') from e

        # 3단계: Editor (교정) — 4단계 SEO와 병렬 실행 가능하나
        # SEO가 편집된 콘텐츠를 필요로 하므로 순차 실행
        try:
            logger.info('[Orchestrator] 3단계: Editor 시작')
            editor_result = self._editor.execute(context)
            agent_results['editor'] = editor_result
            context.update(editor_result)
            logger.info(f'[Orchestrator] 3단계: Editor 완료 — grade={editor_result.get("quality", {}).get("grade", "?")}')
        except UsageLockUnavailable:
            raise
        except Exception as e:
            logger.error(f'[Orchestrator] Editor 실패: {e}')
            # Editor 실패 시 원본 초안 사용
            context['edited_content'] = context.get('draft', '')
            context['title'] = context.get('title', 'AI 생성 콘텐츠')
            agent_results['editor'] = {
                'agent': 'editor', 'edited_content': context['edited_content'],
                'title': context['title'], 'quality': {},
            }

        # 4단계: SEO (메타데이터 생성)
        try:
            logger.info('[Orchestrator] 4단계: SEO 시작')
            seo_result = self._seo.execute(context)
            agent_results['seo'] = seo_result
            context.update(seo_result)
            logger.info('[Orchestrator] 4단계: SEO 완료')
        except UsageLockUnavailable:
            raise
        except Exception as e:
            logger.error(f'[Orchestrator] SEO 실패 (무시): {e}')
            seo_result = {'agent': 'seo', 'meta_title': '', 'meta_description': '', 'keywords': [], 'faq': [], 'json_ld': {}}
            agent_results['seo'] = seo_result

        elapsed = time.time() - start_time

        # 최종 콘텐츠 조합
        final_content = context.get('edited_content') or context.get('draft', '')
        final_title = context.get('title', 'AI 생성 콘텐츠')

        # HTML 변환
        try:
            html = markdown.markdown(final_content, extensions=['tables', 'fenced_code', 'nl2br'])
        except Exception as md_err:
            logger.warning(f'[Orchestrator] 마크다운 변환 실패: {md_err}')
            html = f'<pre>{html_lib.escape(final_content)}</pre>'

        logger.info(f'[Orchestrator] 파이프라인 완료: elapsed={elapsed:.1f}초')

        return {
            'title': final_title,
            'content': final_content,
            'html': html,
            'usage': {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0},
            'agent_results': agent_results,
            'quality': agent_results.get('editor', {}).get('quality', {}),
            'seo': {
                'meta_title': context.get('meta_title', ''),
                'meta_description': context.get('meta_description', ''),
                'keywords': context.get('keywords', []),
                'faq': context.get('faq', []),
                'og_title': context.get('og_title', ''),
                'og_description': context.get('og_description', ''),
                'json_ld': context.get('json_ld', {}),
            },
            'elapsed_time': elapsed,
        }
