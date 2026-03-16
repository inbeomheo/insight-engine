"""
RuleBasedRewardModel / PreferenceCollector 단위 테스트 (F10-02)
"""
import json
import os
import tempfile
import unittest

from services.finetune.reward_model import (
    PreferencePair,
    RuleBasedRewardModel,
    PreferenceCollector,
)


class TestPreferencePair(unittest.TestCase):

    def test_to_dpo_format(self):
        pair = PreferencePair(prompt="p", chosen="c", rejected="r")
        dpo = pair.to_dpo_format()
        self.assertEqual(dpo, {"prompt": "p", "chosen": "c", "rejected": "r"})


class TestRuleBasedRewardModel(unittest.TestCase):

    def setUp(self):
        self.model = RuleBasedRewardModel()

    def test_empty_content_returns_zero(self):
        scores = self.model.score("", "blog_seo")
        self.assertEqual(scores["total"], 0.0)

    def test_whitespace_only_returns_zero(self):
        scores = self.model.score("   \n  ", "blog_seo")
        self.assertEqual(scores["total"], 0.0)

    def test_score_returns_all_keys(self):
        content = "한국어 블로그 테스트 콘텐츠입니다. " * 50
        scores = self.model.score(content, "blog_seo")
        expected_keys = {"total", "length_score", "structure_score", "forbidden_penalty",
                         "korean_ratio", "no_hallucination", "readability"}
        self.assertEqual(set(scores.keys()), expected_keys)

    def test_total_between_0_and_1(self):
        content = "한국어로 작성된 블로그 포스트.\n\n## 제목\n\n- 항목1\n- 항목2\n" * 30
        scores = self.model.score(content, "blog_seo")
        self.assertGreaterEqual(scores["total"], 0.0)
        self.assertLessEqual(scores["total"], 1.0)

    def test_forbidden_words_reduce_score(self):
        clean = "일반적인 블로그 내용입니다. " * 50
        dirty = "놀라운 혁신적 획기적인 블로그 내용입니다. " * 50
        score_clean = self.model.score(clean, "blog_seo")["forbidden_penalty"]
        score_dirty = self.model.score(dirty, "blog_seo")["forbidden_penalty"]
        self.assertGreater(score_clean, score_dirty)

    def test_structure_score_increases_with_headings(self):
        flat = "문장입니다. " * 100
        structured = "\n# 제목1\n\n- 항목1\n- 항목2\n\n# 제목2\n\n내용입니다.\n\n## 소제목\n\n- A\n- B\n- C\n"
        score_flat = self.model.score(flat, "blog_seo")["structure_score"]
        score_struct = self.model.score(structured, "blog_seo")["structure_score"]
        self.assertGreaterEqual(score_struct, score_flat)

    def test_different_style_length_targets(self):
        """sns_post 스타일은 짧은 콘텐츠가 적정"""
        short = "짧은 SNS 포스트 내용." * 10  # ~120자
        score_sns = self.model.score(short, "sns_post")["length_score"]
        score_blog = self.model.score(short, "blog_seo")["length_score"]
        self.assertGreater(score_sns, score_blog)

    def test_compare_returns_winner(self):
        good = "한국어 블로그 콘텐츠.\n\n## 제목\n\n- 항목\n\n내용 " * 30
        bad = ""
        result = self.model.compare(good, bad, "blog_seo")
        self.assertEqual(result, "a")

    def test_compare_tie(self):
        content = "동일한 콘텐츠." * 50
        result = self.model.compare(content, content, "blog_seo")
        self.assertEqual(result, "tie")


class TestPreferenceCollector(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.tmpdir, "prefs.jsonl")
        self.collector = PreferenceCollector(storage_path=self.storage_path)

    def test_collect_from_ab_test_auto(self):
        good = "좋은 콘텐츠입니다.\n\n## 제목\n\n- 항목\n\n" * 30
        bad = "놀라운 혁신적 획기적." * 5
        pair = self.collector.collect_from_ab_test("프롬프트", good, bad, "blog_seo")
        self.assertIsNotNone(pair)
        self.assertEqual(pair.chosen, good)

    def test_collect_with_human_preference(self):
        a = "A 콘텐츠" * 50
        b = "B 콘텐츠" * 50
        pair = self.collector.collect_from_ab_test("프롬프트", a, b, "blog_seo", human_preference="b")
        self.assertIsNotNone(pair)
        self.assertEqual(pair.chosen, b)
        self.assertEqual(pair.rejected, a)

    def test_tie_returns_none(self):
        content = "동일한 콘텐츠입니다. " * 50
        pair = self.collector.collect_from_ab_test("프롬프트", content, content, "blog_seo")
        self.assertIsNone(pair)

    def test_save_and_load_pairs(self):
        good = "좋은 한국어 콘텐츠.\n\n## 제목\n\n- 항목\n\n" * 30
        bad = "나쁜." * 5
        self.collector.collect_from_ab_test("프롬프트", good, bad, "blog_seo")
        pairs = self.collector.load_pairs()
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].prompt, "프롬프트")

    def test_load_pairs_empty_file(self):
        pairs = self.collector.load_pairs()
        self.assertEqual(pairs, [])

    def test_export_dpo_dataset(self):
        good = "한국어 콘텐츠.\n\n## 제목\n\n" * 30
        bad = "짧은." * 3
        self.collector.collect_from_ab_test("프롬프트", good, bad)
        output_path = os.path.join(self.tmpdir, "dpo.jsonl")
        count = self.collector.export_dpo_dataset(output_path)
        self.assertEqual(count, 1)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.loads(f.readline())
        self.assertIn("prompt", data)
        self.assertIn("chosen", data)


if __name__ == "__main__":
    unittest.main()
