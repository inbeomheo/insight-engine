"""보도자료 팩토리 서비스 테스트"""
import unittest
from datetime import date

from services.press_release_service import (
    PressKit, Quote,
    generate_press_kit, format_press_release,
    _extract_quotes, _extract_key_facts, _extract_still_timestamps,
    _build_body, _extract_sentences,
)


class TestGeneratePressKit(unittest.TestCase):
    """generate_press_kit 함수 테스트"""

    def test_basic_press_kit_generation(self):
        """기본 영상 데이터로 PressKit이 정상 생성되는지 확인"""
        video_data = {
            "title": "AI 기술 발표",
            "transcript": "오늘 발표할 내용은 AI 기술입니다. 새로운 기능을 소개합니다.",
            "speaker": "김철수",
            "company": "테크컴퍼니",
        }
        kit = generate_press_kit(video_data)

        self.assertIsInstance(kit, PressKit)
        self.assertEqual(kit.headline, "AI 기술 발표")
        self.assertIn("테크컴퍼니", kit.subheadline)
        self.assertIn("김철수", kit.speaker_bio)
        self.assertIn("테크컴퍼니", kit.speaker_bio)

    def test_press_kit_without_speaker(self):
        """발표자 정보 없이도 PressKit이 생성되는지 확인"""
        video_data = {
            "title": "제품 출시",
            "transcript": "새로운 제품이 출시되었습니다.",
        }
        kit = generate_press_kit(video_data)

        self.assertEqual(kit.headline, "제품 출시")
        self.assertEqual(kit.speaker_bio, "")
        self.assertEqual(kit.contact_info, {})

    def test_press_kit_without_company(self):
        """회사 정보 없이 발표자만 있는 경우"""
        video_data = {
            "title": "기술 강연",
            "transcript": "안녕하세요. 오늘 기술 강연을 시작합니다.",
            "speaker": "박영희",
        }
        kit = generate_press_kit(video_data)

        self.assertIn("박영희", kit.speaker_bio)
        self.assertIn("전문가", kit.speaker_bio)
        self.assertNotIn("테크컴퍼니", kit.subheadline)

    def test_press_kit_empty_data(self):
        """빈 데이터로도 에러 없이 기본 PressKit 반환"""
        kit = generate_press_kit({})

        self.assertEqual(kit.headline, "보도자료")
        self.assertIsInstance(kit.quotes, list)
        self.assertIsInstance(kit.key_facts, list)
        self.assertIsInstance(kit.still_timestamps, list)

    def test_press_kit_contact_info(self):
        """contact_info에 회사/발표자 정보가 포함되는지 확인"""
        video_data = {
            "title": "발표",
            "transcript": "발표 내용",
            "speaker": "이민수",
            "company": "스타트업X",
        }
        kit = generate_press_kit(video_data)

        self.assertEqual(kit.contact_info["organization"], "스타트업X")
        self.assertEqual(kit.contact_info["contact_person"], "이민수")


class TestExtractQuotes(unittest.TestCase):
    """인용문 추출 테스트"""

    def test_extract_korean_quotes(self):
        """한국어 큰따옴표로 감싼 인용문 추출"""
        transcript = '발표자가 "우리의 기술은 세계 최고 수준에 도달했습니다"라고 말했습니다.'
        quotes = _extract_quotes(transcript, "김대표", "테크사")

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].speaker, "김대표")
        self.assertIn("세계 최고 수준", quotes[0].text)

    def test_extract_unicode_quotes(self):
        """유니코드 따옴표(\u201C \u201D) 추출"""
        transcript = '\u201C이번 연구 결과는 매우 의미있는 성과입니다\u201D'
        quotes = _extract_quotes(transcript, "연구원", "연구소")

        self.assertEqual(len(quotes), 1)

    def test_no_quotes_in_transcript(self):
        """따옴표 없는 자막에서 빈 리스트 반환"""
        transcript = "오늘 발표 내용을 시작하겠습니다."
        quotes = _extract_quotes(transcript, "발표자", "회사")

        self.assertEqual(len(quotes), 0)

    def test_duplicate_quotes_removed(self):
        """동일한 인용문 중복 제거"""
        transcript = '"동일한 인용문입니다"라고 했다. 다시 "동일한 인용문입니다"라고 강조했다.'
        quotes = _extract_quotes(transcript, "A", "B")

        self.assertEqual(len(quotes), 1)

    def test_short_quotes_ignored(self):
        """10자 미만 짧은 따옴표는 인용문으로 추출하지 않음"""
        transcript = '"짧은말" 다음에 긴 내용이 이어집니다.'
        quotes = _extract_quotes(transcript, "A", "B")

        self.assertEqual(len(quotes), 0)


class TestExtractKeyFacts(unittest.TestCase):
    """핵심 팩트 추출 테스트"""

    def test_extract_percentage_facts(self):
        """퍼센트 포함 문장 추출"""
        transcript = "매출이 전년 대비 150% 증가했습니다. 다른 이야기도 있습니다."
        facts = _extract_key_facts(transcript)

        self.assertGreaterEqual(len(facts), 1)
        self.assertTrue(any("150%" in f for f in facts))

    def test_extract_currency_facts(self):
        """금액 포함 문장 추출"""
        transcript = "총 투자금액은 500억원에 달합니다. 회사 소개를 하겠습니다."
        facts = _extract_key_facts(transcript)

        self.assertGreaterEqual(len(facts), 1)
        self.assertTrue(any("500억" in f for f in facts))

    def test_no_facts_in_text(self):
        """숫자/통계 없는 텍스트에서 빈 리스트 반환"""
        transcript = "오늘 좋은 날씨입니다. 발표를 시작하겠습니다."
        facts = _extract_key_facts(transcript)

        self.assertEqual(len(facts), 0)

    def test_extract_count_facts(self):
        """수량 포함 문장 추출 (개, 명 등)"""
        transcript = "이 프로젝트에 참여한 인원은 총 200명입니다."
        facts = _extract_key_facts(transcript)

        self.assertGreaterEqual(len(facts), 1)
        self.assertTrue(any("200명" in f for f in facts))


