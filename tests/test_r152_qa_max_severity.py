"""R152: qa_gate_service.check_quality에 max_severity 필드 추가 테스트."""
import unittest
from unittest.mock import patch


class TestQAMaxSeverity(unittest.TestCase):
    """check_quality 응답의 max_severity 필드 검증."""

    @patch('services.quality.qa_gate_service.QA_MIN_CHARS', 10)
    @patch('services.quality.qa_gate_service.QA_MIN_SECTIONS', 1)
    def test_max_severity_none_when_clean(self):
        """이슈 없을 때 max_severity는 'none'."""
        from services.quality.qa_gate_service import check_quality
        content = "## 섹션 제목\n\n" + "정상적인 콘텐츠 텍스트입니다. " * 10
        result = check_quality(content)
        self.assertIn('max_severity', result)
        self.assertEqual(result['max_severity'], 'none')

    @patch('services.quality.qa_gate_service.QA_MIN_CHARS', 10)
    @patch('services.quality.qa_gate_service.QA_MIN_SECTIONS', 5)
    @patch('services.quality.qa_gate_service.QA_FORBIDDEN_WORDS', [])
    def test_max_severity_warning(self):
        """경고만 있을 때 max_severity는 'warning'."""
        from services.quality.qa_gate_service import check_quality
        content = "## 하나만 있는 섹션\n\n" + "충분히 긴 텍스트 내용입니다. " * 10
        result = check_quality(content)
        self.assertEqual(result['max_severity'], 'warning')

    @patch('services.quality.qa_gate_service.QA_MIN_CHARS', 99999)
    def test_max_severity_error(self):
        """에러가 있을 때 max_severity는 'error'."""
        from services.quality.qa_gate_service import check_quality
        result = check_quality("짧은 텍스트")
        self.assertEqual(result['max_severity'], 'error')

    def test_max_severity_in_exception_fallback(self):
        """예외 발생 시 fallback에도 max_severity 존재."""
        from services.quality.qa_gate_service import check_quality
        with patch('services.quality.qa_gate_service._check_length', side_effect=Exception('test')):
            result = check_quality("테스트")
        self.assertIn('max_severity', result)
        self.assertEqual(result['max_severity'], 'none')


if __name__ == '__main__':
    unittest.main()
