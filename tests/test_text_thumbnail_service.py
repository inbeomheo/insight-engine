"""
텍스트 썸네일 서비스 단위 테스트
"""
import unittest

from services.text_thumbnail_service import (
    ThumbnailResult,
    generate_text_thumbnail,
    list_styles,
    STYLE_PALETTES,
    AVAILABLE_STYLES,
    _split_title_lines,
    _calculate_font_size,
    _calculate_readability_score,
    _hex_brightness,
    _MAX_CHARS_PER_LINE,
    _FONT_SIZE_MAX,
    _FONT_SIZE_MIN,
)


class TestGenerateTextThumbnail(unittest.TestCase):
    """generate_text_thumbnail 함수 테스트"""

    def test_기본_생성_결과_타입(self):
        """기본 호출 시 ThumbnailResult 반환"""
        result = generate_text_thumbnail("테스트 제목")
        self.assertIsInstance(result, ThumbnailResult)

    def test_기본_스타일_bold(self):
        """스타일 미지정 시 기본값 bold"""
        result = generate_text_thumbnail("제목")
        self.assertEqual(result.style, "bold")

    def test_모든_스타일_적용(self):
        """5가지 스타일 모두 정상 동작"""
        for style in AVAILABLE_STYLES:
            result = generate_text_thumbnail("스타일 테스트", style=style)
            self.assertEqual(result.style, style)
            self.assertIn("bg", result.colors)
            self.assertIn("text", result.colors)
            self.assertIn("accent", result.colors)

    def test_잘못된_스타일_폴백(self):
        """존재하지 않는 스타일 → bold 폴백"""
        result = generate_text_thumbnail("제목", style="존재하지않음")
        self.assertEqual(result.style, "bold")

    def test_빈_제목_기본값(self):
        """빈 제목 → '제목 없음' 기본값"""
        result = generate_text_thumbnail("")
        self.assertEqual(result.title, "제목 없음")

    def test_None_제목_기본값(self):
        """None 제목 → '제목 없음' 기본값"""
        result = generate_text_thumbnail(None)
        self.assertEqual(result.title, "제목 없음")

    def test_레이아웃_필드_존재(self):
        """layout에 필수 필드가 모두 포함"""
        result = generate_text_thumbnail("레이아웃 확인")
        expected_keys = {"width", "height", "text_align", "vertical_align", "padding", "line_spacing"}
        self.assertTrue(expected_keys.issubset(set(result.layout.keys())))

    def test_레이아웃_기본_크기(self):
        """기본 해상도 1280x720"""
        result = generate_text_thumbnail("크기 확인")
        self.assertEqual(result.layout["width"], 1280)
        self.assertEqual(result.layout["height"], 720)

    def test_가독성_점수_범위(self):
        """readability_score는 0~100 사이"""
        for title in ["짧", "적절한 길이의 제목", "아주 긴 제목입니다 " * 10]:
            result = generate_text_thumbnail(title)
            self.assertGreaterEqual(result.readability_score, 0.0)
            self.assertLessEqual(result.readability_score, 100.0)

    def test_colors_복사본_반환(self):
        """반환된 colors는 원본 팔레트의 복사본"""
        result = generate_text_thumbnail("색상 테스트", style="neon")
        result.colors["bg"] = "#FFFFFF"
        # 원본은 변경되지 않아야 함
        self.assertEqual(STYLE_PALETTES["neon"]["bg"], "#0A0A0A")

    def test_공백만_있는_제목(self):
        """공백만 있는 제목 → '제목 없음'"""
        result = generate_text_thumbnail("   ")
        self.assertEqual(result.title, "제목 없음")

    def test_긴_제목_폰트_크기_감소(self):
        """긴 제목은 짧은 제목보다 작은 폰트"""
        short = generate_text_thumbnail("짧음")
        long = generate_text_thumbnail("이것은 매우 긴 제목입니다 여러 줄에 걸쳐 표시되어야 합니다")
        self.assertGreater(short.font_size, long.font_size)


class TestSplitTitleLines(unittest.TestCase):
    """_split_title_lines 함수 테스트"""

    def test_짧은_제목_한줄(self):
        """12자 이하 제목은 한 줄"""
        lines = _split_title_lines("짧은 제목")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "짧은 제목")

    def test_긴_제목_줄바꿈(self):
        """12자 초과 시 여러 줄로 분리"""
        lines = _split_title_lines("이것은 매우 긴 제목으로 여러 줄이 필요합니다")
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(len(line), _MAX_CHARS_PER_LINE)

    def test_단일_긴_단어_강제분할(self):
        """12자 초과 단일 단어는 강제 분할"""
        long_word = "가나다라마바사아자차카타파하히"  # 15자
        lines = _split_title_lines(long_word)
        for line in lines:
            self.assertLessEqual(len(line), _MAX_CHARS_PER_LINE)

    def test_빈_문자열(self):
        """빈 문자열 → 빈 리스트"""
        lines = _split_title_lines("")
        self.assertEqual(lines, [])


class TestCalculateFontSize(unittest.TestCase):
    """_calculate_font_size 함수 테스트"""

    def test_짧은_제목_큰_폰트(self):
        """1~5자 → 최대 크기에 근접"""
        size = _calculate_font_size("테스트")
        self.assertGreaterEqual(size, 60)
        self.assertLessEqual(size, _FONT_SIZE_MAX)

    def test_긴_제목_작은_폰트(self):
        """50자+ → 최소 크기에 근접"""
        size = _calculate_font_size("가" * 60)
        self.assertGreaterEqual(size, _FONT_SIZE_MIN)
        self.assertLessEqual(size, 40)

    def test_빈_제목_최대크기(self):
        """빈 제목 → 최대 폰트 크기"""
        size = _calculate_font_size("")
        self.assertEqual(size, _FONT_SIZE_MAX)

    def test_범위_내_유지(self):
        """어떤 길이든 MIN~MAX 범위 내"""
        for length in [1, 5, 10, 20, 50, 100, 500]:
            size = _calculate_font_size("가" * length)
            self.assertGreaterEqual(size, _FONT_SIZE_MIN)
            self.assertLessEqual(size, _FONT_SIZE_MAX)


class TestReadabilityScore(unittest.TestCase):
    """_calculate_readability_score 함수 테스트"""

    def test_적절한_제목_높은_점수(self):
        """적절한 길이(10~30자) + 대비 좋은 스타일 → 높은 점수"""
        lines = _split_title_lines("적절한 길이의 제목입니다")
        score = _calculate_readability_score("적절한 길이의 제목입니다", "bold", lines)
        self.assertGreater(score, 70.0)

    def test_매우_짧은_제목_감점(self):
        """3자 미만 → 감점"""
        lines = ["가"]
        score = _calculate_readability_score("가", "bold", lines)
        self.assertLess(score, 90.0)

    def test_매우_긴_제목_감점(self):
        """40자 초과 → 감점"""
        long_title = "가나다라마바사아자차" * 5
        lines = _split_title_lines(long_title)
        score = _calculate_readability_score(long_title, "bold", lines)
        self.assertLess(score, 90.0)


class TestHexBrightness(unittest.TestCase):
    """_hex_brightness 함수 테스트"""

    def test_검정(self):
        self.assertAlmostEqual(_hex_brightness("#000000"), 0.0, places=1)

    def test_흰색(self):
        self.assertAlmostEqual(_hex_brightness("#FFFFFF"), 255.0, places=1)

    def test_잘못된_형식_기본값(self):
        """파싱 불가 → 128.0"""
        self.assertEqual(_hex_brightness("invalid"), 128.0)

    def test_해시_없는_형식(self):
        """# 없이도 정상 동작"""
        result = _hex_brightness("FF0000")
        self.assertGreater(result, 0.0)


class TestListStyles(unittest.TestCase):
    """list_styles 함수 테스트"""

    def test_5개_스타일_반환(self):
        styles = list_styles()
        self.assertEqual(len(styles), 5)

    def test_필수_스타일_포함(self):
        styles = list_styles()
        for s in ["bold", "minimal", "gradient", "dark", "neon"]:
            self.assertIn(s, styles)

    def test_원본_리스트_보호(self):
        """반환값 수정이 원본에 영향 없음"""
        styles = list_styles()
        styles.append("custom")
        self.assertEqual(len(list_styles()), 5)


if __name__ == "__main__":
    unittest.main()
