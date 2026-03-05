"""
OCR 서비스 단위 테스트

Gemini Vision API를 모킹하여 이미지 텍스트 추출을 테스트합니다.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os


class TestExtractTextFromImage(unittest.TestCase):
    """extract_text_from_image 단위 테스트"""

    def test_raises_file_not_found(self):
        """존재하지 않는 파일에서 FileNotFoundError 발생"""
        from services.ocr_service import extract_text_from_image

        with self.assertRaises(FileNotFoundError):
            extract_text_from_image("/nonexistent/image.png")

    @patch("services.ocr_service.os.path.exists", return_value=True)
    def test_raises_on_unsupported_format(self, mock_exists):
        """지원하지 않는 형식에서 ValueError 발생"""
        from services.ocr_service import extract_text_from_image

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_image("/path/to/file.bmp")
        self.assertIn("지원하지 않는", str(ctx.exception))

    @patch("services.ocr_service.completion")
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("services.ocr_service.os.path.exists", return_value=True)
    def test_successful_extraction(self, mock_exists, mock_completion):
        """성공적인 텍스트 추출"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "추출된 텍스트입니다."
        mock_completion.return_value = mock_response

        from services.ocr_service import extract_text_from_image

        result = extract_text_from_image("/path/to/image.png")

        self.assertEqual(result["source_type"], "ocr")
        self.assertEqual(result["title"], "OCR 추출")
        self.assertEqual(result["content"], "추출된 텍스트입니다.")

        # LiteLLM completion이 호출되었는지 확인
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")

    @patch("services.ocr_service.completion")
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("services.ocr_service.os.path.exists", return_value=True)
    def test_raises_on_empty_result(self, mock_exists, mock_completion):
        """빈 결과에서 ValueError 발생"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""
        mock_completion.return_value = mock_response

        from services.ocr_service import extract_text_from_image

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_image("/path/to/image.jpg")
        self.assertIn("텍스트를 찾을 수 없습니다", str(ctx.exception))

    @patch("services.ocr_service.completion")
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("services.ocr_service.os.path.exists", return_value=True)
    def test_raises_on_api_error(self, mock_exists, mock_completion):
        """API 오류 시 ValueError 발생"""
        mock_completion.side_effect = Exception("API rate limit exceeded")

        from services.ocr_service import extract_text_from_image

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_image("/path/to/image.png")
        self.assertIn("실패", str(ctx.exception))


class TestExtractFromUpload(unittest.TestCase):
    """extract_from_upload 단위 테스트"""

    def test_raises_on_unsupported_format(self):
        """지원하지 않는 업로드 형식에서 ValueError 발생"""
        from services.ocr_service import extract_from_upload

        mock_file = MagicMock()
        mock_file.filename = "document.pdf"

        with self.assertRaises(ValueError):
            extract_from_upload(mock_file)

    @patch("services.ocr_service.completion")
    def test_successful_upload_extraction(self, mock_completion):
        """업로드 파일에서 성공적인 텍스트 추출"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "업로드 이미지 텍스트"
        mock_completion.return_value = mock_response

        mock_file = MagicMock()
        mock_file.filename = "screenshot.png"
        mock_file.read.return_value = b"fake png data"

        from services.ocr_service import extract_from_upload

        result = extract_from_upload(mock_file)

        self.assertEqual(result["source_type"], "ocr")
        self.assertEqual(result["content"], "업로드 이미지 텍스트")


if __name__ == "__main__":
    unittest.main()
