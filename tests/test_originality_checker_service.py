"""독창성·출처 중복 검사 서비스 테스트"""
import unittest

from services.quality.originality_checker_service import check_originality


class TestOriginalityCheckerService(unittest.TestCase):
    """check_originality 함수의 동작을 검증한다."""

    # --- 1. 빈 콘텐츠 ---
    def test_empty_content(self):
        """빈 문자열 입력 시 F등급과 점수 0을 반환해야 한다."""
        result = check_originality("")
        self.assertEqual(result["originality_score"], 0.0)
        self.assertEqual(result["grade"], "F")
        self.assertIsNone(result["overlap_analysis"]["external_overlap"])
        self.assertEqual(result["flagged_sentences"], [])
        self.assertEqual(result["common_phrases"], [])
        self.assertIsInstance(result["suggestions"], list)

    # --- 2. None 콘텐츠 ---
    def test_none_content(self):
        """None 입력 시에도 안전하게 F등급을 반환해야 한다."""
        result = check_originality(None)
        self.assertEqual(result["originality_score"], 0.0)
        self.assertEqual(result["grade"], "F")

    # --- 3. 기본 분석 ---
    def test_basic_originality(self):
        """정상 콘텐츠에 대해 필수 키를 모두 포함하는 결과를 반환해야 한다."""
        content = (
            "인공지능은 현대 기술의 핵심 분야입니다. "
            "머신러닝 알고리즘은 데이터에서 패턴을 학습합니다. "
            "딥러닝은 신경망을 활용한 기법입니다. "
            "자연어 처리는 텍스트를 이해하는 기술입니다."
        )
        result = check_originality(content)

        # 필수 키 존재 확인
        self.assertIn("originality_score", result)
        self.assertIn("grade", result)
        self.assertIn("overlap_analysis", result)
        self.assertIn("flagged_sentences", result)
        self.assertIn("common_phrases", result)
        self.assertIn("suggestions", result)

        # overlap_analysis 하위 키 확인
        analysis = result["overlap_analysis"]
        self.assertIn("self_repetition", analysis)
        self.assertIn("external_overlap", analysis)
        self.assertIn("unique_ratio", analysis)

    # --- 4. 점수 범위 ---
    def test_score_range(self):
        """독창성 점수는 0에서 100 사이여야 한다."""
        content = "파이썬은 프로그래밍 언어입니다. 자바스크립트도 프로그래밍 언어입니다."
        result = check_originality(content)
        self.assertGreaterEqual(result["originality_score"], 0.0)
        self.assertLessEqual(result["originality_score"], 100.0)

    # --- 5. 등급 매핑 ---
    def test_grade_mapping(self):
        """독창적인 콘텐츠는 높은 등급, 반복 콘텐츠는 낮은 등급이어야 한다."""
        # 독창적인 콘텐츠 → 높은 등급
        unique_content = (
            "블록체인 기술은 분산 원장을 기반으로 합니다. "
            "양자 컴퓨팅은 큐비트를 활용하여 병렬 연산을 수행합니다. "
            "사물인터넷은 기기 간 네트워크 연결을 가능하게 합니다. "
            "증강 현실은 디지털 정보를 현실 세계에 오버레이합니다. "
            "엣지 컴퓨팅은 데이터를 현장에서 처리하여 지연 시간을 줄입니다."
        )
        result_unique = check_originality(unique_content)
        self.assertIn(result_unique["grade"], ["A", "B"])

        # 반복 콘텐츠 → 낮은 등급
        repeated = "이것은 동일한 문장을 반복하는 콘텐츠입니다. " * 10
        result_repeated = check_originality(repeated)
        self.assertIn(result_repeated["grade"], ["C", "D", "F"])

    # --- 6. 높은 독창성 ---
    def test_high_originality(self):
        """모든 문장이 서로 다른 콘텐츠는 높은 독창성 점수를 받아야 한다."""
        content = (
            "서울의 봄은 벚꽃이 만개하는 아름다운 계절입니다. "
            "부산 해운대 해변은 여름 관광 명소로 유명합니다. "
            "제주도의 한라산은 사계절 등산객이 찾는 명산입니다. "
            "경주의 불국사는 유네스코 세계문화유산으로 지정되었습니다. "
            "강릉의 커피 거리는 바리스타 문화를 이끌고 있습니다."
        )
        result = check_originality(content)
        self.assertGreaterEqual(result["originality_score"], 70.0)
        self.assertEqual(result["overlap_analysis"]["self_repetition"], 0.0)

    # --- 7. 내부 반복 감지 ---
    def test_self_repetition(self):
        """동일하거나 유사한 문장이 반복되면 반복률이 높아야 한다."""
        content = (
            "인공지능 기술이 빠르게 발전하고 있습니다. "
            "인공지능 기술이 매우 빠르게 발전하고 있습니다. "
            "블록체인은 보안에 강한 기술입니다. "
            "인공지능 기술은 빠르게 발전하고 있습니다."
        )
        result = check_originality(content)
        self.assertGreater(result["overlap_analysis"]["self_repetition"], 0.0)

        # 반복 문장이 flagged에 포함되어야 함
        self_repeat_flags = [
            f for f in result["flagged_sentences"] if f["issue"] == "self_repeat"
        ]
        self.assertGreater(len(self_repeat_flags), 0)

    # --- 8. 외부 중복 감지 ---
    def test_external_overlap(self):
        """reference 콘텐츠와 유사한 문장이 있으면 외부 중복으로 감지해야 한다."""
        content = (
            "파이썬은 데이터 분석에 널리 사용되는 프로그래밍 언어입니다. "
            "웹 개발에는 자바스크립트가 필수적입니다."
        )
        references = [
            {
                "id": "ref1",
                "title": "프로그래밍 입문",
                "content": "파이썬은 데이터 분석에 널리 사용되는 프로그래밍 언어입니다. "
                "초보자도 쉽게 배울 수 있습니다.",
            }
        ]
        result = check_originality(content, reference_contents=references)

        self.assertIsNotNone(result["overlap_analysis"]["external_overlap"])
        self.assertGreater(result["overlap_analysis"]["external_overlap"], 0.0)

        ext_flags = [
            f for f in result["flagged_sentences"] if f["issue"] == "external_overlap"
        ]
        self.assertGreater(len(ext_flags), 0)
        # matched_with에 출처 제목이 포함되어야 함
        self.assertIn("프로그래밍 입문", ext_flags[0]["matched_with"])

    # --- 9. reference 없을 때 ---
    def test_no_reference(self):
        """reference_contents가 없으면 external_overlap은 None이어야 한다."""
        content = "클라우드 컴퓨팅은 IT 인프라를 혁신하고 있습니다."
        result = check_originality(content)
        self.assertIsNone(result["overlap_analysis"]["external_overlap"])

    # --- 10. 클리셰 감지 ---
    def test_common_phrases(self):
        """클리셰 표현이 포함되면 common_phrases에 감지되어야 한다."""
        content = (
            "오늘날 빠르게 변화하는 기술 환경에서 적응이 중요합니다. "
            "많은 사람들이 이에 공감하고 있습니다. "
            "결론적으로 말하자면 미래를 준비해야 합니다. "
            "이것은 과언이 아니다라고 할 수 있습니다."
        )
        result = check_originality(content)

        self.assertGreater(len(result["common_phrases"]), 0)
        self.assertIn("오늘날 빠르게 변화하는", result["common_phrases"])
        self.assertIn("많은 사람들이", result["common_phrases"])

        # 클리셰가 flagged_sentences에도 포함되어야 함
        cliche_flags = [
            f for f in result["flagged_sentences"] if f["issue"] == "common_phrase"
        ]
        self.assertGreater(len(cliche_flags), 0)

    # --- 11. 고유 문장 비율 ---
    def test_unique_ratio(self):
        """고유 문장 비율은 반복이 없으면 100에 가깝고, 반복이 많으면 낮아야 한다."""
        # 모두 고유
        unique_content = (
            "태양계에는 여덟 개의 행성이 있습니다. "
            "달은 지구의 유일한 자연 위성입니다. "
            "화성에는 올림포스 산이 있습니다."
        )
        result_unique = check_originality(unique_content)
        self.assertEqual(result_unique["overlap_analysis"]["unique_ratio"], 100.0)

        # 반복 포함
        repeated_content = (
            "기술은 발전하고 있습니다. "
            "기술은 계속 발전하고 있습니다. "
            "완전히 다른 주제의 문장입니다."
        )
        result_repeated = check_originality(repeated_content)
        self.assertLess(result_repeated["overlap_analysis"]["unique_ratio"], 100.0)

    # --- 12. 플래그된 문장 구조 ---
    def test_flagged_sentences(self):
        """플래그된 문장은 sentence, issue, similarity, matched_with 키를 포함해야 한다."""
        content = (
            "데이터 과학은 통계와 프로그래밍의 융합 분야입니다. "
            "데이터 과학은 통계와 프로그래밍을 융합한 학문입니다. "
            "아시다시피 이 분야는 성장하고 있습니다."
        )
        result = check_originality(content)

        # 플래그된 문장이 존재해야 함
        self.assertGreater(len(result["flagged_sentences"]), 0)

        for flagged in result["flagged_sentences"]:
            self.assertIn("sentence", flagged)
            self.assertIn("issue", flagged)
            self.assertIn("similarity", flagged)
            self.assertIn("matched_with", flagged)
            # issue 타입 검증
            self.assertIn(
                flagged["issue"],
                ["self_repeat", "external_overlap", "common_phrase"],
            )
            # similarity 범위 검증
            self.assertGreaterEqual(flagged["similarity"], 0.0)
            self.assertLessEqual(flagged["similarity"], 1.0)

    # --- 13. 제안 목록 ---
    def test_suggestions(self):
        """suggestions는 비어있지 않은 문자열 목록이어야 한다."""
        content = "이것은 테스트 콘텐츠입니다. 분석 결과를 확인합니다."
        result = check_originality(content)

        self.assertIsInstance(result["suggestions"], list)
        self.assertGreater(len(result["suggestions"]), 0)
        for s in result["suggestions"]:
            self.assertIsInstance(s, str)
            self.assertGreater(len(s), 0)


if __name__ == "__main__":
    unittest.main()
