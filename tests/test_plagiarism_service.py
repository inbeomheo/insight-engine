"""
표절/중복 감지 서비스 단위 테스트 (F3-09)
"""
import unittest


class TestPlagiarismService(unittest.TestCase):
    """plagiarism_service.check_plagiarism 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠"""
        from services.quality.plagiarism_service import check_plagiarism
        result = check_plagiarism("")
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['verdict'], 'clean')

    def test_unique_content(self):
        """고유한 콘텐츠는 clean"""
        from services.quality.plagiarism_service import check_plagiarism
        content = (
            "인공지능은 현대 기술의 핵심입니다. "
            "머신러닝은 데이터에서 패턴을 학습합니다. "
            "딥러닝은 신경망 기반 학습 방법론입니다. "
            "자연어 처리는 텍스트를 이해하는 기술입니다."
        )
        result = check_plagiarism(content)
        self.assertEqual(result['verdict'], 'clean')

    def test_repeated_content_detected(self):
        """반복 콘텐츠 감지"""
        from services.quality.plagiarism_service import check_plagiarism
        # 같은 문장 반복
        sentence = "이것은 반복되는 테스트 문장입니다 예시로 작성된 것입니다"
        content = (sentence + ". ") * 10
        result = check_plagiarism(content)
        self.assertGreater(result['score'], 0)
        self.assertGreater(len(result['repeated_phrases']), 0)

    def test_verdict_values(self):
        """verdict가 유효한 값"""
        from services.quality.plagiarism_service import check_plagiarism
        result = check_plagiarism("테스트 콘텐츠입니다. 다른 내용도 있습니다.")
        self.assertIn(result['verdict'], ('clean', 'minor', 'significant'))

    def test_score_range(self):
        """점수 0-100 범위"""
        from services.quality.plagiarism_service import check_plagiarism
        result = check_plagiarism("정상적인 텍스트입니다. 각 문장은 서로 다릅니다.")
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_duplicate_ratio_float(self):
        """duplicate_ratio가 float"""
        from services.quality.plagiarism_service import check_plagiarism
        result = check_plagiarism("테스트입니다. 다른 문장입니다.")
        self.assertIsInstance(result['duplicate_ratio'], float)

    def test_similar_sentences_structure(self):
        """similar_sentences 구조 검증"""
        from services.quality.plagiarism_service import check_plagiarism
        # 유사한 문장 쌍 생성
        content = (
            "인공지능 기술이 발전하고 있습니다. "
            "자연어 처리가 중요합니다. "
            "인공지능 기술이 크게 발전하고 있습니다. "
            "데이터 분석이 필요합니다."
        )
        result = check_plagiarism(content)
        for pair in result['similar_sentences']:
            self.assertIn('sentence_a', pair)
            self.assertIn('sentence_b', pair)
            self.assertIn('similarity', pair)


class TestJaccardSimilarity(unittest.TestCase):
    """_jaccard_similarity 테스트"""

    def test_identical_texts(self):
        from services.quality.plagiarism_service import _jaccard_similarity
        self.assertEqual(_jaccard_similarity("hello world", "hello world"), 1.0)

    def test_completely_different(self):
        from services.quality.plagiarism_service import _jaccard_similarity
        sim = _jaccard_similarity("hello world", "foo bar")
        self.assertEqual(sim, 0.0)

    def test_partial_overlap(self):
        from services.quality.plagiarism_service import _jaccard_similarity
        sim = _jaccard_similarity("hello world foo", "hello world bar")
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_empty_text(self):
        from services.quality.plagiarism_service import _jaccard_similarity
        self.assertEqual(_jaccard_similarity("", "hello"), 0.0)


if __name__ == '__main__':
    unittest.main()
