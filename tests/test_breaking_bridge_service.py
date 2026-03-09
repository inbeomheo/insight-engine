"""breaking_bridge_service 단위 테스트"""
import unittest

from services.breaking_bridge_service import (
    generate_bridge,
    BridgePack,
    _split_sentences,
    _extract_key_facts,
    _extract_timeline,
    _build_instant_reaction,
    _generate_follow_up_questions,
)


class TestGenerateBridge(unittest.TestCase):
    """generate_bridge 함수 테스트"""

    def test_basic_bridge_generation(self):
        """기본 속보 콘텐츠로 BridgePack 생성"""
        content = (
            "오늘 오전 10시 서울 강남구에서 대규모 정전이 발생했다. "
            "한국전력에 따르면 약 5만 가구가 영향을 받았다. "
            "원인은 변전소 설비 고장으로 확인되었다. "
            "복구 작업은 오후 3시까지 완료될 예정이다."
        )
        result = generate_bridge(content)
        self.assertIsInstance(result, BridgePack)
        self.assertTrue(len(result.instant_reaction) > 0)
        self.assertTrue(len(result.deep_analysis) > 0)
        self.assertGreaterEqual(len(result.key_facts), 3)

    def test_instant_reaction_length(self):
        """즉시 반응 글이 200자 이내인지 확인"""
        content = (
            "정부가 새로운 부동산 정책을 발표했다. "
            "이번 정책은 다주택자 양도세 중과를 완화하는 것이 핵심이다. "
            "국토교통부 장관은 기자회견에서 '시장 안정을 위한 불가피한 조치'라고 밝혔다. "
            "전문가들은 시장에 미칠 영향에 대해 엇갈린 전망을 내놓고 있다."
        )
        result = generate_bridge(content)
        self.assertLessEqual(len(result.instant_reaction), 200)

    def test_instant_and_deep_different(self):
        """즉시반응과 검색형 해설이 서로 다른 콘텐츠인지 확인"""
        content = (
            "삼성전자가 차세대 반도체 공장 건설을 발표했다. "
            "투자 규모는 약 30조원에 달한다. "
            "2027년 완공 목표로 경기도 평택에 건설된다."
        )
        result = generate_bridge(content)
        # 즉시반응은 짧고, 해설은 길어야 함
        self.assertGreater(len(result.deep_analysis), len(result.instant_reaction))

    def test_key_facts_minimum_three(self):
        """핵심 사실이 최소 3개인지 확인"""
        content = (
            "폭우로 인해 한강 수위가 급격히 상승했다. "
            "기상청은 서울에 호우경보를 발령했다. "
            "교통이 마비되어 출퇴근에 큰 차질이 빚어졌다. "
            "시민들은 대피소로 이동하고 있다."
        )
        result = generate_bridge(content)
        self.assertGreaterEqual(len(result.key_facts), 3)

    def test_timeline_extraction(self):
        """타임라인이 시간 정보를 포함하는지 확인"""
        content = (
            "어제 오후 2시 지진이 발생했다. "
            "오늘 오전 9시 여진이 한 차례 더 감지되었다. "
            "기상청은 추가 여진 가능성을 경고했다."
        )
        result = generate_bridge(content)
        self.assertGreaterEqual(len(result.timeline), 1)
        for item in result.timeline:
            self.assertIn('time', item)
            self.assertIn('event', item)

    def test_follow_up_questions(self):
        """후속 질문이 생성되는지 확인"""
        content = (
            "국제유가가 배럴당 100달러를 돌파했다. "
            "OPEC의 감산 결정이 주요 원인으로 분석된다."
        )
        result = generate_bridge(content)
        self.assertGreater(len(result.follow_up_questions), 0)

    def test_empty_content_raises(self):
        """빈 콘텐츠 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_bridge("")

    def test_none_content_raises(self):
        """None 콘텐츠 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_bridge(None)

    def test_whitespace_only_raises(self):
        """공백만 있는 콘텐츠 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_bridge("   \n  \t  ")

    def test_deep_analysis_has_markdown(self):
        """검색형 해설이 마크다운 형식인지 확인"""
        content = (
            "AI 스타트업이 10억 달러 투자를 유치했다. "
            "글로벌 AI 시장이 빠르게 성장하고 있다. "
            "전문가들은 2025년까지 시장 규모가 2배로 늘어날 것으로 전망한다."
        )
        result = generate_bridge(content)
        self.assertIn('#', result.deep_analysis)
        self.assertIn('핵심 요약', result.deep_analysis)

    def test_long_content(self):
        """긴 콘텐츠도 정상 처리되는지 확인"""
        sentences = [f"뉴스 문장 {i}번입니다." for i in range(50)]
        content = " ".join(sentences)
        result = generate_bridge(content)
        self.assertIsInstance(result, BridgePack)
        self.assertLessEqual(len(result.instant_reaction), 200)


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트"""

    def test_period_split(self):
        """마침표 기준 분리"""
        result = _split_sentences("첫 번째 문장입니다. 두 번째 문장입니다.")
        self.assertEqual(len(result), 2)

    def test_newline_split(self):
        """줄바꿈 기준 분리"""
        result = _split_sentences("첫 번째 문장입니다\n두 번째 문장입니다")
        self.assertEqual(len(result), 2)

    def test_short_sentence_filtered(self):
        """짧은 문장(5자 미만)은 필터링"""
        result = _split_sentences("좋은 뉴스입니다. 네. 매우 중요한 소식입니다.")
        # "네"는 5자 미만이므로 제외
        for s in result:
            self.assertGreaterEqual(len(s), 5)


class TestExtractKeyFacts(unittest.TestCase):
    """_extract_key_facts 함수 테스트"""

    def test_fact_indicators_boost(self):
        """사실 지표가 있는 문장이 우선 선택"""
        sentences = [
            "날씨가 좋습니다.",
            "경찰에 따르면 용의자가 체포되었다.",
            "오늘 점심은 맛있었다.",
        ]
        facts = _extract_key_facts(sentences)
        self.assertIn("경찰에 따르면 용의자가 체포되었다.", facts)

    def test_minimum_three_facts(self):
        """최소 3개 사실 반환 보장"""
        sentences = ["문장 하나입니다.", "문장 둘입니다.", "문장 셋입니다.", "문장 넷입니다."]
        facts = _extract_key_facts(sentences)
        self.assertGreaterEqual(len(facts), 3)


class TestExtractTimeline(unittest.TestCase):
    """_extract_timeline 함수 테스트"""

    def test_date_extraction(self):
        """날짜 패턴 추출"""
        sentences = ["3월 15일 대통령이 담화문을 발표했다."]
        timeline = _extract_timeline(sentences)
        self.assertEqual(len(timeline), 1)
        self.assertIn("3월 15일", timeline[0]['time'])

    def test_no_time_info(self):
        """시간 정보 없으면 빈 타임라인"""
        sentences = ["사건이 발생했다.", "조사가 진행 중이다."]
        timeline = _extract_timeline(sentences)
        self.assertEqual(len(timeline), 0)

    def test_duplicate_events_removed(self):
        """중복 이벤트 제거"""
        sentences = [
            "오전 10시 폭발이 발생했다.",
            "오전 10시 폭발이 발생했다.",
        ]
        timeline = _extract_timeline(sentences)
        self.assertEqual(len(timeline), 1)


if __name__ == '__main__':
    unittest.main()
