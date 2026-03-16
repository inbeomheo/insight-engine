"""
자동 태깅 서비스

TF-IDF 기반 키워드 추출 및 카테고리 분류.
외부 AI 호출 없이 로컬에서 처리합니다.
"""
import math
import re
from collections import Counter
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# 한국어 불용어 (조사, 접미사, 일반적인 단어)
_STOPWORDS_KO = frozenset([
    '이', '그', '저', '것', '수', '등', '때', '중', '더', '또', '및',
    '를', '을', '에', '의', '가', '는', '은', '로', '으로', '와', '과',
    '에서', '까지', '부터', '도', '만', '보다', '처럼', '같이',
    '있다', '없다', '하다', '되다', '않다', '이다',
    '있는', '없는', '하는', '되는', '않는', '이런', '저런', '그런',
    '합니다', '합니다', '입니다', '됩니다', '습니다',
    '그리고', '하지만', '그러나', '때문에', '위해', '대해', '통해',
    '아주', '매우', '정말', '너무', '굉장히', '상당히',
])

_STOPWORDS_EN = frozenset([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'must',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
    'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
    'this', 'that', 'these', 'those', 'and', 'but', 'or', 'nor',
    'for', 'in', 'on', 'at', 'to', 'from', 'by', 'with', 'of',
    'not', 'no', 'so', 'if', 'then', 'than', 'too', 'very',
    'just', 'about', 'also', 'some', 'any', 'all', 'each',
])

STOPWORDS = _STOPWORDS_KO | _STOPWORDS_EN

# 카테고리 키워드 매핑
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    '기술': [
        'api', 'sdk', 'python', 'javascript', 'react', 'ai', '인공지능', '머신러닝',
        '딥러닝', '프로그래밍', '코딩', '개발', '서버', '클라우드', '데이터',
        '알고리즘', '프레임워크', '라이브러리', 'github', 'docker', 'kubernetes',
        'llm', 'gpt', '모델', '학습', 'gpu', 'cpu', '소프트웨어', '하드웨어',
    ],
    '비즈니스': [
        '마케팅', '매출', '수익', '투자', '스타트업', '사업', '전략', '브랜드',
        '고객', '시장', '성장', '경영', '매니지먼트', 'roi', '비용', '광고',
        'b2b', 'b2c', '세일즈', '영업', '펀딩', 'vc', 'kpi',
    ],
    '라이프스타일': [
        '여행', '음식', '건강', '운동', '다이어트', '요리', '패션', '뷰티',
        '인테리어', '취미', '반려동물', '카페', '레시피', '피트니스',
    ],
    '교육': [
        '학습', '강의', '수업', '교육', '학교', '대학', '시험', '자격증',
        '공부', '입시', '과외', '튜토리얼', '커리큘럼', '온라인강의',
    ],
    '엔터테인먼트': [
        '영화', '드라마', '음악', '게임', '예능', '웹툰', '만화', '애니메이션',
        '콘서트', '공연', '넷플릭스', '유튜브', '스트리밍', '팟캐스트',
    ],
    '뉴스/시사': [
        '정치', '경제', '사회', '국제', '북한', '선거', '정부', '국회',
        '법률', '규제', '정책', '외교', '안보',
    ],
    '과학': [
        '물리', '화학', '생물', '천문', '우주', '양자', '유전', '세포',
        '나노', '실험', '연구', '논문', '학회',
    ],
}


def _tokenize(text: str) -> List[str]:
    """텍스트를 토큰으로 분리합니다.

    한국어: 2글자 이상 연속 한글을 단어로 추출
    영어: 소문자 변환 후 알파벳 2글자 이상 추출
    """
    # 한글 단어 추출 (2글자 이상)
    ko_tokens = re.findall(r'[가-힣]{2,}', text)
    # 영어 단어 추출 (2글자 이상)
    en_tokens = [w.lower() for w in re.findall(r'[a-zA-Z]{2,}', text)]

    all_tokens = ko_tokens + en_tokens
    return [t for t in all_tokens if t not in STOPWORDS and len(t) >= 2]


def _compute_tfidf(tokens: List[str], top_n: int = 10) -> List[str]:
    """단순 TF-IDF로 상위 키워드를 추출합니다.

    단일 문서이므로 IDF는 단어 빈도의 역수 기반 가중치를 사용합니다.
    """
    if not tokens:
        return []

    tf = Counter(tokens)
    total = len(tokens)
    unique = len(tf)

    if unique == 0:
        return []

    # 단일 문서 IDF 근사: 빈도가 낮은 단어에 가중치 부여
    scores = {}
    for word, count in tf.items():
        tf_val = count / total
        # IDF 근사: log(전체 고유 단어 수 / 해당 단어 빈도)
        idf_val = math.log(unique / count + 1)
        scores[word] = tf_val * idf_val

    sorted_words = sorted(scores, key=scores.get, reverse=True)
    return sorted_words[:top_n]


def _classify_category(tags: List[str], text_lower: str) -> str:
    """태그와 원문을 기반으로 카테고리를 분류합니다."""
    category_scores: Dict[str, int] = {}
    tags_lower = [t.lower() for t in tags]

    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # 태그에 포함되면 가중치 2
            if kw_lower in tags_lower:
                score += 2
            # 원문에 포함되면 가중치 1
            if kw_lower in text_lower:
                score += 1
        if score > 0:
            category_scores[category] = score

    if not category_scores:
        return '일반'

    return max(category_scores, key=category_scores.get)


def generate_tags(content: str, max_tags: int = 10) -> Dict:
    """콘텐츠에서 태그와 카테고리를 추출합니다.

    Args:
        content: 분석할 텍스트
        max_tags: 최대 태그 수 (5~10)

    Returns:
        {"tags": ["태그1", "태그2", ...], "category": "기술"}
    """
    if not content or not content.strip():
        return {"tags": [], "category": "일반"}

    try:
        max_tags = max(5, min(max_tags, 10))

        tokens = _tokenize(content)
        tags = _compute_tfidf(tokens, top_n=max_tags)
        text_lower = content.lower()
        category = _classify_category(tags, text_lower)

        return {"tags": tags, "category": category}
    except Exception as e:
        logger.error("generate_tags 실패: %s", e, exc_info=True)
        return {}
