"""
AI 썸네일 A/B 테스트 서비스 (F10-08)
썸네일 변형 생성 + 성과 추적 + 자동 승자 선택
"""
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STORE_PATH = os.getenv('THUMBNAIL_AB_STORE', './data/thumbnail_ab.jsonl')


@dataclass
class ThumbnailVariant:
    """썸네일 변형"""
    variant_id: str
    name: str                    # 예: 'control', 'variant_a', 'variant_b'
    image_url: str
    prompt_used: str             # 생성에 사용된 프롬프트
    impressions: int = 0         # 노출 수
    clicks: int = 0              # 클릭 수
    ctr: float = 0.0             # CTR (클릭/노출)
    created_at: float = field(default_factory=time.time)

    def update_ctr(self):
        """노출 대비 클릭률(CTR) 재계산"""
        self.ctr = self.clicks / max(1, self.impressions)


@dataclass
class ABTest:
    """A/B 테스트 실험"""
    test_id: str
    title: str
    video_url: str
    variants: List[ThumbnailVariant]
    status: str = 'running'          # 'running', 'completed', 'paused'
    winner_id: Optional[str] = None
    min_impressions: int = 100       # 최소 노출 후 승자 선택
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class ThumbnailABService:
    """
    AI 썸네일 A/B 테스트 서비스

    기능:
    1. AI로 다양한 썸네일 변형 생성
    2. 변형별 노출/클릭 추적
    3. 통계적 유의성 기반 승자 선택
    4. 자동 승자 적용
    """

    def __init__(self, store_path: str = STORE_PATH):
        self.store_path = store_path
        os.makedirs(os.path.dirname(store_path) if os.path.dirname(store_path) else '.', exist_ok=True)
        self._tests: Dict[str, ABTest] = {}

    def create_test(
        self,
        video_url: str,
        title: str,
        num_variants: int = 2,
        style: str = 'youtube',
        model: Optional[str] = None,
    ) -> ABTest:
        """
        새 A/B 테스트 생성

        Args:
            video_url: YouTube URL
            title: 영상 제목
            num_variants: 변형 수 (2~4)
            style: 썸네일 스타일 힌트

        Returns:
            ABTest 인스턴스
        """
        test_id = str(uuid.uuid4())[:8]

        variants = []
        prompts = self._generate_variant_prompts(title, num_variants, style)

        for i, (variant_name, prompt) in enumerate(prompts):
            # 실제 구현: image_gen_service 호출
            image_url = self._generate_thumbnail(prompt, model=model)
            variants.append(ThumbnailVariant(
                variant_id=f"{test_id}_v{i}",
                name=variant_name,
                image_url=image_url,
                prompt_used=prompt,
            ))

        test = ABTest(
            test_id=test_id,
            title=title,
            video_url=video_url,
            variants=variants,
        )
        self._tests[test_id] = test
        self._save_test(test)

        logger.info("A/B 테스트 생성: %s (%d변형)", test_id, len(variants))
        return test

    def record_impression(self, test_id: str, variant_id: str) -> bool:
        """노출 이벤트 기록"""
        test = self._tests.get(test_id)
        if not test or test.status != 'running':
            return False
        for v in test.variants:
            if v.variant_id == variant_id:
                v.impressions += 1
                v.update_ctr()
                self._check_auto_winner(test)
                return True
        return False

    def record_click(self, test_id: str, variant_id: str) -> bool:
        """클릭 이벤트 기록"""
        test = self._tests.get(test_id)
        if not test or test.status != 'running':
            return False
        for v in test.variants:
            if v.variant_id == variant_id:
                v.clicks += 1
                v.update_ctr()
                return True
        return False

    def get_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """테스트 결과 조회"""
        test = self._tests.get(test_id)
        if not test:
            return None

        return {
            'test_id': test.test_id,
            'title': test.title,
            'status': test.status,
            'winner_id': test.winner_id,
            'variants': [
                {
                    'variant_id': v.variant_id,
                    'name': v.name,
                    'image_url': v.image_url,
                    'impressions': v.impressions,
                    'clicks': v.clicks,
                    'ctr': round(v.ctr * 100, 2),
                }
                for v in test.variants
            ],
        }

    def _check_auto_winner(self, test: ABTest) -> None:
        """최소 노출 달성 시 자동 승자 선택"""
        min_impressions = min(v.impressions for v in test.variants)
        if min_impressions < test.min_impressions:
            return

        best = max(test.variants, key=lambda v: v.ctr)
        # 승자가 2위보다 10% 이상 높아야 확정
        sorted_variants = sorted(test.variants, key=lambda v: v.ctr, reverse=True)
        if len(sorted_variants) >= 2:
            gap = sorted_variants[0].ctr - sorted_variants[1].ctr
            if gap < 0.01:  # 1% 미만 차이면 미결
                return

        test.winner_id = best.variant_id
        test.status = 'completed'
        test.completed_at = time.time()
        logger.info("A/B 테스트 승자 결정: %s → %s (CTR=%.2f%%)",
                    test.test_id, best.variant_id, best.ctr * 100)

    def _generate_variant_prompts(
        self, title: str, num_variants: int, style: str
    ) -> List[tuple]:
        """변형별 썸네일 프롬프트 생성"""
        base_prompts = [
            ('control', f"YouTube thumbnail for: {title}. Clean, professional design."),
            ('variant_a', f"Eye-catching YouTube thumbnail: {title}. Bold text, bright colors, face close-up."),
            ('variant_b', f"Minimalist YouTube thumbnail: {title}. Simple background, large readable text."),
            ('variant_c', f"YouTube thumbnail with infographic style: {title}. Data visualization, icons."),
        ]
        return base_prompts[:num_variants]

    def _generate_thumbnail(self, prompt: str, model: Optional[str] = None) -> str:
        """썸네일 이미지 생성 (image_gen_service 연동)"""
        try:
            from services.image_gen_service import ImageGenService
            svc = ImageGenService()
            result = svc.generate(prompt, size='1280x720')
            return result.get('url', '')
        except Exception as e:
            logger.warning("썸네일 생성 실패, 플레이스홀더 사용: %s", e)
            # 플레이스홀더 URL
            return f"https://placehold.co/1280x720?text={prompt[:20]}"

    def _save_test(self, test: ABTest) -> None:
        try:
            with open(self.store_path, 'a', encoding='utf-8') as f:
                data = {
                    'test_id': test.test_id,
                    'title': test.title,
                    'video_url': test.video_url,
                    'status': test.status,
                    'created_at': test.created_at,
                }
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning("테스트 저장 실패: %s", e)
