"""수술 전 준비(프리헵) 키트 서비스 테스트"""
import unittest

from services.medical_prehab_service import (
    PrehabKit, PrehabStep, TimelineItem,
    generate_prehab_kit, list_procedure_types,
    _extract_relevant_content, _MEDICAL_DISCLAIMER, _PROCEDURE_DATA,
)


class TestListProcedureTypes(unittest.TestCase):
    """list_procedure_types 함수 테스트"""

    def test_returns_list(self):
        """리스트 타입 반환 확인"""
        result = list_procedure_types()
        self.assertIsInstance(result, list)

    def test_contains_all_types(self):
        """5가지 시술 유형이 모두 포함되는지 확인"""
        result = list_procedure_types()
        expected = ["general", "dental", "orthopedic", "cardiac", "cosmetic"]
        for t in expected:
            self.assertIn(t, result)

    def test_count(self):
        """정확히 5개 시술 유형"""
        result = list_procedure_types()
        self.assertEqual(len(result), 5)


class TestGeneratePrehabKit(unittest.TestCase):
    """generate_prehab_kit 함수 테스트"""

    def test_general_kit(self):
        """일반 수술 키트 생성"""
        kit = generate_prehab_kit("수술 준비에 대한 내용", "general")

        self.assertIsInstance(kit, PrehabKit)
        self.assertEqual(kit.procedure_type, "general")
        self.assertGreater(len(kit.preparation_steps), 0)
        self.assertGreater(len(kit.timeline), 0)
        self.assertGreater(len(kit.checklist), 0)
        self.assertGreater(len(kit.faq), 0)

    def test_dental_kit(self):
        """치과 시술 키트 생성"""
        kit = generate_prehab_kit("임플란트 시술 준비", "dental")

        self.assertEqual(kit.procedure_type, "dental")
        self.assertGreater(len(kit.preparation_steps), 0)

    def test_orthopedic_kit(self):
        """정형외과 키트 생성"""
        kit = generate_prehab_kit("무릎 수술 준비", "orthopedic")

        self.assertEqual(kit.procedure_type, "orthopedic")
        self.assertGreater(len(kit.preparation_steps), 0)

    def test_cardiac_kit(self):
        """심장 시술 키트 생성"""
        kit = generate_prehab_kit("심장 스텐트 시술", "cardiac")

        self.assertEqual(kit.procedure_type, "cardiac")
        self.assertGreater(len(kit.preparation_steps), 0)

    def test_cosmetic_kit(self):
        """미용 시술 키트 생성"""
        kit = generate_prehab_kit("보톡스 시술 준비", "cosmetic")

        self.assertEqual(kit.procedure_type, "cosmetic")
        self.assertGreater(len(kit.preparation_steps), 0)

    def test_unknown_type_falls_back_to_general(self):
        """알 수 없는 시술 유형은 general로 폴백"""
        kit = generate_prehab_kit("내용", "unknown_type")

        self.assertEqual(kit.procedure_type, "general")

    def test_default_type_is_general(self):
        """기본값이 general인지 확인"""
        kit = generate_prehab_kit("내용")

        self.assertEqual(kit.procedure_type, "general")

    def test_medical_disclaimer_always_included(self):
        """의료 면책조항이 반드시 포함되는지 확인"""
        for ptype in list_procedure_types():
            kit = generate_prehab_kit("테스트", ptype)
            self.assertIn(_MEDICAL_DISCLAIMER, kit.warnings,
                          f"{ptype} 키트에 면책조항 누락")

    def test_empty_content(self):
        """빈 콘텐츠로도 에러 없이 키트 생성"""
        kit = generate_prehab_kit("")

        self.assertIsInstance(kit, PrehabKit)
        self.assertIn(_MEDICAL_DISCLAIMER, kit.warnings)

    def test_faq_has_minimum_three(self):
        """각 시술 유형에 최소 3개 FAQ가 있는지 확인"""
        for ptype in list_procedure_types():
            kit = generate_prehab_kit("내용", ptype)
            self.assertGreaterEqual(len(kit.faq), 3,
                                    f"{ptype} FAQ가 3개 미만")

    def test_faq_has_q_and_a_keys(self):
        """FAQ 항목에 q, a 키가 있는지 확인"""
        kit = generate_prehab_kit("내용", "general")

        for item in kit.faq:
            self.assertIn("q", item)
            self.assertIn("a", item)
            self.assertIsInstance(item["q"], str)
            self.assertIsInstance(item["a"], str)


