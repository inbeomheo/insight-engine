"""리뷰 매트릭스 서비스 — 리뷰 데이터에서 제품별 비교표 생성

리뷰 데이터([{"product": ..., "text": ..., "rating": ...}])를 분석하여
제품 간 기준별 점수 비교표(ComparisonTable)를 생성합니다.
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List

logger = logging.getLogger(__name__)

# 기본 비교 기준 (AI가 리뷰에서 추출 못했을 때 폴백)
_DEFAULT_CRITERIA = ["품질", "가격", "디자인", "내구성", "사용성"]


@dataclass
class ComparisonTable:
    """제품 비교표"""
    products: List[str]
    criteria: List[str]
    ratings: Dict[str, Dict[str, float]]  # {product: {criterion: score}}
    winner: str
    summary: str


def create_comparison_matrix(reviews: List[dict]) -> ComparisonTable:
    """리뷰 데이터에서 제품별 비교표 생성

    Args:
        reviews: [{"product": "...", "text": "...", "rating": 4.5}]
                 product, text는 필수. rating은 선택(없으면 0.0).

    Returns:
        ComparisonTable 인스턴스

    Raises:
        ValueError: 리뷰가 없거나 제품이 없을 때
    """
    if not reviews:
        raise ValueError("리뷰 데이터가 비어있습니다")

    # 유효한 리뷰만 필터링 (product, text 필수)
    valid_reviews = [
        r for r in reviews
        if isinstance(r, dict)
        and r.get('product', '').strip()
        and r.get('text', '').strip()
    ]
    if not valid_reviews:
        raise ValueError("유효한 리뷰가 없습니다 (product, text 필수)")

    # 제품별 리뷰 그룹핑
    product_reviews = _group_by_product(valid_reviews)
    products = sorted(product_reviews.keys())

    if len(products) < 1:
        raise ValueError("비교할 제품이 없습니다")

    # 기준별 점수 계산
    criteria = _extract_criteria(valid_reviews)
    ratings = _compute_ratings(product_reviews, criteria)

    # 우승 제품 결정
    winner = _determine_winner(ratings, products)

    # 요약 생성
    summary = _generate_summary(products, criteria, ratings, winner)

    return ComparisonTable(
        products=products,
        criteria=criteria,
        ratings=ratings,
        winner=winner,
        summary=summary,
    )


def _group_by_product(reviews: List[dict]) -> Dict[str, List[dict]]:
    """제품별로 리뷰를 그룹핑합니다."""
    groups: Dict[str, List[dict]] = {}
    for r in reviews:
        product = r['product'].strip()
        if product not in groups:
            groups[product] = []
        groups[product].append(r)
    return groups


def _extract_criteria(reviews: List[dict]) -> List[str]:
    """리뷰에서 비교 기준을 추출합니다.

    간단한 키워드 매칭으로 리뷰 텍스트에서 언급된 기준을 찾고,
    없으면 기본 기준을 사용합니다.
    """
    # 확장된 기준 키워드 맵핑
    criteria_keywords = {
        "품질": ["품질", "퀄리티", "quality", "완성도", "마감"],
        "가격": ["가격", "비용", "가성비", "price", "저렴", "비싸"],
        "디자인": ["디자인", "외관", "모양", "design", "스타일", "예쁘"],
        "내구성": ["내구성", "튼튼", "오래", "견고", "durability", "고장"],
        "사용성": ["사용", "편리", "편의", "쉽", "인터페이스", "usability"],
        "성능": ["성능", "속도", "빠르", "performance", "파워"],
        "서비스": ["서비스", "A/S", "고객", "지원", "응대", "배송"],
    }

    all_text = ' '.join(r.get('text', '') for r in reviews).lower()
    found = []
    for criterion, keywords in criteria_keywords.items():
        for kw in keywords:
            if kw.lower() in all_text:
                found.append(criterion)
                break

    # 최소 3개 기준 보장
    if len(found) < 3:
        for c in _DEFAULT_CRITERIA:
            if c not in found:
                found.append(c)
            if len(found) >= 5:
                break

    return found[:7]  # 최대 7개


def _compute_ratings(
    product_reviews: Dict[str, List[dict]],
    criteria: List[str]
) -> Dict[str, Dict[str, float]]:
    """제품별 기준별 점수를 계산합니다.

    리뷰 텍스트의 감성 + 평점을 조합하여 0.0~5.0 점수 생성.
    """
    # 기준별 긍정/부정 키워드
    positive_words = ["좋", "훌륭", "최고", "만족", "추천", "완벽", "뛰어나",
                      "편리", "빠르", "우수", "great", "good", "excellent"]
    negative_words = ["나쁘", "별로", "불만", "실망", "고장", "느리", "불편",
                      "부족", "약하", "bad", "poor", "terrible"]

    ratings: Dict[str, Dict[str, float]] = {}

    for product, reviews in product_reviews.items():
        ratings[product] = {}

        # 기본 평점 (없으면 3.0)
        avg_rating = _avg_rating(reviews)

        all_text = ' '.join(r.get('text', '') for r in reviews).lower()

        for criterion in criteria:
            # 기본 점수: 평점 기반
            base_score = avg_rating

            # 감성 보정: 긍정 키워드 → +0.2, 부정 키워드 → -0.2
            pos_count = sum(1 for w in positive_words if w in all_text)
            neg_count = sum(1 for w in negative_words if w in all_text)
            sentiment_adj = (pos_count - neg_count) * 0.1

            score = base_score + sentiment_adj
            # 0.0 ~ 5.0 범위 클램핑
            score = max(0.0, min(5.0, round(score, 1)))
            ratings[product][criterion] = score

    return ratings


def _avg_rating(reviews: List[dict]) -> float:
    """리뷰들의 평균 평점을 계산합니다."""
    valid_ratings = []
    for r in reviews:
        try:
            rating = float(r.get('rating', 0))
            if 0 < rating <= 5:
                valid_ratings.append(rating)
        except (TypeError, ValueError):
            continue

    if not valid_ratings:
        return 3.0  # 기본값
    return sum(valid_ratings) / len(valid_ratings)


def _determine_winner(
    ratings: Dict[str, Dict[str, float]],
    products: List[str]
) -> str:
    """전체 평균 점수가 가장 높은 제품을 우승자로 결정합니다."""
    if not products:
        return ""

    best_product = products[0]
    best_avg = 0.0

    for product in products:
        scores = ratings.get(product, {})
        if scores:
            avg = sum(scores.values()) / len(scores)
        else:
            avg = 0.0
        if avg > best_avg:
            best_avg = avg
            best_product = product

    return best_product


def _generate_summary(
    products: List[str],
    criteria: List[str],
    ratings: Dict[str, Dict[str, float]],
    winner: str
) -> str:
    """비교 결과 요약문을 생성합니다."""
    if len(products) == 1:
        product = products[0]
        scores = ratings.get(product, {})
        if scores:
            avg = round(sum(scores.values()) / len(scores), 1)
            return f"{product}의 평균 점수는 {avg}/5.0입니다."
        return f"{product}에 대한 리뷰가 분석되었습니다."

    # 각 제품의 평균 점수
    avgs = {}
    for p in products:
        scores = ratings.get(p, {})
        avgs[p] = round(sum(scores.values()) / len(scores), 1) if scores else 0.0

    product_scores = ', '.join(f"{p}({avgs[p]})" for p in products)
    return f"{len(products)}개 제품 비교 결과: {product_scores}. 종합 우승: {winner}"


def comparison_table_to_dict(table: ComparisonTable) -> dict:
    """ComparisonTable을 직렬화 가능한 dict로 변환합니다."""
    return asdict(table)
