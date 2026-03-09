"""recording_guide_service 단위 테스트"""
import unittest

from services.recording_guide_service import (
    GuideStep,
    StepGuide,
    recording_to_guide,
    _detect_action,
    _extract_target,
    _extract_tip,
    _split_lines,
    _format_duration,
    _deduplicate_steps,
    _extract_prerequisites,
)


class TestRecordingToGuide(unittest.TestCase):
    """recording_to_guide 함수 통합 테스트"""

    def test_empty_transcript_raises(self):
        """빈 자막이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            recording_to_guide('')

    def test_whitespace_only_raises(self):
        """공백만 있는 자막이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            recording_to_guide('   \n  \t  ')

    def test_none_raises(self):
        """None 입력이면 ValueError 발생"""
        with self.assertRaises(ValueError):
            recording_to_guide(None)

    def test_basic_guide_generation(self):
        """동작 키워드가 충분한 자막에서 가이드 생성"""
        transcript = (
            '먼저 브라우저를 열어주세요\n'
            '"로그인" 버튼을 클릭합니다\n'
            '이메일 필드에 주소를 입력합니다\n'
            '비밀번호를 입력하세요\n'
            '"확인" 버튼을 클릭합니다\n'
            '대시보드가 열립니다\n'
            '설정 메뉴를 선택합니다\n'
        )
        result = recording_to_guide(transcript)

        self.assertIsInstance(result, StepGuide)
        self.assertGreaterEqual(result.total_steps, 5)
        self.assertEqual(result.total_steps, len(result.steps))
        self.assertTrue(result.title)
        self.assertTrue(result.estimated_time)

    def test_minimum_five_steps_guaranteed(self):
        """동작 키워드가 부족해도 5단계 이상 보장"""
        transcript = (
            '화면에 메뉴가 보입니다\n'
            '여기서 버튼을 클릭합니다\n'
            '다음 화면으로 넘어갑니다\n'
            '결과가 표시됩니다\n'
            '이 기능은 매우 유용합니다\n'
            '데이터가 저장되었습니다\n'
            '작업이 완료되었습니다\n'
        )
        result = recording_to_guide(transcript)
        self.assertGreaterEqual(result.total_steps, 5)

    def test_step_numbers_sequential(self):
        """단계 번호가 1부터 순차적인지 검증"""
        transcript = (
            '파일 메뉴를 클릭합니다\n'
            '"새 문서"를 선택합니다\n'
            '제목을 입력합니다\n'
            '내용을 작성합니다\n'
            '"저장" 버튼을 클릭합니다\n'
        )
        result = recording_to_guide(transcript)
        for i, step in enumerate(result.steps, 1):
            self.assertEqual(step.step_number, i)

    def test_steps_are_guidestep_instances(self):
        """각 단계가 GuideStep 인스턴스인지 확인"""
        transcript = (
            '설정을 열어주세요\n'
            '언어를 선택합니다\n'
            '한국어를 클릭합니다\n'
            '확인 버튼을 누릅니다\n'
            '저장을 클릭합니다\n'
        )
        result = recording_to_guide(transcript)
        for step in result.steps:
            self.assertIsInstance(step, GuideStep)
            self.assertTrue(step.action)
            self.assertTrue(step.target)
            self.assertTrue(step.description)

    def test_prerequisites_extracted(self):
        """사전 조건이 올바르게 추출되는지 확인"""
        transcript = (
            '먼저 Chrome 브라우저를 실행합니다\n'
            '사이트에 로그인합니다\n'
            '프로그램을 설치해야 합니다\n'
            '설정 메뉴를 클릭합니다\n'
            '옵션을 선택합니다\n'
            '저장 버튼을 클릭합니다\n'
        )
        result = recording_to_guide(transcript)
        self.assertGreater(len(result.prerequisites), 0)
        # 브라우저, 로그인, 설치 관련 사전 조건 확인
        prereq_text = ' '.join(result.prerequisites)
        self.assertTrue(
            any(kw in prereq_text for kw in ['로그인', '브라우저', '설치']),
        )

    def test_estimated_time_format(self):
        """예상 시간이 올바른 형식인지 확인"""
        transcript = (
            '버튼을 클릭합니다\n'
            '메뉴를 선택합니다\n'
            '값을 입력합니다\n'
            '확인을 클릭합니다\n'
            '저장을 클릭합니다\n'
        )
        result = recording_to_guide(transcript)
        self.assertTrue(result.estimated_time.startswith('약'))

    def test_english_actions_detected(self):
        """영어 동작 키워드도 감지되는지 확인"""
        transcript = (
            'Click the "Settings" button\n'
            'Select your language preference\n'
            'Type your email address\n'
            'Press the submit button\n'
            'Open the dashboard page\n'
        )
        result = recording_to_guide(transcript)
        actions = [s.action for s in result.steps]
        self.assertTrue(any(a in actions for a in ['클릭', '선택', '입력', '열기']))

    def test_duplicate_steps_merged(self):
        """연속 중복 단계가 병합되는지 확인"""
        transcript = (
            '"저장" 버튼을 클릭합니다\n'
            '"저장" 버튼을 클릭합니다\n'
            '"저장" 버튼을 클릭합니다\n'
            '메뉴를 선택합니다\n'
            '값을 입력합니다\n'
            '확인을 클릭합니다\n'
            '완료 버튼을 클릭합니다\n'
        )
        result = recording_to_guide(transcript)
        # 3개의 동일 "저장 클릭"이 1개로 병합
        descriptions = [s.description for s in result.steps]
        save_count = sum(1 for d in descriptions if '저장' in d and '클릭' in d)
        self.assertLessEqual(save_count, 1)

    def test_tip_extraction(self):
        """팁/참고 문구가 추출되는지 확인"""
        transcript = (
            '"새 프로젝트"를 클릭합니다. 참고: 관리자 권한이 필요합니다\n'
            '이름을 입력합니다\n'
            '카테고리를 선택합니다\n'
            '저장을 클릭합니다\n'
            '목록에서 확인합니다\n'
        )
        result = recording_to_guide(transcript)
        tips = [s.tip for s in result.steps if s.tip]
        self.assertGreater(len(tips), 0)


class TestDetectAction(unittest.TestCase):
    """_detect_action 함수 단위 테스트"""

    def test_korean_click(self):
        self.assertEqual(_detect_action('버튼을 클릭합니다'), '클릭')

    def test_english_click(self):
        self.assertEqual(_detect_action('Click the button'), '클릭')

    def test_korean_input(self):
        self.assertEqual(_detect_action('이름을 입력합니다'), '입력')

    def test_korean_select(self):
        self.assertEqual(_detect_action('항목을 선택합니다'), '선택')

    def test_no_action(self):
        self.assertIsNone(_detect_action('이것은 일반 문장입니다'))

    def test_drag(self):
        self.assertEqual(_detect_action('파일을 드래그합니다'), '드래그')

    def test_scroll(self):
        self.assertEqual(_detect_action('페이지를 스크롤합니다'), '스크롤')

    def test_open(self):
        self.assertEqual(_detect_action('프로그램을 실행합니다'), '열기')

    def test_delete(self):
        self.assertEqual(_detect_action('항목을 삭제합니다'), '삭제')

    def test_search(self):
        self.assertEqual(_detect_action('키워드를 검색합니다'), '검색')


class TestExtractTarget(unittest.TestCase):
    """_extract_target 함수 단위 테스트"""

    def test_quoted_target(self):
        self.assertEqual(_extract_target('"저장" 버튼을 클릭'), '저장')

    def test_single_quoted_target(self):
        self.assertEqual(_extract_target("'설정' 메뉴를 선택"), '설정')

    def test_button_label(self):
        result = _extract_target('버튼: 확인을 클릭')
        self.assertTrue(result)

    def test_fallback_word(self):
        """패턴 매칭 실패 시 핵심 단어 반환"""
        result = _extract_target('대시보드 화면에서 진행합니다')
        self.assertTrue(result)


class TestExtractTip(unittest.TestCase):
    """_extract_tip 함수 단위 테스트"""

    def test_tip_with_colon(self):
        result = _extract_tip('팁: Ctrl+S로 빠르게 저장 가능')
        self.assertEqual(result, 'Ctrl+S로 빠르게 저장 가능')

    def test_note_keyword(self):
        result = _extract_tip('참고: 관리자만 접근 가능합니다')
        self.assertIsNotNone(result)

    def test_no_tip(self):
        result = _extract_tip('버튼을 클릭합니다')
        self.assertIsNone(result)


class TestSplitLines(unittest.TestCase):
    """_split_lines 함수 테스트"""

    def test_basic_split(self):
        text = '첫째 줄\n둘째 줄\n셋째 줄'
        result = _split_lines(text)
        self.assertEqual(len(result), 3)

    def test_empty_lines_removed(self):
        text = '첫째 줄\n\n둘째 줄\n\n\n셋째 줄'
        result = _split_lines(text)
        self.assertEqual(len(result), 3)

    def test_sentence_split(self):
        text = '첫째 문장. 둘째 문장. 셋째 문장.'
        result = _split_lines(text)
        self.assertGreaterEqual(len(result), 1)


class TestFormatDuration(unittest.TestCase):
    """_format_duration 함수 테스트"""

    def test_seconds_only(self):
        self.assertEqual(_format_duration(30), '약 30초')

    def test_minutes_even(self):
        self.assertEqual(_format_duration(120), '약 2분')

    def test_minutes_and_seconds(self):
        self.assertEqual(_format_duration(150), '약 2분 30초')


class TestDeduplicateSteps(unittest.TestCase):
    """_deduplicate_steps 함수 테스트"""

    def test_no_duplicates(self):
        steps = [
            {'action': '클릭', 'target': '버튼A', 'description': 'A 클릭'},
            {'action': '입력', 'target': '필드B', 'description': 'B 입력'},
        ]
        result = _deduplicate_steps(steps)
        self.assertEqual(len(result), 2)

    def test_consecutive_duplicates(self):
        steps = [
            {'action': '클릭', 'target': '버튼A', 'description': 'A 클릭'},
            {'action': '클릭', 'target': '버튼A', 'description': 'A 클릭 또'},
            {'action': '입력', 'target': '필드B', 'description': 'B 입력'},
        ]
        result = _deduplicate_steps(steps)
        self.assertEqual(len(result), 2)

    def test_empty_list(self):
        result = _deduplicate_steps([])
        self.assertEqual(len(result), 0)


class TestExtractPrerequisites(unittest.TestCase):
    """_extract_prerequisites 함수 테스트"""

    def test_login_detected(self):
        result = _extract_prerequisites('먼저 사이트에 로그인하세요')
        self.assertTrue(any('로그인' in p for p in result))

    def test_browser_detected(self):
        result = _extract_prerequisites('Chrome 브라우저를 실행합니다')
        self.assertTrue(any('브라우저' in p for p in result))

    def test_no_prereqs(self):
        result = _extract_prerequisites('버튼을 클릭합니다')
        self.assertEqual(len(result), 0)

    def test_no_duplicates(self):
        result = _extract_prerequisites('로그인 후 다시 로그인합니다')
        login_count = sum(1 for p in result if '로그인' in p)
        self.assertEqual(login_count, 1)


if __name__ == '__main__':
    unittest.main()
