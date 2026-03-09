"""cs_asset_pack_service 단위 테스트"""
import unittest

from services.cs_asset_pack_service import (
    build_cs_pack,
    CsAssetPack,
    _strip_markup,
    _split_sentences,
    _extract_faq,
    _is_question_like,
    _is_problem_description,
    _is_step_instruction,
    _contains_actionable_info,
    _sentence_to_question,
    _extract_sentence_topic,
    _extract_troubleshoot,
    _build_quick_reference,
    _build_training_outline,
)


# ── 테스트 데이터 ──

_SUPPORT_TRANSCRIPT = """
안녕하세요, 오늘은 비밀번호 재설정 방법을 안내해드리겠습니다.
비밀번호를 잊어버린 경우 어떻게 해야 하나요?
먼저 로그인 페이지에서 비밀번호 찾기를 클릭하세요.
그 다음 등록된 이메일 주소를 입력하세요.
이메일로 전송된 인증 코드를 확인하세요.
새로운 비밀번호를 8자 이상으로 설정하세요.
비밀번호 변경이 완료됩니다.
문제가 발생하면 고객센터로 문의하세요.
오류가 발생하는 경우 브라우저 캐시를 삭제해 보세요.
그리고 다른 브라우저로 시도해 보세요.
인증 코드가 오지 않으면 스팸 메일함을 확인하세요.
계정이 잠긴 경우 24시간 후에 다시 시도하세요.
추가 질문이 있으시면 FAQ 페이지를 참조하세요.
감사합니다.
"""

_MINIMAL_TRANSCRIPT = "설정을 확인하세요. 문제가 있으면 재시작합니다."


class TestBuildCsPack(unittest.TestCase):
    """build_cs_pack 통합 테스트"""

    def test_empty_transcript(self):
        """빈 자막 → 빈 결과"""
        result = build_cs_pack("")
        self.assertIsInstance(result, CsAssetPack)
        self.assertEqual(result.faq_items, [])
        self.assertEqual(result.video_id, "")

    def test_none_transcript(self):
        """None 입력 → 빈 결과"""
        result = build_cs_pack(None)
        self.assertEqual(result.faq_items, [])

    def test_whitespace_only(self):
        """공백만 있는 자막"""
        result = build_cs_pack("   \n\n  ")
        self.assertEqual(result.faq_items, [])

    def test_faq_minimum_five(self):
        """FAQ 항목이 최소 5개 생성됨"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT, video_id="pw_reset")
        self.assertGreaterEqual(len(result.faq_items), 5)

    def test_faq_structure(self):
        """FAQ 항목 구조 (q, a 키)"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT)
        for item in result.faq_items:
            self.assertIn("q", item)
            self.assertIn("a", item)
            self.assertTrue(len(item["q"]) > 0)
            self.assertTrue(len(item["a"]) > 0)

    def test_video_id_preserved(self):
        """video_id가 결과에 보존됨"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT, video_id="test_vid")
        self.assertEqual(result.video_id, "test_vid")

    def test_video_id_auto_generated(self):
        """video_id 미제공 시 자동 생성"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT)
        self.assertTrue(len(result.video_id) > 0)

    def test_troubleshoot_steps_extracted(self):
        """문제 해결 단계가 추출됨"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT)
        self.assertGreater(len(result.troubleshoot_steps), 0)

    def test_quick_reference_generated(self):
        """퀵 레퍼런스 카드가 생성됨"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT)
        self.assertIn("퀵 레퍼런스 카드", result.quick_reference)
        self.assertGreater(len(result.quick_reference), 10)

    def test_training_outline_generated(self):
        """교육 아웃라인이 생성됨"""
        result = build_cs_pack(_SUPPORT_TRANSCRIPT)
        self.assertGreater(len(result.training_outline), 0)

    def test_minimal_transcript(self):
        """최소 자막에서도 결과 생성"""
        result = build_cs_pack(_MINIMAL_TRANSCRIPT)
        self.assertIsInstance(result, CsAssetPack)


