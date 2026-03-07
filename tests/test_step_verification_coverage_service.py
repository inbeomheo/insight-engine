"""Step Verification Coverage Analyzer 서비스 테스트."""
import unittest
from services.step_verification_coverage_service import analyze_step_verification_coverage


class TestStepVerificationCoverage(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_step_verification_coverage('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_step_verification_coverage(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_steps(self):
        content = '일반 텍스트입니다. 단계가 없습니다.'
        result = analyze_step_verification_coverage(content)
        self.assertEqual(result['summary']['total_steps'], 0)

    def test_steps_with_verification(self):
        content = ('단계 1: 프로젝트 생성\n'
                   '다음 명령어를 실행합니다.\n'
                   '```\nnpx create-app\n```\n'
                   '확인: 프로젝트 폴더가 생성되면 성공입니다.\n\n'
                   '단계 2: 의존성 설치\n'
                   'npm install을 실행합니다.\n'
                   '예상 결과: node_modules 폴더가 생성됩니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['verified_steps'], 0)

    def test_steps_without_verification(self):
        content = ('단계 1: 프로젝트 생성\n'
                   'create-app을 실행합니다.\n\n'
                   '단계 2: 의존성 설치\n'
                   'npm install을 실행합니다.\n\n'
                   '단계 3: 서버 시작\n'
                   'npm start를 실행합니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['unverified_steps'], 0)

    def test_numbered_steps(self):
        content = ('1. 환경을 설정합니다.\n'
                   '2. 코드를 작성합니다.\n'
                   '3. 테스트를 실행합니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['total_steps'], 0)

    def test_english_steps(self):
        content = ('Step 1: Create project\n'
                   'Run the init command.\n'
                   'You should see the welcome screen.\n\n'
                   'Step 2: Install deps\n'
                   'Run npm install.\n'
                   'Verify that node_modules exists.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['verified_steps'], 0)

    def test_thorough_level(self):
        content = ('단계 1: 설치\n'
                   '설치 명령어를 실행합니다.\n'
                   '확인: 설치 완료 메시지가 표시됩니다.\n\n'
                   '단계 2: 설정\n'
                   '설정 파일을 수정합니다.\n'
                   '예상 결과: 설정이 적용됩니다.\n\n'
                   '단계 3: 실행\n'
                   '서버를 시작합니다.\n'
                   '정상 작동하면 포트 3000에서 접속됩니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertIn(result['summary']['level'], ('thorough', 'partial'))

    def test_coverage_ratio(self):
        content = ('단계 1: 생성\n'
                   '프로젝트를 생성합니다.\n'
                   '올바르게 설치되었는지 확인합니다.\n\n'
                   '단계 2: 빌드\n'
                   '빌드를 실행합니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['coverage_ratio'], 0.0)
        self.assertLess(result['summary']['coverage_ratio'], 100.1)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_step_verification_coverage(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_step_verification_coverage(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('step_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_steps', result['summary'])
        self.assertIn('verified_steps', result['summary'])
        self.assertIn('unverified_steps', result['summary'])
        self.assertIn('coverage_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_missing(self):
        content = ('단계 1: 설치\n설치합니다.\n\n'
                   '단계 2: 설정\n설정합니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_code_block_as_verification(self):
        content = ('단계 1: 실행\n'
                   '다음을 실행합니다.\n'
                   '```bash\nnpm start\n```\n'
                   '출력:\n```\nServer running on port 3000\n```\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(result['summary']['verified_steps'], 0)

    def test_step_details_content(self):
        content = ('단계 1: 설치\n설치합니다.\n확인합니다.\n\n'
                   '단계 2: 설정\n설정합니다.\n')
        result = analyze_step_verification_coverage(content)
        self.assertGreater(len(result['step_details']), 0)
        detail = result['step_details'][0]
        self.assertIn('has_verification', detail)


if __name__ == '__main__':
    unittest.main()
