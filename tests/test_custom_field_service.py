"""custom_field_service 단위 테스트"""
import unittest

from services.data import custom_field_service


class TestCustomFieldService(unittest.TestCase):
    """커스텀 필드 서비스 테스트"""

    def setUp(self):
        """각 테스트 전 저장소 초기화"""
        with custom_field_service._lock:
            custom_field_service._schemas.clear()
            custom_field_service._values.clear()

    # ── 스키마 관리 ──

    def test_create_field_schema(self):
        """스키마 생성 성공"""
        schema = custom_field_service.create_field_schema('ws1', '우선순위', 'select', options=['높음', '보통', '낮음'])
        self.assertEqual(schema['name'], '우선순위')
        self.assertEqual(schema['field_type'], 'select')
        self.assertEqual(schema['workspace_id'], 'ws1')
        self.assertIn('id', schema)

    def test_invalid_type_defaults_to_text(self):
        """유효하지 않은 타입은 text로 기본값"""
        schema = custom_field_service.create_field_schema('ws1', '필드', 'invalid_type')
        self.assertEqual(schema['field_type'], 'text')

    def test_list_schemas_by_workspace(self):
        """워크스페이스별 스키마 조회"""
        custom_field_service.create_field_schema('ws1', '필드A')
        custom_field_service.create_field_schema('ws2', '필드B')
        custom_field_service.create_field_schema('ws1', '필드C')
        ws1_schemas = custom_field_service.list_schemas('ws1')
        self.assertEqual(len(ws1_schemas), 2)

    def test_delete_schema(self):
        """스키마 삭제"""
        schema = custom_field_service.create_field_schema('ws1', '삭제용')
        self.assertTrue(custom_field_service.delete_schema(schema['id']))
        self.assertEqual(len(custom_field_service.list_schemas('ws1')), 0)

    def test_delete_nonexistent_schema(self):
        """존재하지 않는 스키마 삭제 시 False"""
        self.assertFalse(custom_field_service.delete_schema('no-such-id'))

    def test_get_schema(self):
        """스키마 단일 조회"""
        schema = custom_field_service.create_field_schema('ws1', '조회용')
        found = custom_field_service.get_schema(schema['id'])
        self.assertEqual(found['name'], '조회용')

    def test_get_schema_not_found(self):
        """없는 스키마 조회 시 None"""
        self.assertIsNone(custom_field_service.get_schema('no-such-id'))

    # ── 값 관리 ──

    def test_set_and_get_field_value(self):
        """필드 값 설정 및 조회"""
        custom_field_service.set_field_value('item1', 'field1', '값')
        values = custom_field_service.get_field_values('item1')
        self.assertEqual(values['field1'], '값')

    def test_get_empty_field_values(self):
        """값이 없는 아이템 조회 시 빈 dict"""
        values = custom_field_service.get_field_values('no-item')
        self.assertEqual(values, {})

    def test_delete_field_values(self):
        """필드 값 삭제"""
        custom_field_service.set_field_value('item1', 'f1', 'v1')
        custom_field_service.delete_field_values('item1')
        self.assertEqual(custom_field_service.get_field_values('item1'), {})

    def test_overwrite_field_value(self):
        """같은 필드에 값 덮어쓰기"""
        custom_field_service.set_field_value('item1', 'f1', 'old')
        custom_field_service.set_field_value('item1', 'f1', 'new')
        values = custom_field_service.get_field_values('item1')
        self.assertEqual(values['f1'], 'new')


if __name__ == '__main__':
    unittest.main()
