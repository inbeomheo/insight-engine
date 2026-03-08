"""
콘텐츠 시뮬레이터 서비스 (F10-17)
콘텐츠 발행 전 성과 시뮬레이션 (예측 CTR, 조회수, 공유수)
"""
import logging
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """시뮬레이션 예측 결과"""
    predicted_views_30d: int         # 30일 예상 조회수
    predicted_clicks_30d: int        # 30일 예상 클릭수
    predicted_shares: int            # 예상 공유수
    predicted_ctr: float             # 예상 CTR (%)
    engagement_score: float          # 참여도 점수 (0~100)
    seo_potential: float             # SEO 잠재력 (0~100)
    confidence_interval: float       # 예측 신뢰 구간 (±%)
    bottlenecks: list                # 개선 필요 항목
    recommendations: list            # 성과 향상 추천

    def to_dict(self) -> Dict[str, Any]:
        """시뮬레이션 결과를 딕셔너리로 변환"""
        return {
            'predicted_views_30d': self.predicted_views_30d,
            'predicted_clicks_30d': self.predicted_clicks_30d,
            'predicted_shares': self.predicted_shares,
            'predicted_ctr': round(self.predicted_ctr, 1),
            'engagement_score': round(self.engagement_score, 1),
            'seo_potential': round(self.seo_potential, 1),
            'confidence_interval': round(self.confidence_interval, 1),
            'bottlenecks': self.bottlenecks,
            'recommendations': self.recommendations,
        }


class SimulatorService:
    """
    콘텐츠 성과 시뮬레이터

    규칙 기반 예측 모델 (실제 데이터 없이도 동작)
    ML 모델과 결합 시 정확도 대폭 향상
    """

    # 스타일별 기본 조회수 배율
    STYLE_VIEW_MULTIPLIER = {
        'blog_seo': 1.5,
        'naver_popular': 2.0,
        'tutorial': 1.3,
        'qna': 1.2,
        'sns_post': 3.0,
        'newsletter': 0.8,
        'summary': 1.0,
        'brunch_essay': 0.9,
        'geo_seo': 1.8,
    }

    # 플랫폼 기준 조회수 (30일)
    PLATFORM_BASE_VIEWS = {
        'naver_blog': 500,
        'tistory': 300,
        'medium': 200,
        'substack': 150,
        'brunch': 250,
        'default': 200,
    }

    def simulate(
        self,
        content: str,
        style_id: str = 'blog_seo',
        platform: str = 'default',
        follower_count: int = 1000,
        has_seo_keywords: bool = True,
        has_images: bool = False,
        title_length: int = 50,
        seed: Optional[int] = None,
    ) -> SimulationResult:
        """
        콘텐츠 성과 시뮬레이션

        Args:
            content: 콘텐츠 텍스트
            style_id: 콘텐츠 스타일
            platform: 발행 플랫폼
            follower_count: 팔로워/구독자 수
            has_seo_keywords: SEO 키워드 포함 여부
            has_images: 이미지 포함 여부
            title_length: 제목 길이 (자)
            seed: 랜덤 시드 (재현성)
        """
        if seed is not None:
            random.seed(seed)

        base_views = self.PLATFORM_BASE_VIEWS.get(platform, 200)
        style_mult = self.STYLE_VIEW_MULTIPLIER.get(style_id, 1.0)

        # 콘텐츠 품질 분석
        content_len = len(content)
        word_count = len(content.split())
        heading_count = content.count('\n#')
        has_structure = heading_count >= 2

        # 팔로워 기여
        follower_boost = math.log10(max(10, follower_count)) * 50

        # 콘텐츠 품질 점수 (0~1)
        quality = 0.0
        if 800 <= content_len <= 3000:
            quality += 0.3
        elif content_len > 300:
            quality += 0.15
        if has_structure:
            quality += 0.2
        if has_seo_keywords:
            quality += 0.25
        if has_images:
            quality += 0.15
        if 30 <= title_length <= 60:
            quality += 0.1

        # 예상 조회수
        predicted_views = int(
            (base_views + follower_boost) *
            style_mult *
            (0.5 + quality * 1.5) *
            (1 + random.uniform(-0.2, 0.3))  # ±25% 변동
        )

        # 예상 CTR (%)
        base_ctr = {'naver_popular': 3.5, 'blog_seo': 2.5, 'geo_seo': 4.0}.get(style_id, 2.0)
        predicted_ctr = base_ctr * (0.8 + quality * 0.5)
        if 30 <= title_length <= 50:
            predicted_ctr *= 1.2

        predicted_clicks = int(predicted_views * predicted_ctr / 100)

        # 예상 공유수 (SNS 바이럴 계수)
        share_rate = {'sns_post': 0.05, 'naver_popular': 0.03, 'tutorial': 0.02}.get(style_id, 0.01)
        predicted_shares = int(predicted_clicks * share_rate)

        # 참여도 점수
        engagement = min(100, quality * 60 + style_mult * 15 + (predicted_ctr / 5) * 25)

        # SEO 잠재력
        seo_potential = min(100, (
            (30 if has_seo_keywords else 0) +
            (20 if has_structure else 0) +
            (25 if 800 <= content_len <= 3000 else 10) +
            (style_mult - 1) * 15 +
            15
        ))

        # 신뢰 구간
        confidence_interval = max(15, 40 - quality * 30)

        # 병목 및 개선 제안
        bottlenecks = []
        recommendations = []

        if not has_seo_keywords:
            bottlenecks.append("SEO 키워드 없음")
            recommendations.append("핵심 키워드를 제목과 소제목에 자연스럽게 포함하세요")
        if not has_structure:
            bottlenecks.append("콘텐츠 구조 부족")
            recommendations.append("H2/H3 소제목으로 콘텐츠를 명확하게 구분하세요")
        if not has_images:
            bottlenecks.append("이미지 없음")
            recommendations.append("관련 이미지나 인포그래픽을 추가하면 체류 시간이 향상됩니다")
        if title_length < 30 or title_length > 60:
            bottlenecks.append(f"제목 길이 비최적 ({title_length}자)")
            recommendations.append("제목은 30~60자가 최적입니다")
        if content_len < 800:
            bottlenecks.append("콘텐츠 너무 짧음")
            recommendations.append("800자 이상으로 확장하면 SEO와 신뢰도가 향상됩니다")

        return SimulationResult(
            predicted_views_30d=predicted_views,
            predicted_clicks_30d=predicted_clicks,
            predicted_shares=predicted_shares,
            predicted_ctr=predicted_ctr,
            engagement_score=engagement,
            seo_potential=seo_potential,
            confidence_interval=confidence_interval,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )
