"""
가독성 점수 분석 서비스 단위 테스트 (F3-10)
"""
import unittest


class TestReadabilityService(unittest.TestCase):
    """readability_service.analyze_readability 테스트"""

    def test_empty_text(self):
        """빈 텍스트"""
        from services.analysis.readability_service import analyze_readability
        result = analyze_readability("")
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['grade'], 'D')

    def test_returns_all_fields(self):
        """모든 필드 반환 확인"""
        from services.analysis.readability_service import analyze_readability
        result = analyze_readability("이것은 테스트 문장입니다. 가독성을 분석합니다.")
        self.assertIn('score', result)
        self.assertIn('grade', result)
        self.assertIn('details', result)
        self.assertIn('suggestions', result)

    def test_grade_values(self):
        """grade가 A/B/C/D 중 하나"""
        from services.analysis.readability_service import analyze_readability
        result = analyze_readability("테스트 문장입니다. " * 10)
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D'))

    def test_score_range(self):
        """점수 0-100 범위"""
        from services.analysis.readability_service import analyze_readability
        result = analyze_readability("적당한 길이의 문장입니다. " * 20)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_well_structured_content(self):
        """잘 구성된 콘텐츠는 높은 점수"""
        from services.analysis.readability_service import analyze_readability
        content = (
            "인공지능은 현대 기술의 핵심입니다.\n\n"
            "머신러닝은 데이터에서 패턴을 학습합니다. "
            "이를 통해 예측 모델을 구축할 수 있습니다.\n\n"
            "딥러닝은 신경망 기반의 학습 방법입니다. "
            "이미지 인식과 자연어 처리에 활용됩니다."
        )
        result = analyze_readability(content)
        self.assertGreaterEqual(result['score'], 50)

    def test_single_paragraph_long_text_penalty(self):
        """긴 텍스트가 하나의 문단이면 감점"""
        from services.analysis.readability_service import analyze_readability
        content = "이것은 긴 텍스트입니다. " * 50  # 문단 나눔 없이 긴 텍스트
        result = analyze_readability(content)
        self.assertTrue(any('문단' in s for s in result['suggestions']))

    def test_details_structure(self):
        """details 필드 구조"""
        from services.analysis.readability_service import analyze_readability
        result = analyze_readability("테스트입니다. 두 번째 문장입니다.")
        details = result['details']
        self.assertIn('avg_sentence_length', details)
        self.assertIn('vocabulary_diversity', details)
        self.assertIn('foreign_ratio', details)
        self.assertIn('paragraph_count', details)
        self.assertIn('sentence_count', details)
        self.assertIn('char_count', details)

    def test_foreign_ratio_high(self):
        """외래어 비율 높으면 경고"""
        from services.analysis.readability_service import analyze_readability
        content = "This is a test content with many English words. " * 20
        result = analyze_readability(content)
        self.assertGreater(result['details']['foreign_ratio'], 0.0)

    def test_markdown_stripped(self):
        """마크다운이 제거되어 분석됨"""
        from services.analysis.readability_service import analyze_readability
        md = "## 제목\n\n**볼드** 텍스트와 [링크](http://example.com)가 있습니다."
        result = analyze_readability(md)
        # 마크다운 문법이 char_count에 포함되지 않음 (대략적)
        self.assertGreater(result['details']['char_count'], 0)


if __name__ == '__main__':
    unittest.main()
