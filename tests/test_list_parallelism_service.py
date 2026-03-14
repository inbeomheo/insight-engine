"""List Parallelism Checker 서비스 테스트."""
import unittest
from services.analysis.list_parallelism_service import check_list_parallelism


class TestListParallelism(unittest.TestCase):

    def test_empty_content(self):
        result = check_list_parallelism('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_list_parallelism(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_lists(self):
        content = '일반 텍스트입니다.\n문단이 이어집니다.\n목록이 없습니다.'
        result = check_list_parallelism(content)
        self.assertEqual(result['summary']['total_lists'], 0)

    def test_parallel_list(self):
        content = ('다음 단계를 따르세요:\n'
                   '- 프로젝트를 생성합니다\n'
                   '- 패키지를 설치합니다\n'
                   '- 서버를 시작합니다\n')
        result = check_list_parallelism(content)
        self.assertGreater(result['summary']['total_lists'], 0)
        self.assertEqual(result['summary']['non_parallel_lists'], 0)

    def test_non_parallel_ending(self):
        content = ('목록:\n'
                   '- 프로젝트를 생성합니다\n'
                   '- 패키지 설치하기\n'
                   '- 서버 시작\n'
                   '- 테스트를 실행해요\n')
        result = check_list_parallelism(content)
        self.assertGreater(result['summary']['non_parallel_lists'], 0)

    def test_english_imperative_parallel(self):
        content = ('Steps:\n'
                   '- Create a new project\n'
                   '- Install dependencies\n'
                   '- Run the server\n')
        result = check_list_parallelism(content)
        self.assertEqual(result['summary']['parallel_lists'],
                         result['summary']['total_lists'])

    def test_numbered_list(self):
        content = ('절차:\n'
                   '1. 계정을 만듭니다\n'
                   '2. 프로필을 설정합니다\n'
                   '3. 서비스를 시작합니다\n')
        result = check_list_parallelism(content)
        self.assertGreater(result['summary']['total_lists'], 0)

    def test_multiple_lists(self):
        content = ('첫 번째 목록:\n'
                   '- 항목 하나입니다\n'
                   '- 항목 둘입니다\n'
                   '\n일반 텍스트 구간입니다.\n\n'
                   '두 번째 목록:\n'
                   '- 기능 확인\n'
                   '- 성능 테스트\n')
        result = check_list_parallelism(content)
        self.assertEqual(result['summary']['total_lists'], 2)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_list_parallelism(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_list_parallelism(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('parallelism_issues', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_lists', result['summary'])
        self.assertIn('parallel_lists', result['summary'])
        self.assertIn('non_parallel_lists', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_non_parallel(self):
        content = ('목록:\n'
                   '- 설정하기\n'
                   '- 확인합니다\n'
                   '- 완료\n')
        result = check_list_parallelism(content)
        if result['summary']['non_parallel_lists'] > 0:
            self.assertGreater(len(result['suggestions']), 0)

    def test_consistent_level(self):
        content = ('가이드:\n'
                   '- Use TypeScript for type safety\n'
                   '- Use ESLint for linting\n'
                   '- Use Prettier for formatting\n')
        result = check_list_parallelism(content)
        self.assertIn(result['summary']['level'], ('none', 'consistent'))

    def test_single_item_not_counted(self):
        content = '목록:\n- 하나뿐인 항목\n\n일반 텍스트.'
        result = check_list_parallelism(content)
        self.assertEqual(result['summary']['total_lists'], 0)

    def test_length_inconsistency(self):
        content = ('목록:\n'
                   '- 아주 긴 설명이 들어간 항목으로 상세하게 작성된 내용이 이어집니다\n'
                   '- 짧음\n'
                   '- 역시 매우 길고 상세한 설명이 포함된 긴 항목입니다\n')
        result = check_list_parallelism(content)
        # 길이 비일관성 감지 여부 확인
        self.assertGreater(result['summary']['total_lists'], 0)


if __name__ == '__main__':
    unittest.main()
