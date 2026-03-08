"""
콘텐츠 감성 분석 서비스

텍스트의 감성 톤(긍정/부정/중립)을 규칙 기반으로 분석합니다.
문단별 감성 흐름, 전체 톤 분포, 감정 키워드를 제공합니다.
"""
import re
import logging


logger = logging.getLogger(__name__)

# 긍정 감성어 (한국어)
_POSITIVE_WORDS = {
    '좋은', '훌륭', '우수', '효과적', '성공', '향상', '개선', '발전',
    '편리', '유용', '강력', '안정', '빠른', '쉬운', '간단', '뛰어난',
    '혁신', '성장', '이점', '장점', '추천', '만족', '긍정', '기회',
    '최적', '완벽', '인기', '신뢰', '안전', '효율',
}

# 부정 감성어 (한국어)
_NEGATIVE_WORDS = {
    '나쁜', '부족', '문제', '위험', '실패', '어려운', '복잡', '느린',
    '비싸', '제한', '단점', '약점', '우려', '걱정', '불안', '리스크',
    '손실', '감소', '하락', '악화', '취약', '오류', '버그', '장애',
    '불편', '비효율', '부정', '위협', '결함', '지연',
}

# 강조어 (감성 강도 증폭)
_INTENSIFIERS = {
    '매우', '정말', '아주', '극히', '상당히', '엄청', '대단히',
    '굉장히', '절대', '완전', '가장',
}

# 부정어 (감성 반전)
_NEGATORS = {
    '않', '못', '없', '안', '아니', '불',
}


def analyze_sentiment(content: str) -> dict:
    """콘텐츠의 감성을 분석합니다.

    Args:
        content: 분석할 텍스트

    Returns:
        {
            "overall_sentiment": "positive" | "negative" | "neutral",
            "overall_score": float (-1.0 ~ 1.0),
            "distribution": {"positive": float, "negative": float, "neutral": float},
            "paragraph_sentiments": [{"text_preview": str, "sentiment": str, "score": float}],
            "top_positive_words": list[str],
            "top_negative_words": list[str],
            "tone_summary": str,
        }
    """
    if not content or not content.strip():
        return {
            'overall_sentiment': 'neutral',
            'overall_score': 0.0,
            'distribution': {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
            'paragraph_sentiments': [],
            'top_positive_words': [],
            'top_negative_words': [],
            'tone_summary': '분석할 콘텐츠가 없습니다.',
        }

    plain = _strip_markdown(content)
    paragraphs = [p.strip() for p in plain.split('\n\n') if len(p.strip()) >= 10]
    if not paragraphs:
        paragraphs = [plain]

    # 문단별 감성 분석
    para_results = []
    all_pos_words = []
    all_neg_words = []
    scores = []

    for para in paragraphs:
        score, pos_words, neg_words = _score_paragraph(para)
        scores.append(score)
        all_pos_words.extend(pos_words)
        all_neg_words.extend(neg_words)

        sentiment = 'positive' if score > 0.1 else ('negative' if score < -0.1 else 'neutral')
        preview = para[:80] + ('...' if len(para) > 80 else '')

        para_results.append({
            'text_preview': preview,
            'sentiment': sentiment,
            'score': round(score, 3),
        })

    # 전체 점수
    overall_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    overall_score = max(-1.0, min(1.0, overall_score))

    if overall_score > 0.1:
        overall_sentiment = 'positive'
    elif overall_score < -0.1:
        overall_sentiment = 'negative'
    else:
        overall_sentiment = 'neutral'

    # 분포 계산
    pos_count = sum(1 for s in scores if s > 0.1)
    neg_count = sum(1 for s in scores if s < -0.1)
    neu_count = len(scores) - pos_count - neg_count
    total = max(len(scores), 1)

    distribution = {
        'positive': round(pos_count / total, 2),
        'negative': round(neg_count / total, 2),
        'neutral': round(neu_count / total, 2),
    }

    # 상위 키워드 (빈도순, 중복 제거)
    top_pos = _unique_top(all_pos_words, 5)
    top_neg = _unique_top(all_neg_words, 5)

    tone_summary = _generate_tone_summary(overall_sentiment, distribution)

    return {
        'overall_sentiment': overall_sentiment,
        'overall_score': overall_score,
        'distribution': distribution,
        'paragraph_sentiments': para_results[:10],
        'top_positive_words': top_pos,
        'top_negative_words': top_neg,
        'tone_summary': tone_summary,
    }


def _score_paragraph(text: str) -> tuple:
    """문단의 감성 점수와 감성어를 반환합니다."""
    words = re.findall(r'[가-힣]{2,}', text)
    if not words:
        return 0.0, [], []

    pos_found = []
    neg_found = []
    score = 0.0

    for i, word in enumerate(words):
        multiplier = 1.0

        # 강조어 체크 (이전 단어)
        if i > 0 and words[i - 1] in _INTENSIFIERS:
            multiplier = 1.5

        # 부정어 체크 (이전 단어에 부정 접두/접미)
        negated = False
        if i > 0:
            prev = words[i - 1]
            if any(neg in prev for neg in _NEGATORS):
                negated = True

        # 부분 일치: 단어가 감성어를 포함하는지 확인 (예: '훌륭하고' → '훌륭')
        matched_pos = any(pw in word for pw in _POSITIVE_WORDS)
        matched_neg = any(nw in word for nw in _NEGATIVE_WORDS)

        if matched_pos:
            match_word = next(pw for pw in _POSITIVE_WORDS if pw in word)
            if negated:
                score -= 0.1 * multiplier
                neg_found.append(match_word)
            else:
                score += 0.1 * multiplier
                pos_found.append(match_word)
        elif matched_neg:
            match_word = next(nw for nw in _NEGATIVE_WORDS if nw in word)
            if negated:
                score += 0.05 * multiplier
                pos_found.append(match_word)
            else:
                score -= 0.1 * multiplier
                neg_found.append(match_word)

    # 정규화 (단어 수 기준)
    normalized = score / max(len(words), 1) * 10
    return max(-1.0, min(1.0, normalized)), pos_found, neg_found


def _strip_markdown(text: str) -> str:
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _unique_top(words: list, n: int) -> list:
    """빈도순 상위 N개 (중복 제거)."""
    from collections import Counter
    counter = Counter(words)
    return [w for w, _ in counter.most_common(n)]


def _generate_tone_summary(sentiment: str, distribution: dict) -> str:
    summaries = {
        'positive': f"전반적으로 긍정적인 톤입니다 (긍정 {distribution['positive']:.0%}). "
                    f"독자에게 신뢰감을 줄 수 있습니다.",
        'negative': f"부정적 톤이 우세합니다 (부정 {distribution['negative']:.0%}). "
                    f"균형 잡힌 시각을 추가하면 좋겠습니다.",
        'neutral': f"중립적이고 객관적인 톤입니다 (중립 {distribution['neutral']:.0%}). "
                   f"필요에 따라 감성적 요소를 추가해보세요.",
    }
    return summaries.get(sentiment, '톤 분석 완료.')
