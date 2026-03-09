"""리뷰 학습 데이터 서비스 테스트"""
import unittest
from services.review_training_data_service import (
    label_review, create_dataset, balance_dataset, export_dataset,
    get_statistics, ReviewSample, TrainingDataset
)


class TestReviewTrainingDataService(unittest.TestCase):

    def setUp(self):
        self.reviews = [
            '정말 좋은 제품입니다. 최고!',
            '별로에요. 실망했습니다.',
            '그냥 보통이에요.',
            '훌륭한 서비스, 추천합니다!',
            '최악의 경험. 후회.',
            '사랑하는 제품입니다!',
        ]

    def test_label_review_positive(self):
        sample = label_review('정말 좋은 제품 최고!')
        self.assertIsInstance(sample, ReviewSample)
        self.assertEqual(sample.label, 'positive')
        self.assertEqual(sample.annotator, 'auto')

    def test_label_review_negative(self):
        sample = label_review('최악 별로 실망')
        self.assertEqual(sample.label, 'negative')

    def test_label_review_neutral(self):
        sample = label_review('오늘 배송이 왔습니다')
        self.assertEqual(sample.label, 'neutral')

    def test_label_review_confidence_range(self):
        sample = label_review('좋아요 추천!')
        self.assertGreaterEqual(sample.confidence, 0.0)
        self.assertLessEqual(sample.confidence, 1.0)

    def test_create_dataset(self):
        dataset = create_dataset(self.reviews)
        self.assertIsInstance(dataset, TrainingDataset)
        self.assertEqual(len(dataset.samples), 6)
        self.assertIn('positive', dataset.label_distribution)

    def test_balance_dataset(self):
        dataset = create_dataset(self.reviews)
        balanced = balance_dataset(dataset)
        counts = list(balanced.label_distribution.values())
        if len(counts) > 1:
            self.assertEqual(len(set(counts)), 1)  # 모든 라벨 동일 수

    def test_balance_dataset_empty(self):
        dataset = TrainingDataset('d1', [], {})
        balanced = balance_dataset(dataset)
        self.assertEqual(len(balanced.samples), 0)

    def test_export_dataset_jsonl(self):
        dataset = create_dataset(['좋아요', '별로에요'])
        output = export_dataset(dataset, 'jsonl')
        lines = output.strip().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertIn('review_text', lines[0])

    def test_export_dataset_csv(self):
        dataset = create_dataset(['좋아요', '나빠요'])
        output = export_dataset(dataset, 'csv')
        lines = output.strip().split('\n')
        self.assertEqual(lines[0], 'sample_id,review_text,label,confidence,annotator')

    def test_get_statistics(self):
        dataset = create_dataset(self.reviews)
        stats = get_statistics(dataset)
        self.assertEqual(stats['total_samples'], 6)
        self.assertGreater(stats['avg_review_length'], 0)

    def test_label_review_english(self):
        sample = label_review('This product is great and amazing!')
        self.assertEqual(sample.label, 'positive')


if __name__ == '__main__':
    unittest.main()
