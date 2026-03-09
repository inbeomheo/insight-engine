"""
태그 정규화 서비스 테스트
"""

import unittest

from services.tag_normalizer_service import (
    TagMapping,
    NormalizationResult,
    normalize_tag,
    normalize_tags,
    suggest_canonical,
    merge_tag_sets,
)


class TestNormalizeTag(unittest.TestCase):
    """단일 태그 정규화 테스트"""

    def test_lowercase(self):
        """소문자 변환"""
        self.assertEqual(normalize_tag("Python"), "python")

    def test_spaces_to_hyphens(self):
        """공백을 하이픈으로"""
        self.assertEqual(normalize_tag("machine learning"), "machine-learning")

    def test_underscores_to_hyphens(self):
        """언더스코어를 하이픈으로"""
        self.assertEqual(normalize_tag("deep_learning"), "deep-learning")

    def test_special_chars_removed(self):
        """특수문자 제거"""
        result = normalize_tag("c++")
        self.assertEqual(result, "c")

    def test_synonym_mapping(self):
        """동의어 매핑"""
        self.assertEqual(normalize_tag("js"), "javascript")
        self.assertEqual(normalize_tag("ts"), "typescript")
        self.assertEqual(normalize_tag("py"), "python")
        self.assertEqual(normalize_tag("ML"), "machine-learning")

    def test_synonym_reactjs(self):
        """React.js 동의어"""
        self.assertEqual(normalize_tag("React.js"), "react")
        self.assertEqual(normalize_tag("reactjs"), "react")

    def test_empty_tag(self):
        """빈 태그"""
        self.assertEqual(normalize_tag(""), "")
        self.assertEqual(normalize_tag("   "), "")

    def test_korean_tag(self):
        """한국어 태그 유지"""
        self.assertEqual(normalize_tag("프로그래밍"), "프로그래밍")

    def test_trim_hyphens(self):
        """앞뒤 하이픈 제거"""
        self.assertEqual(normalize_tag("-tag-"), "tag")

    def test_consecutive_hyphens(self):
        """연속 하이픈 제거"""
        self.assertEqual(normalize_tag("a  b   c"), "a-b-c")


class TestNormalizeTags(unittest.TestCase):
    """태그 목록 정규화 테스트"""

    def test_basic_normalization(self):
        """기본 정규화"""
        result = normalize_tags(["Python", "JS", "React.js"])
        self.assertEqual(len(result.tags), 3)
        normalized = [t.normalized for t in result.tags]
        self.assertIn("python", normalized)
        self.assertIn("javascript", normalized)
        self.assertIn("react", normalized)

    def test_duplicate_removal(self):
        """중복 제거"""
        result = normalize_tags(["Python", "python", "PYTHON"])
        self.assertEqual(len(result.tags), 1)
        self.assertEqual(result.duplicates_removed, 2)

    def test_synonym_dedup(self):
        """동의어 중복 제거 (JS와 JavaScript)"""
        result = normalize_tags(["js", "javascript"])
        self.assertEqual(len(result.tags), 1)
        self.assertEqual(result.duplicates_removed, 1)

    def test_empty_tags_filtered(self):
        """빈 태그 필터링"""
        result = normalize_tags(["python", "", "  ", "react"])
        self.assertEqual(len(result.tags), 2)

    def test_normalized_count(self):
        """정규화 횟수"""
        result = normalize_tags(["Python", "JS"])
        # Python → python (변경), JS → javascript (변경)
        self.assertGreaterEqual(result.normalized_count, 1)

    def test_confidence_same(self):
        """변경 없는 태그 신뢰도"""
        result = normalize_tags(["python"])
        self.assertEqual(result.tags[0].confidence, 1.0)

    def test_confidence_changed(self):
        """변경된 태그 신뢰도"""
        result = normalize_tags(["JS"])
        self.assertEqual(result.tags[0].confidence, 0.9)


class TestSuggestCanonical(unittest.TestCase):
    """유사 태그 제안 테스트"""

    def test_suggest_similar(self):
        """유사한 태그 제안"""
        known = ["python", "javascript", "typescript"]
        result = suggest_canonical("pythn", known)
        self.assertEqual(result, "python")

    def test_suggest_no_match(self):
        """유사한 태그 없음"""
        known = ["python", "javascript"]
        result = suggest_canonical("cooking", known)
        self.assertIsNone(result)

    def test_suggest_empty_tag(self):
        """빈 태그"""
        result = suggest_canonical("", ["python"])
        self.assertIsNone(result)

    def test_suggest_empty_known(self):
        """빈 기존 태그 목록"""
        result = suggest_canonical("python", [])
        self.assertIsNone(result)

    def test_suggest_exact_match_excluded(self):
        """정확히 같은 태그는 제안하지 않음"""
        known = ["python", "javascript"]
        result = suggest_canonical("python", known)
        self.assertIsNone(result)


class TestMergeTagSets(unittest.TestCase):
    """태그셋 병합 테스트"""

    def test_merge_basic(self):
        """기본 병합"""
        result = merge_tag_sets([["Python", "JS"], ["React", "python"]])
        self.assertIn("python", result)
        self.assertIn("javascript", result)
        self.assertIn("react", result)
        # 중복 제거 (python 1개)
        self.assertEqual(result.count("python"), 1)

    def test_merge_empty_sets(self):
        """빈 셋 병합"""
        result = merge_tag_sets([[], []])
        self.assertEqual(result, [])

    def test_merge_single_set(self):
        """단일 셋"""
        result = merge_tag_sets([["python", "react"]])
        self.assertEqual(len(result), 2)

    def test_merge_preserves_normalization(self):
        """병합 시 정규화 유지"""
        result = merge_tag_sets([["JS"], ["reactjs"]])
        self.assertIn("javascript", result)
        self.assertIn("react", result)


if __name__ == "__main__":
    unittest.main()
