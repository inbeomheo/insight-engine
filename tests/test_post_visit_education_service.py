"""진료후 교육 서비스 테스트"""
import unittest
from services.post_visit_education_service import (
    generate_material, simplify_language, create_checklist, validate_material,
    EducationMaterial, DEFAULT_DISCLAIMER
)


class TestPostVisitEducationService(unittest.TestCase):

    def setUp(self):
        self.material = generate_material(
            '발치', ['얼음 찜질 20분', '부드러운 음식 섭취'],
            ['출혈 시 거즈 물기', '음주 금지']
        )

    def test_generate_material(self):
        self.assertIsInstance(self.material, EducationMaterial)
        self.assertEqual(self.material.procedure, '발치')
        self.assertEqual(len(self.material.instructions), 2)

    def test_generate_material_auto_disclaimer(self):
        self.assertEqual(self.material.disclaimer, DEFAULT_DISCLAIMER)

    def test_simplify_language(self):
        mat = generate_material('처방 투여', ['경구 투여 1일 2회'], ['부작용 주의'])
        simplified = simplify_language(mat)
        self.assertIn('복용', simplified.instructions[0])
        self.assertIn('나쁜 반응', simplified.warnings[0])

    def test_simplify_preserves_id(self):
        simplified = simplify_language(self.material)
        self.assertEqual(simplified.material_id, self.material.material_id)

    def test_create_checklist(self):
        checklist = create_checklist(self.material)
        self.assertEqual(len(checklist), 4)
        self.assertTrue(checklist[0].startswith('[ ]'))
        self.assertTrue(checklist[2].startswith('[!]'))

    def test_create_checklist_with_followup(self):
        mat = generate_material('시술', ['지시1'], ['경고1'])
        # follow_up 추가
        mat.follow_up = ['1주 후 재방문']
        checklist = create_checklist(mat)
        self.assertTrue(any('[>]' in c for c in checklist))

    def test_validate_material_valid(self):
        errors = validate_material(self.material)
        self.assertEqual(len(errors), 0)

    def test_validate_material_missing_procedure(self):
        mat = generate_material('', ['지시'], ['경고'])
        errors = validate_material(mat)
        self.assertIn('시술명이 비어 있습니다.', errors)

    def test_validate_material_no_instructions(self):
        mat = generate_material('시술', [], ['경고'])
        errors = validate_material(mat)
        self.assertIn('지시사항이 없습니다.', errors)

    def test_validate_material_no_warnings(self):
        mat = generate_material('시술', ['지시'], [])
        errors = validate_material(mat)
        self.assertIn('주의사항이 없습니다.', errors)

    def test_validate_material_no_disclaimer(self):
        mat = generate_material('시술', ['지시'], ['경고'])
        mat.disclaimer = ''
        errors = validate_material(mat)
        self.assertIn('면책조항이 없습니다.', errors)


if __name__ == '__main__':
    unittest.main()
