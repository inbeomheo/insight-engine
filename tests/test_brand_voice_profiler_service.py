"""브랜드 보이스 프로파일러 서비스 테스트.

profile_brand_voice 함수의 다양한 입력 시나리오를 검증합니다.
"""

import unittest

from services.content.brand_voice_profiler_service import profile_brand_voice


class TestBrandVoiceProfilerService(unittest.TestCase):
    """브랜드 보이스 프로파일러 서비스 단위 테스트."""

    # --- 기본 구조 검증 헬퍼 ---

    def _assert_valid_structure(self, result: dict):
        """반환값의 기본 구조를 검증합니다."""
        self.assertIn("voice_profile", result)
        self.assertIn("metrics", result)
        self.assertIn("characteristics", result)
        self.assertIn("dominant_patterns", result)
        self.assertIn("suggestions", result)

        vp = result["voice_profile"]
        self.assertIn(vp["formality"], ("formal", "neutral", "casual"))
        self.assertIn(vp["tone"], (
            "professional", "friendly", "authoritative",
            "conversational", "educational", "neutral",
        ))
        self.assertIn(vp["energy"], ("high", "medium", "low"))

        m = result["metrics"]
        for key in (
            "formality_score", "vocabulary_complexity",
            "sentence_complexity", "emotional_intensity", "consistency_score",
        ):
            self.assertIn(key, m)
            self.assertGreaterEqual(m[key], 0.0)
            self.assertLessEqual(m[key], 100.0)

    # --- 1. 빈 콘텐츠 ---

    def test_empty_content(self):
        """빈 문자열 입력 시 기본 프로파일을 반환해야 합니다."""
        result = profile_brand_voice("")
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["formality"], "neutral")
        self.assertEqual(result["voice_profile"]["tone"], "neutral")
        self.assertEqual(result["voice_profile"]["energy"], "low")
        self.assertEqual(result["characteristics"], [])
        self.assertEqual(result["dominant_patterns"], [])
        self.assertIn("분석할 콘텐츠가 충분하지 않습니다.", result["suggestions"])

    # --- 2. None 입력 ---

    def test_none_content(self):
        """None 입력 시 에러 없이 기본 프로파일을 반환해야 합니다."""
        result = profile_brand_voice(None)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["formality"], "neutral")
        self.assertEqual(result["characteristics"], [])

    # --- 3. 격식체 콘텐츠 ---

    def test_formal_voice(self):
        """격식체 어미(~습니다, ~합니다)가 주된 콘텐츠는 formal로 분류되어야 합니다."""
        content = (
            "본 보고서는 2024년 상반기 매출 현황을 분석합니다. "
            "전년 대비 15% 증가한 것으로 나타났습니다. "
            "주요 원인은 신제품 출시에 있습니다. "
            "향후 전략 수립이 필요합니다. "
            "추가 분석은 다음 분기에 진행됩니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["formality"], "formal")
        self.assertGreaterEqual(result["metrics"]["formality_score"], 70.0)

    # --- 4. 비격식체 콘텐츠 ---

    def test_casual_voice(self):
        """비격식체 어미(~해요, ~죠)가 주된 콘텐츠는 casual로 분류되어야 합니다."""
        content = (
            "이거 진짜 좋아요! "
            "저도 써봤는데 완전 괜찮죠. "
            "가격도 합리적이거든요. "
            "다들 한번 써보면 알잖아요. "
            "후기가 좋은 이유가 있네요."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["formality"], "casual")
        self.assertLess(result["metrics"]["formality_score"], 40.0)

    # --- 5. 전문적 톤 ---

    def test_professional_tone(self):
        """격식체 + 낮은 감정 강도의 콘텐츠는 professional 톤이어야 합니다."""
        content = (
            "제3분기 실적 보고서를 제출합니다. "
            "영업이익은 전년 동기 대비 12% 증가하였습니다. "
            "원가 절감 효과가 반영되었습니다. "
            "신규 사업 부문의 매출 기여도가 확대되었습니다. "
            "세부 내역은 별첨 자료를 참고하시기 바랍니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["tone"], "professional")

    # --- 6. 대화형 톤 ---

    def test_conversational_tone(self):
        """비격식체 + 높은 감정 강도의 콘텐츠는 conversational 톤이어야 합니다."""
        content = (
            "와 이거 진짜 대박이야! 너무 좋아! "
            "정말 놀랍게도 완전 달라졌어! "
            "엄청 기대되지 않아? 매우 신나! "
            "ㅋㅋㅋ 완전 웃겨! 너무 재밌어! "
            "정말 최고야! 굉장히 만족해!"
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["tone"], "conversational")

    # --- 7. 높은 에너지 ---

    def test_high_energy(self):
        """감탄사와 느낌표가 많은 콘텐츠는 high energy여야 합니다."""
        content = (
            "정말 놀라운 소식입니다! 매우 기대됩니다! "
            "너무 좋은 결과입니다! 엄청난 성과입니다! "
            "굉장히 인상적입니다! 놀랍게도 성공했습니다! "
            "정말 대단합니다! 매우 뛰어난 실적입니다! "
            "너무 감사합니다! 엄청 기쁩니다!"
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["energy"], "high")
        self.assertGreaterEqual(result["metrics"]["emotional_intensity"], 60.0)

    # --- 8. 낮은 에너지 ---

    def test_low_energy(self):
        """담담한 서술의 콘텐츠는 low energy여야 합니다."""
        content = (
            "시스템은 정상 작동 중이다. "
            "서버 응답 시간은 평균 200ms이다. "
            "데이터베이스 연결 상태는 안정적이다. "
            "로그 기록은 정상 범위 내에 있다. "
            "다음 점검은 금요일로 예정되어 있다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertEqual(result["voice_profile"]["energy"], "low")
        self.assertLess(result["metrics"]["emotional_intensity"], 30.0)

    # --- 9. 어휘 복잡도 ---

    def test_vocabulary_complexity(self):
        """전문용어(영어)가 많은 콘텐츠는 어휘 복잡도가 높아야 합니다."""
        content = (
            "Kubernetes cluster에서 pod autoscaling을 설정합니다. "
            "deployment YAML manifest를 작성합니다. "
            "HPA configuration의 metrics threshold를 조정합니다. "
            "ingress controller의 TLS termination을 설정합니다. "
            "monitoring dashboard에서 resource utilization을 확인합니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertGreaterEqual(result["metrics"]["vocabulary_complexity"], 30.0)
        self.assertIn("전문용어 다수", result["characteristics"])

    # --- 10. 높은 일관성 ---

    def test_consistency_high(self):
        """일관된 어미와 문장 길이의 콘텐츠는 높은 일관성을 보여야 합니다."""
        content = (
            "프로젝트가 시작됩니다. "
            "요구사항이 정리됩니다. "
            "설계가 진행됩니다. "
            "개발이 착수됩니다. "
            "테스트가 수행됩니다. "
            "배포가 완료됩니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertGreaterEqual(result["metrics"]["consistency_score"], 70.0)

    # --- 11. 특성 감지 ---

    def test_characteristics_detected(self):
        """다양한 문체 특성이 올바르게 감지되어야 합니다."""
        # 짧은 문장 + 질문형 + 비격식체
        content = (
            "궁금하죠? "
            "맞아요. "
            "왜 그럴까요? "
            "쉽죠. "
            "해봤나요? "
            "좋아요."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        # 짧은 문장
        self.assertIn("짧은 문장 선호", result["characteristics"])
        # 질문형 구조
        self.assertIn("질문형 구조", result["characteristics"])

    # --- 12. 주요 패턴 ---

    def test_dominant_patterns(self):
        """주요 패턴이 최대 3개까지 반환되어야 합니다."""
        content = (
            "첫 번째로 확인합니다. 두 번째로 검토합니다. "
            "그리고 세 번째로 분석합니다. 또한 네 번째를 정리합니다. "
            "따라서 다섯 번째를 종합합니다. 그러므로 결론을 도출합니다. "
            "- 항목 1\n- 항목 2\n- 항목 3\n"
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        patterns = result["dominant_patterns"]
        self.assertIsInstance(patterns, list)
        self.assertLessEqual(len(patterns), 3)
        # 접속사가 많으므로 관련 패턴 포함
        self.assertTrue(len(patterns) > 0)

    # --- 13. 제안 목록 ---

    def test_suggestions_exist(self):
        """모든 분석 결과에 최소 1개의 제안이 포함되어야 합니다."""
        # 혼합 문체 → 제안 발생
        content = (
            "보고서를 제출합니다. "
            "이거 진짜 좋죠. "
            "결과는 다음과 같습니다. "
            "완전 대박이거든요. "
            "종합적으로 판단됩니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertIsInstance(result["suggestions"], list)
        self.assertGreaterEqual(len(result["suggestions"]), 1)

    # --- 추가: 데이터 중심 특성 ---

    def test_data_centric_characteristics(self):
        """숫자가 많은 콘텐츠는 '데이터 중심' 특성이 감지되어야 합니다."""
        content = (
            "2024년 매출은 150억원입니다. "
            "전년 대비 23% 증가했습니다. "
            "직원 수는 340명입니다. "
            "고객 만족도는 92점입니다. "
            "목표 달성률은 108%입니다."
        )
        result = profile_brand_voice(content)
        self._assert_valid_structure(result)

        self.assertIn("데이터 중심", result["characteristics"])


if __name__ == "__main__":
    unittest.main()