class TestStripMarkup(unittest.TestCase):
    """_strip_markup 테스트"""

    def test_removes_markdown_headers(self):
        self.assertNotIn("#", _strip_markup("## 제목"))

    def test_removes_bold(self):
        self.assertEqual(_strip_markup("**굵은**"), "굵은")

    def test_removes_html_tags(self):
        self.assertEqual(_strip_markup("<b>볼드</b>"), "볼드")

    def test_removes_links(self):
        self.assertNotIn("http", _strip_markup("[링크](http://example.com)"))


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 테스트"""

    def test_splits_by_period(self):
        result = _split_sentences("첫 번째 문장입니다. 두 번째 문장입니다.")
        self.assertEqual(len(result), 2)

    def test_filters_short(self):
        """8자 미만 문장 필터링"""
        result = _split_sentences("짧다. 이것은 충분히 긴 문장입니다.")
        self.assertTrue(all(len(s) >= 8 for s in result))


class TestIsQuestionLike(unittest.TestCase):
    """_is_question_like 테스트"""

    def test_question_mark(self):
        self.assertTrue(_is_question_like("이것은 무엇인가요?"))

    def test_trigger_keyword(self):
        self.assertTrue(_is_question_like("어떻게 설정하는지 알려주세요"))

    def test_non_question(self):
        self.assertFalse(_is_question_like("오늘 날씨가 좋습니다"))


class TestIsProblemDescription(unittest.TestCase):
    """_is_problem_description 테스트"""

    def test_error_keyword(self):
        self.assertTrue(_is_problem_description("오류가 발생합니다"))

    def test_problem_keyword(self):
        self.assertTrue(_is_problem_description("문제가 있는 경우"))

    def test_normal_sentence(self):
        self.assertFalse(_is_problem_description("안녕하세요 반갑습니다"))


class TestIsStepInstruction(unittest.TestCase):
    """_is_step_instruction 테스트"""

    def test_click_keyword(self):
        self.assertTrue(_is_step_instruction("설정 버튼을 클릭하세요"))

    def test_first_keyword(self):
        self.assertTrue(_is_step_instruction("먼저 프로그램을 실행합니다"))

    def test_non_step(self):
        self.assertFalse(_is_step_instruction("감사합니다 좋은 하루 되세요"))


class TestContainsActionableInfo(unittest.TestCase):
    """_contains_actionable_info 테스트"""

    def test_instruction(self):
        self.assertTrue(_contains_actionable_info("설정을 확인하세요"))

    def test_description(self):
        self.assertTrue(_contains_actionable_info("이렇게 됩니다"))


class TestSentenceToQuestion(unittest.TestCase):
    """_sentence_to_question 테스트"""

    def test_instruction_to_question(self):
        q = _sentence_to_question("비밀번호를 변경하세요")
        self.assertIn("?", q)

    def test_statement_to_question(self):
        q = _sentence_to_question("계정이 잠김 상태입니다")
        self.assertIn("?", q)


class TestExtractSentenceTopic(unittest.TestCase):
    """_extract_sentence_topic 테스트"""

    def test_extracts_korean_topic(self):
        topic = _extract_sentence_topic("비밀번호를 변경합니다")
        self.assertTrue(len(topic) >= 2)

    def test_extracts_english_topic(self):
        topic = _extract_sentence_topic("Chrome 브라우저에서 실행")
        self.assertTrue(len(topic) >= 2)


class TestExtractTroubleshoot(unittest.TestCase):
    """_extract_troubleshoot 테스트"""

    def test_groups_problem_and_steps(self):
        sentences = [
            "로그인 오류가 발생하는 경우",
            "먼저 캐시를 삭제하세요",
            "그리고 브라우저를 재시작하세요",
        ]
        groups = _extract_troubleshoot(sentences)
        self.assertGreater(len(groups), 0)
        self.assertIn("steps", groups[0])
        self.assertGreater(len(groups[0]["steps"]), 0)

    def test_no_problems_fallback(self):
        """문제 설명 없으면 일반 절차 그룹으로 폴백"""
        sentences = [
            "먼저 설정을 열어주세요",
            "다음 항목을 선택하세요",
        ]
        groups = _extract_troubleshoot(sentences)
        self.assertGreater(len(groups), 0)
        self.assertEqual(groups[0]["problem"], "일반 절차")


class TestBuildQuickReference(unittest.TestCase):
    """_build_quick_reference 테스트"""

    def test_has_title(self):
        sentences = ["먼저 설정을 클릭하세요", "그리고 저장을 확인합니다"]
        ref = _build_quick_reference(sentences)
        self.assertIn("퀵 레퍼런스 카드", ref)

    def test_limits_items(self):
        """최대 8개 항목"""
        sentences = [f"단계 {i}: 작업을 클릭하세요" for i in range(15)]
        ref = _build_quick_reference(sentences)
        lines = [l for l in ref.split("\n") if l.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))]
        self.assertLessEqual(len(lines), 8)


class TestBuildTrainingOutline(unittest.TestCase):
    """_build_training_outline 테스트"""

    def test_minimum_three_items(self):
        """최소 3개 아웃라인 항목"""
        sentences = ["짧은 문장입니다"]
        outline = _build_training_outline(sentences)
        self.assertGreaterEqual(len(outline), 3)

    def test_detects_section_markers(self):
        """섹션 마커 감지"""
        sentences = [
            "소개 부분을 시작하겠습니다",
            "기본 설정을 확인합니다",
            "고급 기능을 활용합니다",
            "마무리 정리를 하겠습니다",
        ]
        outline = _build_training_outline(sentences)
        self.assertGreater(len(outline), 0)
        # 마커가 포함된 항목이 존재
        joined = " ".join(outline)
        self.assertTrue(any(m in joined for m in ["소개", "기본", "고급", "마무리"]))


if __name__ == '__main__':
    unittest.main()
