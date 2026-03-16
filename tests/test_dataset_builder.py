"""
DatasetBuilder 단위 테스트 (F10-01)
"""
import json
import os
import tempfile
import unittest

from services.finetune.dataset_builder import DatasetBuilder, TrainingExample


class TestTrainingExample(unittest.TestCase):

    def setUp(self):
        self.example = TrainingExample(
            instruction="SEO 블로그 작성",
            input="YouTube URL: https://example.com\n영상 제목: 테스트",
            output="생성된 블로그 콘텐츠" * 20,
        )

    def test_to_openai_format(self):
        result = self.example.to_openai_format()
        self.assertIn("messages", result)
        messages = result["messages"]
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[2]["role"], "assistant")

    def test_to_openai_format_no_instruction(self):
        ex = TrainingExample(instruction="", input="질문", output="답변")
        result = ex.to_openai_format()
        # instruction 없으면 system 메시지 스킵
        self.assertEqual(len(result["messages"]), 2)

    def test_to_alpaca_format(self):
        result = self.example.to_alpaca_format()
        self.assertEqual(result["instruction"], "SEO 블로그 작성")
        self.assertIn("input", result)
        self.assertIn("output", result)

    def test_to_sharegpt_format(self):
        result = self.example.to_sharegpt_format()
        self.assertIn("conversations", result)
        convs = result["conversations"]
        self.assertEqual(len(convs), 2)
        self.assertEqual(convs[0]["from"], "human")
        self.assertEqual(convs[1]["from"], "gpt")


class TestDatasetBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = DatasetBuilder(min_output_length=10)
        self.tmpdir = tempfile.mkdtemp()

    def test_add_example_accepted(self):
        ex = TrainingExample(instruction="inst", input="inp", output="a" * 20)
        self.assertTrue(self.builder.add_example(ex))
        self.assertEqual(len(self.builder.examples), 1)

    def test_add_example_rejected_too_short(self):
        ex = TrainingExample(instruction="inst", input="inp", output="짧음")
        self.assertFalse(self.builder.add_example(ex))
        self.assertEqual(len(self.builder.examples), 0)

    def test_add_from_history(self):
        records = [
            {"url": "https://yt.com/1", "title": "영상1", "style_id": "blog_seo",
             "content": "블로그 콘텐츠 " * 20},
            {"url": "https://yt.com/2", "title": "영상2", "style_id": "summary",
             "content": ""},  # 빈 콘텐츠 → 스킵
            {"url": "https://yt.com/3", "title": "영상3", "style_id": "tutorial",
             "content": "튜토리얼 내용 " * 20},
        ]
        added = self.builder.add_from_history(records)
        self.assertEqual(added, 2)

    def test_build_instruction_known_style(self):
        inst = self.builder._build_instruction("blog_seo")
        self.assertIn("SEO", inst)

    def test_build_instruction_unknown_style(self):
        inst = self.builder._build_instruction("unknown_style")
        self.assertIn("한국어", inst)

    def test_split(self):
        for i in range(10):
            self.builder.add_example(
                TrainingExample(instruction="", input=f"inp{i}", output="a" * 20)
            )
        train, val = self.builder.split(train_ratio=0.8)
        self.assertEqual(len(train) + len(val), 10)
        self.assertEqual(len(train), 8)

    def test_save_openai_format(self):
        for i in range(5):
            self.builder.add_example(
                TrainingExample(instruction="inst", input=f"inp{i}", output="콘텐츠" * 10)
            )
        path = os.path.join(self.tmpdir, "dataset.jsonl")
        result = self.builder.save(path, fmt="openai", split_train_val=False)
        self.assertEqual(result["total"], 5)
        self.assertTrue(os.path.exists(path))

    def test_save_with_split(self):
        for i in range(10):
            self.builder.add_example(
                TrainingExample(instruction="inst", input=f"inp{i}", output="콘텐츠" * 10)
            )
        path = os.path.join(self.tmpdir, "dataset.jsonl")
        result = self.builder.save(path, fmt="alpaca", split_train_val=True, train_ratio=0.8)
        self.assertIn("train", result)
        self.assertIn("val", result)
        self.assertEqual(result["train"] + result["val"], 10)

    def test_get_stats_empty(self):
        stats = self.builder.get_stats()
        self.assertEqual(stats, {"total": 0})

    def test_get_stats_with_data(self):
        self.builder.add_example(
            TrainingExample(instruction="", input="", output="a" * 50,
                            metadata={"style_id": "blog_seo"})
        )
        self.builder.add_example(
            TrainingExample(instruction="", input="", output="b" * 100,
                            metadata={"style_id": "summary"})
        )
        stats = self.builder.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertIn("blog_seo", stats["styles"])
        self.assertIn("summary", stats["styles"])


if __name__ == "__main__":
    unittest.main()
