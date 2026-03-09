"""로직모델 서비스 테스트"""
import unittest
from services.logic_model_service import (
    create_model, add_element, connect, validate_model, export_model,
    LogicModel, LogicElement
)


class TestLogicModelService(unittest.TestCase):

    def test_create_model(self):
        model = create_model('교육 프로그램')
        self.assertIsInstance(model, LogicModel)
        self.assertEqual(model.title, '교육 프로그램')
        self.assertEqual(len(model.elements), 0)

    def test_add_element(self):
        model = create_model('테스트')
        model = add_element(model, 'input', '예산 확보', ['예산액'])
        self.assertEqual(len(model.elements), 1)
        self.assertEqual(model.elements[0].element_type, 'input')

    def test_add_element_invalid_type(self):
        model = create_model('테스트')
        with self.assertRaises(ValueError):
            add_element(model, 'invalid', 'desc', [])

    def test_connect_elements(self):
        model = create_model('테스트')
        model = add_element(model, 'input', '예산', ['금액'])
        model = add_element(model, 'activity', '교육', ['참여자수'])
        e1 = model.elements[0].element_id
        e2 = model.elements[1].element_id
        model = connect(model, e1, e2)
        self.assertEqual(len(model.connections), 1)

    def test_connect_invalid_id(self):
        model = create_model('테스트')
        model = add_element(model, 'input', '예산', [])
        e1 = model.elements[0].element_id
        with self.assertRaises(ValueError):
            connect(model, e1, 'nonexistent')

    def test_validate_model_complete(self):
        model = create_model('테스트')
        for etype in ['input', 'activity', 'output', 'outcome', 'impact']:
            model = add_element(model, etype, f'{etype} 설명', [])
        errors = validate_model(model)
        self.assertEqual(len(errors), 0)

    def test_validate_model_missing_types(self):
        model = create_model('테스트')
        model = add_element(model, 'input', '예산', [])
        errors = validate_model(model)
        self.assertGreater(len(errors), 0)

    def test_validate_model_wrong_chain_order(self):
        model = create_model('테스트')
        for etype in ['input', 'activity', 'output', 'outcome', 'impact']:
            model = add_element(model, etype, etype, [])
        # input → output (체인 순서 건너뜀)
        e_input = model.elements[0].element_id
        e_output = model.elements[2].element_id
        model = connect(model, e_input, e_output)
        errors = validate_model(model)
        chain_errors = [e for e in errors if '체인 순서' in e]
        self.assertGreater(len(chain_errors), 0)

    def test_export_model_text(self):
        model = create_model('교육')
        model = add_element(model, 'input', '예산', ['금액'])
        text = export_model(model)
        self.assertIn('교육', text)
        self.assertIn('예산', text)

    def test_add_element_immutable(self):
        model = create_model('테스트')
        model2 = add_element(model, 'input', 'a', [])
        self.assertEqual(len(model.elements), 0)
        self.assertEqual(len(model2.elements), 1)

    def test_export_model_with_connections(self):
        model = create_model('테스트')
        model = add_element(model, 'input', 'i', [])
        model = add_element(model, 'activity', 'a', [])
        e1, e2 = model.elements[0].element_id, model.elements[1].element_id
        model = connect(model, e1, e2)
        text = export_model(model)
        self.assertIn('[연결]', text)


if __name__ == '__main__':
    unittest.main()