class TestExtractStillTimestamps(unittest.TestCase):
    """스틸컷 시점 추출 테스트"""

    def test_extract_from_timestamped_transcript(self):
        """타임스탬프 + 전환 키워드가 있는 자막에서 시점 추출"""
        transcript = (
            "[0:00] 안녕하세요.\n"
            "[1:30] 다음으로 주요 기능을 살펴보겠습니다.\n"
            "[3:45] 한편 다른 측면도 있습니다.\n"
            "[5:00] 마지막으로 정리하겠습니다.\n"
        )
        timestamps = _extract_still_timestamps(transcript)

        self.assertGreaterEqual(len(timestamps), 2)
        self.assertIn("1:30", timestamps)

    def test_extract_from_plain_transcript(self):
        """타임스탬프 없는 자막에서 전환 키워드 기반 추정"""
        transcript = (
            "안녕하세요.\n"
            "다음으로 주요 내용을 설명합니다.\n"
            "한편 다른 관점도 있습니다.\n"
            "마지막으로 요약합니다.\n"
        )
        timestamps = _extract_still_timestamps(transcript)

        self.assertGreaterEqual(len(timestamps), 1)

    def test_empty_transcript(self):
        """빈 자막에서 빈 리스트 반환"""
        timestamps = _extract_still_timestamps("")

        self.assertEqual(timestamps, [])


class TestBuildBody(unittest.TestCase):
    """본문 구성 테스트"""

    def test_build_body_with_sentences(self):
        """여러 문장이 있는 자막에서 본문 구성"""
        transcript = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다."
        body = _build_body(transcript, "테스트")

        self.assertIn("첫 번째", body)
        self.assertIn("두 번째", body)

    def test_build_body_empty_transcript(self):
        """빈 자막에서 기본 본문 생성"""
        body = _build_body("", "테스트 제목")

        self.assertIn("테스트 제목", body)


class TestFormatPressRelease(unittest.TestCase):
    """보도자료 포맷팅 테스트"""

    def test_format_contains_date(self):
        """오늘 날짜가 포함되는지 확인"""
        kit = PressKit(
            headline="테스트 헤드라인",
            subheadline="테스트 서브헤드라인",
            body="본문 내용입니다.",
            quotes=[],
            speaker_bio="",
            key_facts=[],
            still_timestamps=[],
            contact_info={},
        )
        result = format_press_release(kit)
        today = date.today().strftime("%Y년 %m월 %d일")

        self.assertIn(today, result)

    def test_format_contains_headline(self):
        """헤드라인이 포함되는지 확인"""
        kit = PressKit(
            headline="신제품 출시 발표",
            subheadline="회사X, 신제품 출시 발표",
            body="본문입니다.",
            quotes=[],
            speaker_bio="",
            key_facts=[],
            still_timestamps=[],
            contact_info={},
        )
        result = format_press_release(kit)

        self.assertIn("# 신제품 출시 발표", result)
        self.assertIn("## 회사X", result)

    def test_format_contains_quotes(self):
        """인용문 섹션이 포맷에 포함되는지 확인"""
        kit = PressKit(
            headline="발표",
            subheadline="서브",
            body="본문",
            quotes=[Quote(text="인용 내용", speaker="김대표", title="CEO")],
            speaker_bio="",
            key_facts=[],
            still_timestamps=[],
            contact_info={},
        )
        result = format_press_release(kit)

        self.assertIn("주요 인용", result)
        self.assertIn("인용 내용", result)
        self.assertIn("김대표", result)

    def test_format_contains_facts(self):
        """팩트시트 섹션이 포함되는지 확인"""
        kit = PressKit(
            headline="발표",
            subheadline="서브",
            body="본문",
            quotes=[],
            speaker_bio="",
            key_facts=["매출 200% 증가", "사용자 100만명 돌파"],
            still_timestamps=[],
            contact_info={},
        )
        result = format_press_release(kit)

        self.assertIn("핵심 팩트", result)
        self.assertIn("매출 200% 증가", result)

    def test_format_ends_with_marker(self):
        """보도자료 종료 마커(###)가 포함되는지 확인"""
        kit = PressKit(
            headline="발표",
            subheadline="서브",
            body="본문",
            quotes=[],
            speaker_bio="",
            key_facts=[],
            still_timestamps=[],
            contact_info={},
        )
        result = format_press_release(kit)

        self.assertTrue(result.strip().endswith("###"))

    def test_format_contains_contact_info(self):
        """연락처 정보가 포함되는지 확인"""
        kit = PressKit(
            headline="발표",
            subheadline="서브",
            body="본문",
            quotes=[],
            speaker_bio="",
            key_facts=[],
            still_timestamps=[],
            contact_info={"organization": "테크사", "contact_person": "홍길동"},
        )
        result = format_press_release(kit)

        self.assertIn("문의처", result)
        self.assertIn("테크사", result)
        self.assertIn("홍길동", result)


class TestExtractSentences(unittest.TestCase):
    """문장 분리 테스트"""

    def test_split_by_period(self):
        """마침표로 문장 분리"""
        sentences = _extract_sentences("첫 문장. 둘째 문장. 셋째 문장.")
        self.assertEqual(len(sentences), 3)

    def test_empty_input(self):
        """빈 입력에서 빈 리스트 반환"""
        sentences = _extract_sentences("")
        self.assertEqual(len(sentences), 0)


if __name__ == '__main__':
    unittest.main()
