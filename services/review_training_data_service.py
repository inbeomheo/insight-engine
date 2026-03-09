"""
리뷰 학습 데이터 서비스 — 사용자 리뷰를 학습 데이터로 변환
"""

import uuid
import json
from dataclasses import dataclass, field


POSITIVE_WORDS = ['좋', '훌륭', '최고', '만족', '추천', '사랑', '완벽', '편리', 'good', 'great', 'love', 'best', 'excellent', 'perfect', 'amazing']
NEGATIVE_WORDS = ['나쁘', '별로', '최악', '불만', '실망', '후회', '불편', 'bad', 'worst', 'terrible', 'awful', 'hate', 'disappointing', 'poor']


@dataclass
class ReviewSample:
    """리뷰 샘플"""
    sample_id: str
    review_text: str
    label: str  # positive / negative / neutral
    confidence: float
    annotator: str


@dataclass
class TrainingDataset:
    """학습 데이터셋"""
    dataset_id: str
    samples: list[ReviewSample]
    label_distribution: dict


def label_review(review_text: str) -> ReviewSample:
    """자동 라벨링 — 감정 키워드 기반"""
    text_lower = review_text.lower()

    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    if pos_count > neg_count:
        label = 'positive'
        confidence = min(1.0, pos_count / max(pos_count + neg_count, 1))
    elif neg_count > pos_count:
        label = 'negative'
        confidence = min(1.0, neg_count / max(pos_count + neg_count, 1))
    else:
        label = 'neutral'
        confidence = 0.5

    return ReviewSample(
        sample_id=str(uuid.uuid4())[:8],
        review_text=review_text,
        label=label,
        confidence=round(confidence, 3),
        annotator='auto'
    )


def create_dataset(reviews: list[str]) -> TrainingDataset:
    """데이터셋 생성"""
    samples = [label_review(r) for r in reviews]
    distribution = _calc_distribution(samples)

    return TrainingDataset(
        dataset_id=str(uuid.uuid4())[:8],
        samples=samples,
        label_distribution=distribution
    )


def balance_dataset(dataset: TrainingDataset) -> TrainingDataset:
    """라벨 균형 — 언더샘플링 (최소 클래스 수에 맞춤)"""
    by_label: dict[str, list[ReviewSample]] = {}
    for s in dataset.samples:
        by_label.setdefault(s.label, []).append(s)

    if not by_label:
        return dataset

    min_count = min(len(v) for v in by_label.values())
    balanced_samples = []
    for label_samples in by_label.values():
        balanced_samples.extend(label_samples[:min_count])

    distribution = _calc_distribution(balanced_samples)
    return TrainingDataset(
        dataset_id=dataset.dataset_id,
        samples=balanced_samples,
        label_distribution=distribution
    )


def export_dataset(dataset: TrainingDataset, format: str = 'jsonl') -> str:
    """JSONL/CSV 내보내기"""
    if format == 'csv':
        lines = ['sample_id,review_text,label,confidence,annotator']
        for s in dataset.samples:
            text = s.review_text.replace('"', '""')
            lines.append(f'{s.sample_id},"{text}",{s.label},{s.confidence},{s.annotator}')
        return '\n'.join(lines)

    # JSONL (기본)
    lines = []
    for s in dataset.samples:
        record = {
            'sample_id': s.sample_id,
            'review_text': s.review_text,
            'label': s.label,
            'confidence': s.confidence,
            'annotator': s.annotator
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    return '\n'.join(lines)


def get_statistics(dataset: TrainingDataset) -> dict:
    """데이터셋 통계"""
    total = len(dataset.samples)
    avg_confidence = round(
        sum(s.confidence for s in dataset.samples) / max(total, 1), 3
    )
    avg_length = round(
        sum(len(s.review_text) for s in dataset.samples) / max(total, 1), 1
    )

    return {
        'total_samples': total,
        'label_distribution': dataset.label_distribution,
        'avg_confidence': avg_confidence,
        'avg_review_length': avg_length,
    }


def _calc_distribution(samples: list[ReviewSample]) -> dict:
    """라벨 분포 계산"""
    dist: dict[str, int] = {}
    for s in samples:
        dist[s.label] = dist.get(s.label, 0) + 1
    return dist
