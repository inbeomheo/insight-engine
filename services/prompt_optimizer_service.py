"""
적응형 프롬프트 최적화 서비스

사용자 피드백(좋아요/싫어요)을 수집하고 스타일별 효과를 분석하여
프롬프트 미세 조정 제안을 생성합니다.
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 피드백 저장 경로
_FEEDBACK_DIR = Path(os.getenv('FEEDBACK_DATA_DIR', 'data/feedback'))

# 최적화에 필요한 최소 피드백 수
_MIN_FEEDBACK_FOR_OPTIMIZATION = 5


def _ensure_feedback_dir():
    """피드백 저장 디렉토리를 생성합니다."""
    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def save_feedback(
    style_id: str,
    content_id: str,
    rating: str,
    user_id: Optional[str] = None,
    comment: Optional[str] = None,
) -> dict:
    """사용자 피드백을 저장합니다.

    Args:
        style_id: 스타일 ID (예: 'blog_seo')
        content_id: 콘텐츠 고유 ID
        rating: 'like' 또는 'dislike'
        user_id: 사용자 ID (선택)
        comment: 추가 코멘트 (선택)

    Returns:
        {"ok": True, "feedback_id": str}
    """
    if rating not in ('like', 'dislike'):
        raise ValueError(f"rating은 'like' 또는 'dislike'만 가능: {rating}")

    _ensure_feedback_dir()

    feedback = {
        'style_id': style_id,
        'content_id': content_id,
        'rating': rating,
        'user_id': user_id,
        'comment': comment,
        'timestamp': time.time(),
    }

    feedback_id = f"{style_id}_{int(time.time() * 1000)}"
    filepath = _FEEDBACK_DIR / f"{style_id}.jsonl"

    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(feedback, ensure_ascii=False) + '\n')

    logger.info(f"피드백 저장: style={style_id}, rating={rating}")
    return {'ok': True, 'feedback_id': feedback_id}


def get_feedback_stats(style_id: str) -> dict:
    """스타일별 피드백 통계를 반환합니다.

    Returns:
        {"total": int, "likes": int, "dislikes": int, "like_ratio": float}
    """
    filepath = _FEEDBACK_DIR / f"{style_id}.jsonl"
    if not filepath.exists():
        return {'total': 0, 'likes': 0, 'dislikes': 0, 'like_ratio': 0.0}

    likes = 0
    dislikes = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get('rating') == 'like':
                    likes += 1
                else:
                    dislikes += 1
    except Exception as e:
        logger.warning(f"피드백 통계 읽기 실패: {e}")
        return {'total': 0, 'likes': 0, 'dislikes': 0, 'like_ratio': 0.0}

    total = likes + dislikes
    return {
        'total': total,
        'likes': likes,
        'dislikes': dislikes,
        'like_ratio': round(likes / total, 3) if total > 0 else 0.0,
    }


def optimize_prompt(style_id: str) -> dict:
    """피드백 기반으로 프롬프트 최적화 제안을 생성합니다.

    Args:
        style_id: 스타일 ID

    Returns:
        {"style_id": str, "stats": dict, "suggestions": list[str], "adjusted_temperature": float|None}
    """
    stats = get_feedback_stats(style_id)

    suggestions = []
    adjusted_temperature = None

    if stats['total'] < _MIN_FEEDBACK_FOR_OPTIMIZATION:
        suggestions.append(
            f"최적화를 위해 최소 {_MIN_FEEDBACK_FOR_OPTIMIZATION}개 피드백이 필요합니다 "
            f"(현재: {stats['total']}개)"
        )
        return {
            'style_id': style_id,
            'stats': stats,
            'suggestions': suggestions,
            'adjusted_temperature': None,
        }

    like_ratio = stats['like_ratio']

    # 만족도가 낮으면 temperature 낮춰서 안정적인 출력 유도
    if like_ratio < 0.4:
        adjusted_temperature = -0.1
        suggestions.append('만족도가 낮습니다. temperature를 낮춰 안정적인 출력을 유도합니다.')
        suggestions.append('프롬프트에 구체적인 예시를 추가하는 것을 권장합니다.')
    elif like_ratio < 0.6:
        suggestions.append('만족도가 보통입니다. 프롬프트 구조 개선을 검토하세요.')
    else:
        suggestions.append('만족도가 높습니다. 현재 설정을 유지합니다.')

    # 싫어요에 코멘트가 있으면 수집
    dislike_comments = _get_dislike_comments(style_id, limit=10)
    if dislike_comments:
        suggestions.append(f'최근 부정 피드백 키워드: {", ".join(dislike_comments[:5])}')

    return {
        'style_id': style_id,
        'stats': stats,
        'suggestions': suggestions,
        'adjusted_temperature': adjusted_temperature,
    }


def _get_dislike_comments(style_id: str, limit: int = 10) -> list:
    """싫어요 피드백의 코멘트를 수집합니다."""
    filepath = _FEEDBACK_DIR / f"{style_id}.jsonl"
    if not filepath.exists():
        return []

    comments = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get('rating') == 'dislike' and entry.get('comment'):
                    comments.append(entry['comment'])
    except Exception:
        pass

    return comments[-limit:]
