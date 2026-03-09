"""범용 사이드카 서비스 테스트"""

import unittest
from services.universal_sidecar_service import (
    SidecarPanel,
    build_glossary_panel, build_outline_panel, build_stats_panel,
    combine_panels,
)


class TestBuildGlossaryPanel(unittest.TestCase):
    """build_glossary_panel 테스트"""

    def test_extract_acronyms(self):
        """대문자 약어 추출"""
        content = "API와 SDK를 활용한 개발 방법을 알아봅니다. REST API 설계 원칙."
        panel = build_glossary_panel(content)
        terms = [item["term"] for item in panel.items]
        self.assertIn("API", terms)
        self.assertIn("SDK", terms)
        self.assertIn("REST", terms)

    def test_extract_parenthetical_definitions(self):
        """괄호 정의 추출"""
        content = "캐시(Cache)를 활용하면 성능이 향상됩니다."
        panel = build_glossary_panel(content)
        terms = [item["term"] for item in panel.items]
        self.assertIn("캐시", terms)

    def test_panel_type_is_glossary(self):
        """패널 타입 확인"""
        panel = build_glossary_panel("API 사용법")
        self.assertEqual(panel.panel_type, "glossary")

    def test_no_duplicates(self):
        """중복 용어 없음"""
        content = "API API API SDK SDK"
        panel = build_glossary_panel(content)
        terms = [item["term"] for item in panel.items]
        self.assertEqual(len(terms), len(set(terms)))

    def test_empty_content(self):
        """빈 콘텐츠"""
        panel = build_glossary_panel("")
        self.assertEqual(len(panel.items), 0)


class TestBuildOutlinePanel(unittest.TestCase):
    """build_outline_panel 테스트"""

    def test_extract_headings(self):
        """마크다운 헤딩 추출"""
        content = "# 제목\n본문\n## 소제목1\n내용\n### 세부제목\n내용"
        panel = build_outline_panel(content)
        self.assertEqual(len(panel.items), 3)

    def test_heading_levels(self):
        """헤딩 레벨 구분"""
        content = "# H1\n## H2\n### H3"
        panel = build_outline_panel(content)
        self.assertEqual(panel.items[0]["level"], 1)
        self.assertEqual(panel.items[1]["level"], 2)
        self.assertEqual(panel.items[2]["level"], 3)

    def test_panel_type_is_outline(self):
        """패널 타입 확인"""
        panel = build_outline_panel("# 제목")
        self.assertEqual(panel.panel_type, "outline")

    def test_line_numbers_tracked(self):
        """라인 번호 추적"""
        content = "본문\n# 제목\n내용"
        panel = build_outline_panel(content)
        self.assertEqual(panel.items[0]["line"], 2)

    def test_no_headings(self):
        """헤딩 없는 콘텐츠"""
        panel = build_outline_panel("일반 텍스트만 있습니다.")
        self.assertEqual(len(panel.items), 0)


class TestBuildStatsPanel(unittest.TestCase):
    """build_stats_panel 테스트"""

    def test_stats_have_required_labels(self):
        """필수 통계 항목 포함"""
        content = "한국어 테스트 콘텐츠입니다. 두 번째 문장입니다."
        panel = build_stats_panel(content)
        labels = [item["label"] for item in panel.items]
        self.assertIn("글자수", labels)
        self.assertIn("단어수", labels)
        self.assertIn("문장수", labels)
        self.assertIn("예상 읽기 시간", labels)

    def test_panel_type_is_stats(self):
        """패널 타입 확인"""
        panel = build_stats_panel("테스트")
        self.assertEqual(panel.panel_type, "stats")

    def test_char_count_excludes_spaces(self):
        """글자수는 공백 제외"""
        content = "a b c"
        panel = build_stats_panel(content)
        char_item = next(i for i in panel.items if i["label"] == "글자수")
        self.assertEqual(char_item["value"], 3)  # 'abc'

    def test_reading_time_calculated(self):
        """읽기 시간 계산됨 (1분 이상)"""
        content = "한글 " * 300  # 300 단어
        panel = build_stats_panel(content)
        time_item = next(i for i in panel.items if i["label"] == "예상 읽기 시간")
        self.assertIn("분", str(time_item["value"]))


class TestCombinePanels(unittest.TestCase):
    """combine_panels 테스트"""

    def test_panels_sorted_by_priority(self):
        """타입 우선순위에 따라 정렬"""
        glossary = build_glossary_panel("API SDK")
        outline = build_outline_panel("# 제목")
        stats = build_stats_panel("내용")

        combined = combine_panels([glossary, stats, outline])
        types = [p.panel_type for p in combined]
        self.assertEqual(types[0], "outline")
        self.assertEqual(types[1], "stats")
        self.assertEqual(types[2], "glossary")

    def test_combine_empty_list(self):
        """빈 목록 정렬"""
        combined = combine_panels([])
        self.assertEqual(len(combined), 0)

    def test_combine_single_panel(self):
        """단일 패널"""
        panel = build_stats_panel("내용")
        combined = combine_panels([panel])
        self.assertEqual(len(combined), 1)

    def test_combine_preserves_all_panels(self):
        """모든 패널 보존"""
        panels = [
            build_glossary_panel("API"),
            build_outline_panel("# H1"),
            build_stats_panel("내용"),
        ]
        combined = combine_panels(panels)
        self.assertEqual(len(combined), 3)


if __name__ == "__main__":
    unittest.main()
