"""voice_draft_service 단위 테스트"""
import unittest

from services.voice_draft_service import (
    refine_voice_draft,
    extract_key_points,
    RefinedDraft,
    _extract_title,
    _split_into_paragraphs,
    _calculate_refinement_score,
)


class TestExtractTitle(unittest.TestCase):
    """제목 추출 테스트"""

    def test_first_sentence_as_title(self):
        """첫 문장에서 제목 추출"""
        result = _extract_title("오늘의 주제는 AI입니다. 자세히 알아봅시다.")
        self.assertEqual(result, "오늘의 주제는 AI입니다")

    def test_removes_markdown_hash(self):
        """마크다운 # 기호 제거"""
        result = _extract_title("## 프로젝트 개요. 상세 내용입니다.")
        self.assertEqual(result, "프로젝트 개요")

    def test_removes_markdown_bold(self):
        """마크다운 **bold** 기호 제거"""
        result = _extract_title("**중요한** 내용입니다. 다음은...")
        self.assertNotIn("**", result)
        self.assertIn("중요한", result)

    def test_truncates_long_title(self):
        """50자 초과 시 잘라내기"""
        long_text = "가" * 60 + ". 두 번째."
        result = _extract_title(long_text)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 54)  # 50 + '...'

    def test_empty_input(self):
        result = _extract_title("")
        self.assertEqual(result, "")

    def test_removes_trailing_punctuation(self):
        """끝 구두점 제거"""
        result = _extract_title("제목입니다!")
        self.assertEqual(result, "제목입니다")


class TestSplitIntoParagraphs(unittest.TestCase):
    """문단 분리 테스트"""

    def test_five_sentences_one_paragraph(self):
        """5문장 → 1문단"""
        text = "문장1. 문장2. 문장3. 문장4. 문장5."
        result = _split_into_paragraphs(text)
        self.assertEqual(len(result), 1)

    def test_ten_sentences_two_paragraphs(self):
        """10문장 → 2문단"""
        sentences = ' '.join([f"문장{i}." for i in range(10)])
        result = _split_into_paragraphs(sentences)
        self.assertEqual(len(result), 2)

    def test_six_sentences_two_paragraphs(self):
        """6문장 → 2문단 (5+1)"""
        sentences = ' '.join([f"문장{i}." for i in range(6)])
        result = _split_into_paragraphs(sentences)
        self.assertEqual(len(result), 2)

    def test_empty_input(self):
        result = _split_into_paragraphs("")
        self.assertEqual(result, [])


class TestCalculateRefinementScore(unittest.TestCase):
    """정제 점수 계산 테스트"""

    def test_no_fillers_returns_100(self):
        """필러 없으면 100"""
        score = _calculate_refinement_score("좋은 아침입니다", "좋은 아침입니다")
        self.assertEqual(score, 100)

    def test_fillers_removed_high_score(self):
        """필러 제거되면 높은 점수"""
        original = "음 그 어 좋은 아침입니다"
        refined = "좋은 아침입니다"
        score = _calculate_refinement_score(original, refined)
        self.assertGreater(score, 50)

    def test_empty_original_returns_0(self):
        score = _calculate_refinement_score("", "")
        self.assertEqual(score, 0)

    def test_score_range_0_to_100(self):
        """점수가 0~100 범위"""
        score = _calculate_refinement_score("음 음 음 테스트", "테스트")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestRefineVoiceDraft(unittest.TestCase):
    """refine_voice_draft 함수 테스트"""

    def test_empty_input(self):
        """빈 입력 → 빈 RefinedDraft"""
        result = refine_voice_draft("")
        self.assertEqual(result.title, "")
        self.assertEqual(result.body, "")
        self.assertEqual(result.paragraphs, [])
        self.assertEqual(result.word_count, 0)

    def test_none_input(self):
        result = refine_voice_draft(None)
        self.assertEqual(result.body, "")

    def test_normal_speech(self):
        """일반 음성 텍스트 정제"""
        result = refine_voice_draft("오늘 프로젝트의 주요 목표를 설명하겠습니다. 첫째는 성능 개선입니다.")
        self.assertIn("프로젝트", result.body)
        self.assertTrue(result.title)
        self.assertGreater(result.word_count, 0)
        self.assertGreater(len(result.paragraphs), 0)

    def test_filler_speech(self):
        """필러 포함 음성 정제"""
        result = refine_voice_draft("음 이제 뭐랄까 오늘의 주제는 AI 기술입니다")
        self.assertIn("AI", result.body)
        self.assertGreater(result.refinement_score, 0)

    def test_title_extracted(self):
        """제목이 추출되는지 확인"""
        result = refine_voice_draft("프로젝트 개요 설명입니다. 자세한 내용은 다음과 같습니다.")
        self.assertTrue(result.title)

    def test_paragraphs_created(self):
        """문단이 생성되는지 확인"""
        # 7문장 → 2문단 기대
        text = '. '.join([f"문장 {i}번 내용입니다" for i in range(7)]) + '.'
        result = refine_voice_draft(text)
        self.assertGreaterEqual(len(result.paragraphs), 1)

    def test_refinement_score_set(self):
        """정제 점수가 설정되는지"""
        result = refine_voice_draft("음 그 프로젝트를 시작합니다.")
        self.assertIsInstance(result.refinement_score, int)
        self.assertGreaterEqual(result.refinement_score, 0)
        self.assertLessEqual(result.refinement_score, 100)


class TestExtractKeyPoints(unittest.TestCase):
    """핵심 포인트 추출 테스트"""

    def test_empty_draft(self):
        """빈 드래프트 → 빈 리스트"""
        draft = RefinedDraft()
        result = extract_key_points(draft)
        self.assertEqual(result, [])

    def test_extracts_important_keyword(self):
        """'중요한' 키워드 매칭"""
        draft = RefinedDraft(body="이것은 중요한 발견입니다. 일반적인 내용입니다.")
        result = extract_key_points(draft)
        self.assertEqual(len(result), 1)
        self.assertIn("중요한", result[0])

    def test_extracts_conclusion_keyword(self):
        """'결론' 키워드 매칭"""
        draft = RefinedDraft(body="서론입니다. 결론은 다음과 같습니다.")
        result = extract_key_points(draft)
        self.assertEqual(len(result), 1)
        self.assertIn("결론", result[0])

    def test_extracts_multiple_keywords(self):
        """여러 키워드 매칭"""
        draft = RefinedDraft(body="핵심 내용입니다. 반드시 기억하세요. 일반 내용.")
        result = extract_key_points(draft)
        self.assertGreaterEqual(len(result), 2)

    def test_no_keywords_returns_empty(self):
        """키워드 없으면 빈 리스트"""
        draft = RefinedDraft(body="오늘 날씨가 좋습니다. 산책을 했습니다.")
        result = extract_key_points(draft)
        self.assertEqual(result, [])

    def test_especially_keyword(self):
        """'특히' 키워드 매칭"""
        draft = RefinedDraft(body="특히 이 부분이 인상적입니다.")
        result = extract_key_points(draft)
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
