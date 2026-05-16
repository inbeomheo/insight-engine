"""
콘텐츠 진행률 추적 서비스

콘텐츠 작성 목표 대비 현재 진행률을 계산합니다.
단어수/섹션수/체크리스트 기반 진행률 추적.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r'[\w가-힣]+')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_CHECKLIST_DONE = re.compile(r'^\s*-\s*\[x\]', re.MULTILINE | re.IGNORECASE)
_CHECKLIST_TODO = re.compile(r'^\s*-\s*\[\s?\]', re.MULTILINE)
_IMAGE_PATTERN = re.compile(r'!\[.*?\]\(.*?\)')
_LINK_PATTERN = re.compile(r'(?<!!)\[.*?\]\(.*?\)')


def track_progress(content: str, goals: dict = None) -> dict:
    """콘텐츠 작성 진행률을 추적합니다.

    Args:
        content: 현재 콘텐츠
        goals: 목표 설정 {
            'word_count': int,     # 목표 단어수
            'section_count': int,  # 목표 섹션수
            'image_count': int,    # 목표 이미지수
            'link_count': int,     # 목표 링크수
        }

    Returns:
        {
            'overall_progress': float (0.0~1.0),
            'metrics': {
                'words': {'current': int, 'goal': int, 'progress': float},
                'sections': {'current': int, 'goal': int, 'progress': float},
                'images': {'current': int, 'goal': int, 'progress': float},
                'links': {'current': int, 'goal': int, 'progress': float},
                'checklist': {'done': int, 'total': int, 'progress': float},
            },
            'status': str,
            'suggestions': [str],
        }
    """
    if not content:
        return _empty_result(goals)

    text = content.strip()
    goals = goals or {}

    # 현재 상태 측정
    word_count = len(_WORD_PATTERN.findall(text))
    section_count = len(_HEADING_PATTERN.findall(text))
    image_count = len(_IMAGE_PATTERN.findall(text))
    link_count = len(_LINK_PATTERN.findall(text))
    checklist_done = len(_CHECKLIST_DONE.findall(text))
    checklist_todo = len(_CHECKLIST_TODO.findall(text))
    checklist_total = checklist_done + checklist_todo

    # 목표 대비 진행률
    word_goal = goals.get('word_count', 1000)
    section_goal = goals.get('section_count', 5)
    image_goal = goals.get('image_count', 0)
    link_goal = goals.get('link_count', 0)

    def progress(current: int, goal: int) -> float:
        if goal <= 0:
            return 1.0
        return round(min(1.0, current / goal), 2)

    metrics = {
        'words': {'current': word_count, 'goal': word_goal, 'progress': progress(word_count, word_goal)},
        'sections': {'current': section_count, 'goal': section_goal, 'progress': progress(section_count, section_goal)},
        'images': {'current': image_count, 'goal': image_goal, 'progress': progress(image_count, image_goal)},
        'links': {'current': link_count, 'goal': link_goal, 'progress': progress(link_count, link_goal)},
        'checklist': {
            'done': checklist_done,
            'total': checklist_total,
            'progress': round(checklist_done / checklist_total, 2) if checklist_total > 0 else 1.0,
        },
    }

    # 전체 진행률 (가중 평균: 단어 50%, 섹션 30%, 나머지 20%)
    active_goals = []
    weights = {'words': 0.5, 'sections': 0.3, 'images': 0.1, 'links': 0.1}
    for key, weight in weights.items():
        goal_val = goals.get(f'{key.rstrip("s")}_count', goals.get(f'{key}_count', 0))
        if key == 'words':
            goal_val = goals.get('word_count', 1000)
        elif key == 'sections':
            goal_val = goals.get('section_count', 5)
        if goal_val > 0 or key in ('words', 'sections'):
            active_goals.append((metrics[key]['progress'], weight))

    if active_goals:
        total_weight = sum(w for _, w in active_goals)
        overall = sum(p * w for p, w in active_goals) / total_weight if total_weight > 0 else 0
    else:
        overall = 0.0

    overall = round(min(1.0, overall), 2)

    # 상태 판정
    if overall >= 1.0:
        status = 'complete'
    elif overall >= 0.7:
        status = 'almost_done'
    elif overall >= 0.3:
        status = 'in_progress'
    else:
        status = 'just_started'

    # 제안
    suggestions = _generate_suggestions(metrics, goals)

    return {
        'overall_progress': overall,
        'metrics': metrics,
        'status': status,
        'suggestions': suggestions,
    }


def _generate_suggestions(metrics: dict, goals: dict) -> List[str]:
    """진행률 기반 제안 목록."""
    suggestions = []

    if metrics['words']['progress'] < 0.5 and goals.get('word_count', 0) > 0:
        remaining = metrics['words']['goal'] - metrics['words']['current']
        suggestions.append(f'목표까지 {remaining}단어 더 필요합니다.')

    if metrics['sections']['current'] == 0:
        suggestions.append('헤딩을 추가하여 구조를 잡아보세요.')

    if metrics['sections']['progress'] < 0.5 and goals.get('section_count', 0) > 0:
        remaining = metrics['sections']['goal'] - metrics['sections']['current']
        suggestions.append(f'{remaining}개 섹션을 더 추가하세요.')

    checklist = metrics['checklist']
    if checklist['total'] > 0 and checklist['progress'] < 1.0:
        remaining = checklist['total'] - checklist['done']
        suggestions.append(f'체크리스트 {remaining}개 항목이 미완료입니다.')

    if not suggestions:
        suggestions.append('잘 진행되고 있습니다!')

    return suggestions


def _empty_result(goals: dict = None) -> dict:
    goals = goals or {}
    return {
        'overall_progress': 0.0,
        'metrics': {
            'words': {'current': 0, 'goal': goals.get('word_count', 1000), 'progress': 0.0},
            'sections': {'current': 0, 'goal': goals.get('section_count', 5), 'progress': 0.0},
            'images': {'current': 0, 'goal': goals.get('image_count', 0), 'progress': 0.0},
            'links': {'current': 0, 'goal': goals.get('link_count', 0), 'progress': 0.0},
            'checklist': {'done': 0, 'total': 0, 'progress': 1.0},
        },
        'status': 'just_started',
        'suggestions': ['콘텐츠 작성을 시작하세요.'],
    }
