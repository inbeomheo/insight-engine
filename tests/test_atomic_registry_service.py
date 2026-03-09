"""원자 레지스트리 서비스 테스트"""
import unittest
from services.atomic_registry_service import (
    AtomicUnit, Registry,
    register_unit, search_units, verify_unit,
    get_most_used, increment_usage,
)


class TestRegisterUnit(unittest.TestCase):
    """원자 단위 등록 테스트"""

    def setUp(self):
        self.registry = Registry(registry_id='r1', units=[], type_index={})

    def test_register_fact(self):
        result = register_unit(self.registry, '파이썬은 1991년에 만들어졌다.', 'fact', 'Wikipedia')
        self.assertEqual(len(result.units), 1)
        self.assertEqual(result.units[0].unit_type, 'fact')
        self.assertEqual(result.units[0].source, 'Wikipedia')
        self.assertFalse(result.units[0].verified)
        self.assertEqual(result.units[0].usage_count, 0)

    def test_register_definition(self):
        result = register_unit(self.registry, 'AI는 인공지능의 약어입니다.', 'definition')
        self.assertEqual(result.units[0].unit_type, 'definition')

    def test_register_quote(self):
        result = register_unit(self.registry, '"지식이 힘이다" - 베이컨', 'quote')
        self.assertEqual(result.units[0].unit_type, 'quote')

    def test_register_statistic(self):
        result = register_unit(self.registry, '사용자의 80%가 만족', 'statistic')
        self.assertEqual(result.units[0].unit_type, 'statistic')

    def test_register_example(self):
        result = register_unit(self.registry, '예: for i in range(10)', 'example')
        self.assertEqual(result.units[0].unit_type, 'example')

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            register_unit(self.registry, '내용', 'invalid_type')

    def test_empty_content(self):
        with self.assertRaises(ValueError):
            register_unit(self.registry, '', 'fact')

    def test_duplicate_rejected(self):
        """중복 콘텐츠 등록 거부"""
        reg = register_unit(self.registry, '파이썬은 좋다.', 'fact')
        reg = register_unit(reg, '파이썬은 좋다.', 'fact')
        self.assertEqual(len(reg.units), 1)

    def test_type_index_updated(self):
        """타입 인덱스 업데이트"""
        reg = register_unit(self.registry, '팩트1', 'fact')
        reg = register_unit(reg, '정의1', 'definition')
        self.assertIn('fact', reg.type_index)
        self.assertIn('definition', reg.type_index)
        self.assertEqual(len(reg.type_index['fact']), 1)

    def test_content_stripped(self):
        result = register_unit(self.registry, '  공백 있는 내용  ', 'fact')
        self.assertEqual(result.units[0].content, '공백 있는 내용')


class TestSearchUnits(unittest.TestCase):
    """원자 단위 검색 테스트"""

    def setUp(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        reg = register_unit(reg, '파이썬은 1991년에 만들어졌다.', 'fact')
        reg = register_unit(reg, '머신러닝은 AI의 하위 분야입니다.', 'definition')
        reg = register_unit(reg, '파이썬 사용자의 70%가 데이터 분석에 활용.', 'statistic')
        reg = register_unit(reg, '예시: import numpy as np', 'example')
        self.registry = reg

    def test_keyword_search(self):
        results = search_units(self.registry, '파이썬')
        self.assertGreater(len(results), 0)
        self.assertTrue(any('파이썬' in u.content for u in results))

    def test_type_filter(self):
        results = search_units(self.registry, '파이썬', unit_type='fact')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].unit_type, 'fact')

    def test_empty_query_returns_all(self):
        results = search_units(self.registry, '')
        self.assertEqual(len(results), 4)

    def test_type_only_filter(self):
        results = search_units(self.registry, '', unit_type='definition')
        self.assertEqual(len(results), 1)

    def test_no_match(self):
        results = search_units(self.registry, 'ZZZZZ없는단어')
        self.assertEqual(len(results), 0)

    def test_partial_match(self):
        """부분 키워드 매칭"""
        results = search_units(self.registry, 'AI')
        self.assertGreater(len(results), 0)


class TestVerifyUnit(unittest.TestCase):
    """검증 완료 처리 테스트"""

    def test_verify(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        reg = register_unit(reg, '팩트 내용', 'fact')
        unit_id = reg.units[0].unit_id

        result = verify_unit(reg, unit_id)
        self.assertTrue(result.units[0].verified)

    def test_verify_nonexistent(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        with self.assertRaises(ValueError):
            verify_unit(reg, 'nonexistent')

    def test_verify_preserves_other_fields(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        reg = register_unit(reg, '팩트 내용', 'fact', source='출처')
        unit_id = reg.units[0].unit_id

        result = verify_unit(reg, unit_id)
        self.assertEqual(result.units[0].source, '출처')
        self.assertEqual(result.units[0].content, '팩트 내용')


class TestGetMostUsed(unittest.TestCase):
    """사용 빈도 상위 조회 테스트"""

    def test_most_used(self):
        units = [
            AtomicUnit('u1', '내용1', 'fact', '', True, 10),
            AtomicUnit('u2', '내용2', 'fact', '', True, 5),
            AtomicUnit('u3', '내용3', 'fact', '', True, 20),
        ]
        reg = Registry(registry_id='r1', units=units, type_index={})

        result = get_most_used(reg, top_k=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].unit_id, 'u3')  # 20회
        self.assertEqual(result[1].unit_id, 'u1')  # 10회

    def test_empty_registry(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        result = get_most_used(reg, top_k=5)
        self.assertEqual(len(result), 0)

    def test_top_k_exceeds(self):
        units = [AtomicUnit('u1', '내용', 'fact', '', True, 1)]
        reg = Registry(registry_id='r1', units=units, type_index={})
        result = get_most_used(reg, top_k=10)
        self.assertEqual(len(result), 1)


class TestIncrementUsage(unittest.TestCase):
    """사용 횟수 증가 테스트"""

    def test_increment(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        reg = register_unit(reg, '내용', 'fact')
        unit_id = reg.units[0].unit_id

        result = increment_usage(reg, unit_id)
        self.assertEqual(result.units[0].usage_count, 1)

        result = increment_usage(result, unit_id)
        self.assertEqual(result.units[0].usage_count, 2)

    def test_increment_nonexistent(self):
        reg = Registry(registry_id='r1', units=[], type_index={})
        with self.assertRaises(ValueError):
            increment_usage(reg, 'nonexistent')

    def test_increment_preserves_verified(self):
        units = [AtomicUnit('u1', '내용', 'fact', '', True, 5)]
        reg = Registry(registry_id='r1', units=units, type_index={})
        result = increment_usage(reg, 'u1')
        self.assertTrue(result.units[0].verified)
        self.assertEqual(result.units[0].usage_count, 6)


if __name__ == '__main__':
    unittest.main()