class TestExtractRelevantContent(unittest.TestCase):
    """콘텐츠 기반 추가 주의사항 추출 테스트"""

    def test_allergy_warning(self):
        """알레르기 키워드 감지"""
        warnings = _extract_relevant_content("알레르기가 있는 분은 주의하세요.", "general")
        self.assertTrue(any("알레르기" in w for w in warnings))

    def test_diabetes_warning(self):
        """당뇨 키워드 감지"""
        warnings = _extract_relevant_content("당뇨 환자는 혈당 관리를 해야 합니다.", "general")
        self.assertTrue(any("당뇨" in w for w in warnings))

    def test_hypertension_warning(self):
        """고혈압 키워드 감지"""
        warnings = _extract_relevant_content("고혈압 약을 복용 중입니다.", "general")
        self.assertTrue(any("고혈압" in w or "혈압" in w for w in warnings))

    def test_pregnancy_warning(self):
        """임신/수유 키워드 감지"""
        warnings = _extract_relevant_content("임신 중인 경우 시술이 제한됩니다.", "cosmetic")
        self.assertTrue(any("임신" in w for w in warnings))

    def test_no_keywords(self):
        """관련 키워드 없으면 빈 리스트"""
        warnings = _extract_relevant_content("오늘 날씨가 좋습니다.", "general")
        self.assertEqual(len(warnings), 0)

    def test_multiple_warnings(self):
        """여러 키워드 동시 감지"""
        text = "당뇨와 고혈압이 있고 알레르기도 있습니다."
        warnings = _extract_relevant_content(text, "general")
        self.assertGreaterEqual(len(warnings), 3)


class TestPrehabKitDataStructure(unittest.TestCase):
    """데이터 구조 검증 테스트"""

    def test_preparation_steps_are_prehab_step(self):
        """preparation_steps가 PrehabStep 인스턴스인지 확인"""
        kit = generate_prehab_kit("내용", "general")

        for step in kit.preparation_steps:
            self.assertIsInstance(step, PrehabStep)
            self.assertIsInstance(step.step_number, int)
            self.assertIsInstance(step.category, str)
            self.assertIsInstance(step.instruction, str)
            self.assertIsInstance(step.timing, str)

    def test_timeline_items_are_timeline_item(self):
        """timeline이 TimelineItem 인스턴스인지 확인"""
        kit = generate_prehab_kit("내용", "general")

        for item in kit.timeline:
            self.assertIsInstance(item, TimelineItem)
            self.assertIsInstance(item.days_before, int)
            self.assertIsInstance(item.action, str)
            self.assertIsInstance(item.category, str)

    def test_checklist_items_are_strings(self):
        """체크리스트 항목이 문자열인지 확인"""
        kit = generate_prehab_kit("내용", "general")

        for item in kit.checklist:
            self.assertIsInstance(item, str)
            self.assertGreater(len(item), 0)

    def test_step_numbers_sequential(self):
        """준비 단계 번호가 순차적인지 확인"""
        for ptype in list_procedure_types():
            kit = generate_prehab_kit("내용", ptype)
            for i, step in enumerate(kit.preparation_steps):
                self.assertEqual(step.step_number, i + 1,
                                 f"{ptype}: 단계 번호 불일치")

    def test_timeline_days_non_negative(self):
        """타임라인 days_before가 0 이상인지 확인"""
        for ptype in list_procedure_types():
            kit = generate_prehab_kit("내용", ptype)
            for item in kit.timeline:
                self.assertGreaterEqual(item.days_before, 0,
                                        f"{ptype}: days_before가 음수")


class TestProcedureDataIntegrity(unittest.TestCase):
    """시술 유형별 데이터 무결성 테스트"""

    def test_all_types_have_required_keys(self):
        """모든 시술 유형에 필수 키가 있는지 확인"""
        required_keys = {"label", "steps", "timeline", "checklist", "faq"}
        for ptype, data in _PROCEDURE_DATA.items():
            for key in required_keys:
                self.assertIn(key, data, f"{ptype}에 '{key}' 키 누락")

    def test_all_types_have_label(self):
        """모든 시술 유형에 한국어 라벨이 있는지 확인"""
        for ptype, data in _PROCEDURE_DATA.items():
            self.assertIsInstance(data["label"], str)
            self.assertGreater(len(data["label"]), 0)


if __name__ == '__main__':
    unittest.main()
