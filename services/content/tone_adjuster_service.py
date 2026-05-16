"""
콘텐츠 톤 분석 및 조정 서비스

규칙 기반으로 현재 톤을 분석하고,
AI를 사용하여 목표 톤으로 변환합니다.
"""
import logging
import re

from services.core import ai_service

logger = logging.getLogger(__name__)

# 톤 정의 및 특성 키워드
TONE_PROFILES = {
    'formal': {
        'label': '격식체',
        'markers': ['습니다', '입니다', '하였', '됩니다', '바랍니다', '것입니다', '드립니다'],
        'negative_markers': ['ㅋ', 'ㅎ', '~', '!!!!', '??'],
        'description': '공식 보고서, 논문, 비즈니스 문서에 적합한 격식체',
    },
    'casual': {
        'label': '캐주얼',
        'markers': ['해요', '예요', '거예요', '네요', '죠', '잖아요', '할게요'],
        'negative_markers': ['하였으며', '것이다', '바이다'],
        'description': '블로그, 일상 대화에 적합한 편안한 톤',
    },
    'persuasive': {
        'label': '설득적',
        'markers': ['해야 합니다', '필수', '반드시', '지금', '바로', '핵심은', '중요한 점은', '꼭'],
        'negative_markers': [],
        'description': '독자를 행동으로 이끄는 설득적 톤',
    },
    'neutral': {
        'label': '중립적',
        'markers': ['이다', '있다', '된다', '한다', '것이다'],
        'negative_markers': ['!', '꼭', '반드시', '정말'],
        'description': '객관적 사실 전달에 적합한 중립적 톤',
    },
    'humorous': {
        'label': '유머러스',
        'markers': ['ㅋ', 'ㅎ', '~', '요ㅋ', '잠깐', '아니', '사실은', '웃긴 건'],
        'negative_markers': ['하였으며', '바이다'],
        'description': '가벼운 유머가 섞인 친근한 톤',
    },
}

SUPPORTED_TONES = list(TONE_PROFILES.keys())


def _count_markers(text: str, markers: list) -> int:
    """텍스트에서 마커 등장 횟수를 셉니다."""
    count = 0
    for marker in markers:
        count += len(re.findall(re.escape(marker), text))
    return count


def _sentence_count(text: str) -> int:
    """대략적 문장 수를 반환합니다."""
    sentences = re.split(r'[.!?\n]+', text)
    return max(1, len([s for s in sentences if s.strip()]))


def analyze_tone(content: str) -> dict:
    """콘텐츠의 현재 톤을 규칙 기반으로 분석합니다.

    Returns:
        {
            'primary_tone': str,
            'scores': {tone: float, ...},
            'details': {tone: {'label': str, 'score': float, 'marker_count': int}, ...},
            'sentence_count': int,
            'char_count': int,
        }
    """
    if not content or not content.strip():
        return {
            'primary_tone': 'neutral',
            'scores': {t: 0.0 for t in SUPPORTED_TONES},
            'details': {},
            'sentence_count': 0,
            'char_count': 0,
        }

    text = content.strip()
    sent_count = _sentence_count(text)
    scores = {}

    for tone, profile in TONE_PROFILES.items():
        pos_count = _count_markers(text, profile['markers'])
        neg_count = _count_markers(text, profile['negative_markers'])
        # 문장 수 대비 마커 밀도로 정규화
        raw_score = (pos_count - neg_count * 0.5) / sent_count
        scores[tone] = round(max(0.0, raw_score), 4)

    # 모든 점수가 0이면 neutral로 판정
    max_score = max(scores.values())
    if max_score == 0:
        primary_tone = 'neutral'
        scores['neutral'] = 0.5
    else:
        primary_tone = max(scores, key=scores.get)

    details = {}
    for tone in SUPPORTED_TONES:
        profile = TONE_PROFILES[tone]
        details[tone] = {
            'label': profile['label'],
            'score': scores[tone],
            'marker_count': _count_markers(text, profile['markers']),
        }

    return {
        'primary_tone': primary_tone,
        'scores': scores,
        'details': details,
        'sentence_count': sent_count,
        'char_count': len(text),
    }


def adjust_tone(content: str, target_tone: str, model: str) -> dict:
    """콘텐츠를 목표 톤으로 AI 변환합니다.

    Args:
        content: 원본 콘텐츠
        target_tone: 목표 톤 (formal/casual/persuasive/neutral/humorous)
        model: AI 모델 ID

    Returns:
        {
            'original_tone': str,
            'target_tone': str,
            'adjusted_content': str,
            'char_count': int,
            'tone_analysis': dict,
        }
    """
    if target_tone not in SUPPORTED_TONES:
        return {'error': f'지원하지 않는 톤: {target_tone}. 지원: {SUPPORTED_TONES}'}

    if not content or not content.strip():
        return {'error': '콘텐츠가 비어 있습니다.'}

    original_analysis = analyze_tone(content)
    profile = TONE_PROFILES[target_tone]

    prompt = f"""다음 콘텐츠의 톤을 "{profile['label']}" 스타일로 변환해주세요.

## 목표 톤 설명
{profile['description']}

## 규칙
- 원본 내용(정보, 사실, 구조)은 그대로 유지
- 톤과 어투만 변경
- 마크다운 서식은 유지
- 원본 길이와 비슷하게 유지

## 원본 콘텐츠
{content[:5000]}

변환된 콘텐츠만 출력하세요 (다른 설명 없이):"""

    try:
        result = ai_service.create_content(prompt, model, style_prompt='', style_id='blog_seo')
        adjusted_text = result.get('content', '').strip()
        adjusted_analysis = analyze_tone(adjusted_text)

        return {
            'original_tone': original_analysis['primary_tone'],
            'target_tone': target_tone,
            'adjusted_content': adjusted_text,
            'char_count': len(adjusted_text),
            'tone_analysis': adjusted_analysis,
        }
    except Exception as e:
        logger.error(f"톤 조정 실패: {e}")
        return {'error': '톤 조정 중 오류가 발생했습니다.'}


def get_tone_list() -> list:
    """지원하는 톤 목록을 반환합니다."""
    return [
        {'id': tone, 'label': profile['label'], 'description': profile['description']}
        for tone, profile in TONE_PROFILES.items()
    ]
