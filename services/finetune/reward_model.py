"""
RLHF/DPO 보상 모델 (F10-02)
콘텐츠 품질 점수 계산 및 선호도 쌍(preference pair) 수집
실제 RL 학습은 외부 프레임워크(TRL, OpenRLHF)에서 수행
"""
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PreferencePair:
    """선호도 쌍 (chosen vs rejected)"""
    prompt: str          # 입력 프롬프트
    chosen: str          # 선호 응답 (더 좋은 답변)
    rejected: str        # 비선호 응답 (덜 좋은 답변)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dpo_format(self) -> Dict[str, Any]:
        """TRL DPOTrainer 포맷 변환"""
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
        }


class RuleBasedRewardModel:
    """
    규칙 기반 보상 모델 (LLM 없이 동작)
    실제 RLHF 이전 단계: 휴리스틱 품질 점수 계산
    """

    # 금칙어 (품질 저하 신호)
    FORBIDDEN_WORDS = [
        '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
        '압도적', '경이로운', '드디어', '탁월한', '인상적',
        '뛰어난', '강력한',
    ]

    # 품질 지표별 가중치
    WEIGHTS = {
        'length_score': 0.15,        # 적절한 길이
        'structure_score': 0.20,     # 구조화 (헤딩, 목록)
        'forbidden_penalty': 0.25,   # 금칙어 패널티
        'korean_ratio': 0.10,        # 한국어 비율
        'no_hallucination': 0.15,    # 환각 신호 부재
        'readability': 0.15,         # 가독성 (문장 길이)
    }

    def score(self, content: str, style_id: str = 'blog_seo') -> Dict[str, float]:
        """
        콘텐츠 품질 점수 계산 (0.0 ~ 1.0)

        Returns:
            {'total': 0.0~1.0, 'length_score': ..., ...}
        """
        if not content or not content.strip():
            return {'total': 0.0, **{k: 0.0 for k in self.WEIGHTS}}

        scores = {}

        # 1. 길이 점수 (스타일별 적정 길이)
        target_lengths = {
            'blog_seo': (1000, 3000), 'summary': (300, 1000),
            'tutorial': (800, 2500), 'qna': (500, 2000),
            'sns_post': (100, 500), 'newsletter': (800, 2000),
        }
        lo, hi = target_lengths.get(style_id, (500, 2000))
        length = len(content)
        if lo <= length <= hi:
            scores['length_score'] = 1.0
        elif length < lo:
            scores['length_score'] = max(0.0, length / lo)
        else:
            scores['length_score'] = max(0.0, 1.0 - (length - hi) / hi)

        # 2. 구조화 점수 (헤딩, 목록, 문단 수)
        headings = content.count('\n#')
        bullet_lines = sum(1 for l in content.split('\n') if l.strip().startswith(('-', '*', '•')))
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        structure_indicators = headings + bullet_lines // 3 + paragraphs // 2
        scores['structure_score'] = min(1.0, structure_indicators / 10)

        # 3. 금칙어 패널티
        forbidden_count = sum(w in content for w in self.FORBIDDEN_WORDS)
        scores['forbidden_penalty'] = max(0.0, 1.0 - forbidden_count * 0.2)

        # 4. 한국어 비율
        import unicodedata
        korean_chars = sum(1 for c in content if '\uAC00' <= c <= '\uD7A3')
        total_alpha = sum(1 for c in content if c.isalpha())
        scores['korean_ratio'] = korean_chars / max(1, total_alpha)

        # 5. 환각 신호 부재 (창작/추측 표현)
        hallucination_patterns = ['~인 것 같습니다', '아마도', '추측컨대', '아마', '~일 수도']
        hallucination_count = sum(p in content for p in hallucination_patterns)
        scores['no_hallucination'] = max(0.0, 1.0 - hallucination_count * 0.15)

        # 6. 가독성 (평균 문장 길이 50~150자가 최적)
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        if sentences:
            avg_len = sum(len(s) for s in sentences) / len(sentences)
            if 50 <= avg_len <= 150:
                scores['readability'] = 1.0
            else:
                scores['readability'] = max(0.0, 1.0 - abs(avg_len - 100) / 200)
        else:
            scores['readability'] = 0.5

        # 총점 계산
        total = sum(scores[k] * w for k, w in self.WEIGHTS.items())
        scores['total'] = round(total, 3)

        return scores

    def compare(self, content_a: str, content_b: str, style_id: str = 'blog_seo') -> str:
        """두 콘텐츠 비교 후 더 나은 쪽 반환 ('a' or 'b' or 'tie')"""
        score_a = self.score(content_a, style_id)['total']
        score_b = self.score(content_b, style_id)['total']
        diff = abs(score_a - score_b)
        if diff < 0.05:
            return 'tie'
        return 'a' if score_a > score_b else 'b'


class PreferenceCollector:
    """선호도 쌍 수집 및 저장"""

    def __init__(self, storage_path: str = './data/preferences.jsonl'):
        self.storage_path = storage_path
        self.reward_model = RuleBasedRewardModel()
        os.makedirs(os.path.dirname(storage_path) if os.path.dirname(storage_path) else '.', exist_ok=True)

    def collect_from_ab_test(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
        style_id: str = 'blog_seo',
        human_preference: Optional[str] = None,
    ) -> Optional[PreferencePair]:
        """
        A/B 테스트 결과로 선호도 쌍 생성

        Args:
            human_preference: 'a', 'b', None (None이면 자동 판정)
        """
        if human_preference:
            winner = human_preference
        else:
            winner = self.reward_model.compare(response_a, response_b, style_id)

        if winner == 'tie':
            return None

        chosen = response_a if winner == 'a' else response_b
        rejected = response_b if winner == 'a' else response_a

        pair = PreferencePair(
            prompt=prompt,
            chosen=chosen,
            rejected=rejected,
            metadata={
                'style_id': style_id,
                'winner': winner,
                'source': 'human' if human_preference else 'auto',
                'score_a': self.reward_model.score(response_a, style_id)['total'],
                'score_b': self.reward_model.score(response_b, style_id)['total'],
                'created_at': time.time(),
            }
        )

        self._save_pair(pair)
        return pair

    def _save_pair(self, pair: PreferencePair) -> None:
        with open(self.storage_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(pair), ensure_ascii=False) + '\n')

    def load_pairs(self) -> List[PreferencePair]:
        """저장된 선호도 쌍 로드"""
        if not os.path.exists(self.storage_path):
            return []
        pairs = []
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    pairs.append(PreferencePair(**data))
                except Exception:
                    continue
        return pairs

    def export_dpo_dataset(self, output_path: str) -> int:
        """DPO 학습용 JSONL 내보내기"""
        pairs = self.load_pairs()
        with open(output_path, 'w', encoding='utf-8') as f:
            for pair in pairs:
                f.write(json.dumps(pair.to_dpo_format(), ensure_ascii=False) + '\n')
        logger.info("DPO 데이터셋 내보내기: %d쌍 → %s", len(pairs), output_path)
        return len(pairs)
