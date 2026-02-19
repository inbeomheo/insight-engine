"""댓글 심층 분석 서비스 — 댓글을 인사이트/질문/반론/감상으로 분류"""
import json
import logging

from services import ai_service
from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT

logger = logging.getLogger(__name__)


def analyze_comments(comments, model):
    """댓글 리스트를 AI로 심층 분석하여 4가지 카테고리로 분류

    Args:
        comments: 댓글 문자열 리스트
        model: LiteLLM 모델 ID

    Returns:
        dict: {'insights': [...], 'questions': [...],
               'fact_checks': [...], 'sentiments': [...]}
        None: 댓글이 없거나 분석 실패 시
    """
    if not comments:
        return None

    comments_text = '\n'.join(f'- {c}' for c in comments[:50])
    content = f'다음 댓글들을 분석해주세요:\n\n{comments_text}'

    try:
        result = ai_service.create_content(
            content=content,
            model=model,
            style_prompt=COMMENT_ANALYZER_PROMPT,
            style_id='comment_summary'
        )
        raw = result.get('content', '')
        # JSON 블록 추출 (```json ... ``` 형태 처리)
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0]
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0]
        parsed = json.loads(raw.strip())
        return {
            'insights': parsed.get('insights', []),
            'questions': parsed.get('questions', []),
            'fact_checks': parsed.get('fact_checks', []),
            'sentiments': parsed.get('sentiments', []),
            'usage': result.get('usage', {})
        }
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning('댓글 분석 JSON 파싱 실패: %s', e)
        return None
    except Exception as e:
        logger.error('댓글 심층 분석 실패: %s', e)
        return None
