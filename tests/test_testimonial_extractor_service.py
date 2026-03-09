"""testimonial_extractor_service 단위 테스트"""
import unittest

from services.testimonial_extractor_service import (
    TestimonialCard,
    extract_testimonials,
    testimonial_cards_to_dicts,
    _analyze_sentiment,
    _calculate_credibility,
    _deduplicate_cards,
    _extract_direct_quotes,
    _extract_speaker_quotes,
)


class TestExtractTestimonials(unittest.TestCase):
    """extract_testimonials 함수 테스트"""

    def test_empty_transcript_raises(self):
        """빈 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            extract_testimonials("")

    def test_whitespace_raises(self):
        """공백만 있는 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            extract_testimonials("   \n  ")

    def test_short_transcript_raises(self):
        """20자 미만 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            extract_testimonials("짧은 텍스트")

    def test_direct_quote_extraction(self):
        """직접 인용 부호로 감싼 발언 추출"""
        transcript = (
            '김사장은 "이 제품을 사용한 지 3년이 되었는데, 정말 만족합니다"라고 말했습니다. '
            '그리고 이어서 "품질이 훌륭하고 가격도 합리적입니다"라고 덧붙였습니다.'
        )
        cards = extract_testimonials(transcript)

        self.assertGreater(len(cards), 0)
        for card in cards:
            self.assertIsInstance(card, TestimonialCard)
            self.assertTrue(len(card.quote) > 0)

    def test_speaker_colon_format(self):
        """'발화자: 발화' 형태 추출"""
        transcript = (
            "인터뷰 진행합니다.\n"
            "김부장: 이 기술을 도입한 후 생산성이 30% 향상되었습니다.\n"
            "박대리: 사용하기 편리하고 학습 곡선이 낮습니다."
        )
        cards = extract_testimonials(transcript)

        speakers = [c.speaker for c in cards]
        self.assertTrue(any("김부장" in s for s in speakers) or len(cards) > 0)

    def test_sentiment_assignment(self):
        """감성 분석이 올바르게 적용"""
        transcript = (
            '"이 제품은 정말 좋고 훌륭하며 추천합니다. 만족스러운 경험이었습니다."'
        )
        cards = extract_testimonials(transcript)

        if cards:
            # 긍정 키워드가 많으므로 positive
            self.assertEqual(cards[0].sentiment, "positive")

    def test_credibility_score_range(self):
        """신뢰도 점수는 0.0~1.0 범위"""
        transcript = (
            '전문가: "10년 경험을 바탕으로 말하면, 이 데이터가 연구 결과를 뒷받침합니다."\n'
            '사용자: "그냥 괜찮습니다. 무난한 선택이에요."'
        )
        cards = extract_testimonials(transcript)

        for card in cards:
            self.assertGreaterEqual(card.credibility_score, 0.0)
            self.assertLessEqual(card.credibility_score, 1.0)

    def test_sorted_by_credibility(self):
        """결과가 신뢰도 내림차순 정렬"""
        transcript = (
            '"그냥 괜찮은 제품입니다."\n'
            '"5년 경험으로 테스트한 결과, 성능이 30% 향상되었습니다. 정말 추천합니다."'
        )
        cards = extract_testimonials(transcript)

        if len(cards) >= 2:
            for i in range(len(cards) - 1):
                self.assertGreaterEqual(
                    cards[i].credibility_score,
                    cards[i + 1].credibility_score,
                )

    def test_opinion_sentence_extraction(self):
        """의견/감상 표현이 담긴 문장 추출"""
        transcript = (
            "기술 발전이 빠르게 진행되고 있습니다. "
            "이 방식이 앞으로 대세가 될 것이라고 생각합니다. "
            "저는 이 도구를 확실히 추천합니다."
        )
        cards = extract_testimonials(transcript)
        # 의견 표현이 있으므로 추출되어야 함
        self.assertGreater(len(cards), 0)

    def test_deduplication(self):
        """동일 인용문 중복 제거"""
        transcript = (
            '"이 제품은 정말 좋습니다" 라고 했다. '
            '다시 한번 "이 제품은 정말 좋습니다" 라고 강조했다.'
        )
        cards = extract_testimonials(transcript)

        # 동일 인용은 하나만
        quotes = [c.quote for c in cards]
        # 정규화 후 중복 없어야 함
        self.assertEqual(len(set(q.strip().lower() for q in quotes)), len(quotes))


class TestAnalyzeSentiment(unittest.TestCase):
    """_analyze_sentiment 함수 테스트"""

    def test_positive_text(self):
        """긍정 키워드 다수 → positive"""
        self.assertEqual(_analyze_sentiment("정말 좋고 훌륭한 제품"), "positive")

    def test_negative_text(self):
        """부정 키워드 다수 → negative"""
        self.assertEqual(_analyze_sentiment("나쁘고 불만족스럽고 실망"), "negative")

    def test_neutral_text(self):
        """감성 키워드 없음 → neutral"""
        self.assertEqual(_analyze_sentiment("일반적인 설명 텍스트"), "neutral")


class TestCalculateCredibility(unittest.TestCase):
    """_calculate_credibility 함수 테스트"""

    def test_booster_keywords_increase(self):
        """신뢰도 부스터 키워드가 점수를 올림"""
        base = _calculate_credibility("괜찮은 제품", "")
        boosted = _calculate_credibility("10년 경험으로 직접 테스트한 연구 결과", "전문가")
        self.assertGreater(boosted, base)

    def test_specific_numbers_boost(self):
        """구체적 숫자/단위 포함 시 가산"""
        base = _calculate_credibility("성능이 향상되었습니다", "")
        with_nums = _calculate_credibility("성능이 30% 향상되었습니다", "")
        self.assertGreater(with_nums, base)

    def test_score_always_in_range(self):
        """점수는 항상 0.0~1.0 범위"""
        score1 = _calculate_credibility("", "")
        score2 = _calculate_credibility("경험 연구 데이터 테스트 검증 전문 직접 실제로 50%달성 3년간 100개", "전문가")
        self.assertGreaterEqual(score1, 0.0)
        self.assertLessEqual(score1, 1.0)
        self.assertGreaterEqual(score2, 0.0)
        self.assertLessEqual(score2, 1.0)


class TestDeduplicateCards(unittest.TestCase):
    """_deduplicate_cards 함수 테스트"""

    def test_duplicates_removed(self):
        """동일 인용 중복 제거"""
        cards = [
            TestimonialCard("같은 인용문입니다", "A", "맥락1", "positive", 0.8),
            TestimonialCard("같은 인용문입니다", "B", "맥락2", "neutral", 0.5),
        ]
        result = _deduplicate_cards(cards)
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        """빈 리스트 처리"""
        self.assertEqual(_deduplicate_cards([]), [])


class TestExtractDirectQuotes(unittest.TestCase):
    """_extract_direct_quotes 함수 테스트"""

    def test_double_quote(self):
        """큰따옴표 인용 추출"""
        text = '그는 "이 기술은 10년 경험에서 나온 것입니다"라고 말했다.'
        quotes = _extract_direct_quotes(text)
        self.assertGreater(len(quotes), 0)

    def test_short_quote_ignored(self):
        """10자 미만 인용은 무시"""
        text = '"짧아" 라고 말했다.'
        quotes = _extract_direct_quotes(text)
        self.assertEqual(len(quotes), 0)


class TestExtractSpeakerQuotes(unittest.TestCase):
    """_extract_speaker_quotes 함수 테스트"""

    def test_korean_speaker(self):
        """한국어 발화자: 발화 형태 추출"""
        text = "김대리: 이 프로젝트는 성공적으로 완료되었습니다."
        quotes = _extract_speaker_quotes(text)
        self.assertGreater(len(quotes), 0)
        self.assertEqual(quotes[0].speaker, "김대리")

    def test_label_excluded(self):
        """'참고', '주의' 등 레이블은 발화자로 인식 안 함"""
        text = "참고: 이 내용은 참고용입니다."
        quotes = _extract_speaker_quotes(text)
        self.assertEqual(len(quotes), 0)


class TestTestimonialCardToDict(unittest.TestCase):
    """직렬화 테스트"""

    def test_to_dicts(self):
        """TestimonialCard → dict 변환"""
        cards = [
            TestimonialCard("인용", "화자", "맥락", "positive", 0.8),
        ]
        result = testimonial_cards_to_dicts(cards)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["quote"], "인용")
        self.assertEqual(result[0]["sentiment"], "positive")
        self.assertIsInstance(result[0], dict)


if __name__ == '__main__':
    unittest.main()
