"""regulatory_insert_service 단위 테스트"""
import unittest
from services.regulatory_insert_service import (
    Disclaimer,
    get_required_disclaimers,
    insert_regulatory,
    _is_already_present,
)


class TestDisclaimerDataclass(unittest.TestCase):
    """Disclaimer 데이터클래스 테스트"""

    def test_disclaimer_fields(self):
        """Disclaimer 필드가 올바르게 생성된다"""
        d = Disclaimer(
            text='면책 문구', category='general',
            required=True, position='footer',
        )
        self.assertEqual(d.text, '면책 문구')
        self.assertEqual(d.category, 'general')
        self.assertTrue(d.required)
        self.assertEqual(d.position, 'footer')

    def test_disclaimer_optional_field(self):
        """required=False인 Disclaimer도 생성된다"""
        d = Disclaimer(
            text='선택 문구', category='health',
            required=False, position='inline',
        )
        self.assertFalse(d.required)


class TestIsAlreadyPresent(unittest.TestCase):
    """_is_already_present 내부 함수 테스트"""

    def test_exact_match(self):
        """정확히 일치하는 문구를 감지한다"""
        content = '본문입니다. ※ 본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.'
        disclaimer = '※ 본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.'
        self.assertTrue(_is_already_present(content, disclaimer))

    def test_without_special_char(self):
        """※ 없이도 핵심 텍스트가 일치하면 감지한다"""
        content = '본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.'
        disclaimer = '※ 본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.'
        self.assertTrue(_is_already_present(content, disclaimer))

    def test_not_present(self):
        """포함되지 않은 문구는 False"""
        content = '일반적인 본문 내용입니다.'
        disclaimer = '※ 투자 권유가 아닙니다.'
        self.assertFalse(_is_already_present(content, disclaimer))

    def test_case_insensitive(self):
        """대소문자 무시 비교"""
        content = 'This is AI generated content.'
        disclaimer = 'This is AI Generated Content.'
        self.assertTrue(_is_already_present(content, disclaimer))


class TestGetRequiredDisclaimers(unittest.TestCase):
    """get_required_disclaimers 함수 테스트"""

    def test_finance_disclaimers(self):
        """금융 면책조항이 반환된다"""
        disclaimers = get_required_disclaimers('finance')
        self.assertGreaterEqual(len(disclaimers), 1)
        self.assertTrue(all(d.category == 'finance' for d in disclaimers))
        # 투자 관련 문구 포함 확인
        texts = ' '.join(d.text for d in disclaimers)
        self.assertIn('투자', texts)

    def test_health_disclaimers(self):
        """건강 면책조항이 반환된다"""
        disclaimers = get_required_disclaimers('health')
        self.assertGreaterEqual(len(disclaimers), 1)
        texts = ' '.join(d.text for d in disclaimers)
        self.assertIn('의료', texts)

    def test_legal_disclaimers(self):
        """법률 면책조항이 반환된다"""
        disclaimers = get_required_disclaimers('legal')
        self.assertGreaterEqual(len(disclaimers), 1)
        texts = ' '.join(d.text for d in disclaimers)
        self.assertIn('법적', texts)

    def test_general_disclaimers(self):
        """일반 면책조항이 반환된다"""
        disclaimers = get_required_disclaimers('general')
        self.assertGreaterEqual(len(disclaimers), 1)
        texts = ' '.join(d.text for d in disclaimers)
        self.assertIn('AI', texts)

    def test_invalid_type_raises(self):
        """유효하지 않은 content_type은 ValueError"""
        with self.assertRaises(ValueError):
            get_required_disclaimers('gaming')

    def test_returns_copy(self):
        """원본 리스트의 복사본을 반환한다"""
        d1 = get_required_disclaimers('general')
        d2 = get_required_disclaimers('general')
        self.assertIsNot(d1, d2)


class TestInsertRegulatory(unittest.TestCase):
    """insert_regulatory 함수 테스트"""

    def test_general_insert(self):
        """일반 콘텐츠에 AI 생성 면책조항이 삽입된다"""
        content = '이것은 본문입니다.'
        result = insert_regulatory(content)
        self.assertIn('AI', result)
        self.assertIn('---', result)
        # 원본 본문 유지
        self.assertIn('이것은 본문입니다.', result)

    def test_finance_insert(self):
        """금융 콘텐츠에 투자 면책조항이 삽입된다"""
        content = '주식 분석 결과입니다.'
        result = insert_regulatory(content, content_type='finance')
        self.assertIn('투자 권유가 아니', result)

    def test_health_insert(self):
        """건강 콘텐츠에 의료 면책조항이 삽입된다"""
        content = '건강 정보입니다.'
        result = insert_regulatory(content, content_type='health')
        self.assertIn('의료 전문가', result)

    def test_legal_insert(self):
        """법률 콘텐츠에 법적 면책조항이 삽입된다"""
        content = '법률 안내입니다.'
        result = insert_regulatory(content, content_type='legal')
        self.assertIn('법적 조언이 아닙니다', result)

    def test_none_raises(self):
        """None 입력은 ValueError"""
        with self.assertRaises(ValueError):
            insert_regulatory(None)

    def test_invalid_type_raises(self):
        """유효하지 않은 content_type은 ValueError"""
        with self.assertRaises(ValueError):
            insert_regulatory('본문', content_type='invalid')

    def test_no_duplicate_insert(self):
        """이미 포함된 면책 문구는 중복 삽입하지 않는다"""
        content = '본문입니다.\n\n---\n※ 본 콘텐츠는 AI에 의해 생성되었으며, 사실과 다를 수 있습니다.'
        result = insert_regulatory(content, content_type='general')
        # AI 면책 문구가 정확히 한 번만 존재
        count = result.count('AI에 의해 생성')
        self.assertEqual(count, 1)

    def test_idempotent(self):
        """두 번 적용해도 결과가 동일하다"""
        content = '원본 본문입니다.'
        first = insert_regulatory(content, content_type='general')
        second = insert_regulatory(first, content_type='general')
        self.assertEqual(first, second)

    def test_footer_position(self):
        """footer 위치의 문구는 콘텐츠 끝에 삽입된다"""
        content = '본문 시작.'
        result = insert_regulatory(content, content_type='general')
        # 본문이 면책조항보다 앞에 위치
        body_idx = result.index('본문 시작.')
        disclaimer_idx = result.index('AI에 의해 생성')
        self.assertLess(body_idx, disclaimer_idx)

    def test_empty_content_still_inserts(self):
        """빈 콘텐츠에도 면책조항이 삽입된다"""
        result = insert_regulatory('', content_type='general')
        self.assertIn('AI', result)

    def test_default_type_is_general(self):
        """기본 content_type은 'general'이다"""
        result = insert_regulatory('본문')
        self.assertIn('AI에 의해 생성', result)


if __name__ == '__main__':
    unittest.main()
