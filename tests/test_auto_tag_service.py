"""auto_tag_service 단위 테스트"""
import unittest

from services.auto_tag_service import generate_tags, _tokenize, _compute_tfidf


class TestTokenize(unittest.TestCase):

    def test_korean_tokens(self):
        tokens = _tokenize("인공지능 기술이 발전하고 있습니다")
        self.assertIn("인공지능", tokens)
        self.assertIn("기술이", tokens)

    def test_english_tokens(self):
        tokens = _tokenize("Python framework for machine learning")
        self.assertIn("python", tokens)
        self.assertIn("framework", tokens)
        self.assertIn("machine", tokens)
        self.assertIn("learning", tokens)

    def test_stopwords_removed(self):
        tokens = _tokenize("이것은 매우 좋은 기술입니다")
        # '매우' 는 불용어
        self.assertNotIn("매우", tokens)

    def test_empty_input(self):
        self.assertEqual(_tokenize(""), [])

    def test_single_char_filtered(self):
        tokens = _tokenize("A B CD EF")
        # 1글자 필터링
        self.assertNotIn("a", tokens)
        self.assertNotIn("b", tokens)


class TestComputeTfidf(unittest.TestCase):

    def test_basic(self):
        tokens = ["python", "python", "python", "javascript", "react"]
        result = _compute_tfidf(tokens, top_n=3)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 3)

    def test_empty(self):
        self.assertEqual(_compute_tfidf([]), [])


class TestGenerateTags(unittest.TestCase):

    def test_empty_content(self):
        result = generate_tags("")
        self.assertEqual(result["tags"], [])
        self.assertEqual(result["category"], "일반")

    def test_tech_content(self):
        content = """
        Python 프로그래밍으로 API 서버를 개발합니다.
        React 프레임워크를 사용한 프론트엔드 개발과
        Docker 컨테이너 배포 방법을 학습합니다.
        인공지능 딥러닝 모델을 활용한 서비스 개발.
        """
        result = generate_tags(content)
        self.assertIsInstance(result["tags"], list)
        self.assertGreater(len(result["tags"]), 0)
        self.assertEqual(result["category"], "기술")

    def test_lifestyle_content(self):
        content = """
        건강한 다이어트를 위한 요리 레시피를 소개합니다.
        운동과 피트니스로 건강을 관리하세요.
        여행지 카페에서 맛있는 음식을 즐기세요.
        """
        result = generate_tags(content)
        self.assertEqual(result["category"], "라이프스타일")

    def test_max_tags_limit(self):
        content = "Python " * 100 + "JavaScript " * 50 + "React " * 30
        result = generate_tags(content, max_tags=5)
        self.assertLessEqual(len(result["tags"]), 5)

    def test_returns_dict(self):
        result = generate_tags("테스트 콘텐츠입니다 프로그래밍 개발")
        self.assertIn("tags", result)
        self.assertIn("category", result)


if __name__ == '__main__':
    unittest.main()
