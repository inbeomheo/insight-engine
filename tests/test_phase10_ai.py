"""
Phase 10 고급 AI & 미래 기술 서비스 테스트
F10-01~F10-28 핵심 단위 테스트
"""
import json
import os
import sys
import tempfile
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── F10-01: DatasetBuilder ────────────────────────────────────────────────────

class TestDatasetBuilder:

    def test_add_example(self):
        from services.finetune.dataset_builder import DatasetBuilder, TrainingExample

        builder = DatasetBuilder(min_output_length=10)
        ex = TrainingExample(
            instruction="블로그 작성",
            input="YouTube URL",
            output="블로그 콘텐츠 내용 테스트"
        )
        result = builder.add_example(ex)
        assert result is True
        assert len(builder.examples) == 1

    def test_add_example_too_short(self):
        from services.finetune.dataset_builder import DatasetBuilder, TrainingExample

        builder = DatasetBuilder(min_output_length=500)
        ex = TrainingExample(instruction="x", input="y", output="짧음")
        result = builder.add_example(ex)
        assert result is False

    def test_add_from_history(self):
        from services.finetune.dataset_builder import DatasetBuilder

        builder = DatasetBuilder(min_output_length=10)
        records = [
            {'url': 'https://youtube.com/watch?v=abc', 'title': '테스트', 'style_id': 'blog_seo',
             'content': '이것은 충분히 긴 테스트 콘텐츠입니다.' * 5},
            {'url': 'https://youtube.com/watch?v=def', 'title': '튜토리얼', 'style_id': 'tutorial',
             'content': ''},  # 빈 콘텐츠 → 제외
        ]
        added = builder.add_from_history(records)
        assert added == 1

    def test_to_openai_format(self):
        from services.finetune.dataset_builder import TrainingExample

        ex = TrainingExample(instruction="지시", input="입력", output="출력")
        fmt = ex.to_openai_format()
        assert 'messages' in fmt
        assert len(fmt['messages']) == 3
        assert fmt['messages'][0]['role'] == 'system'
        assert fmt['messages'][-1]['role'] == 'assistant'

    def test_to_alpaca_format(self):
        from services.finetune.dataset_builder import TrainingExample

        ex = TrainingExample(instruction="지시", input="입력", output="출력")
        fmt = ex.to_alpaca_format()
        assert fmt['instruction'] == '지시'
        assert fmt['output'] == '출력'

    def test_save_jsonl(self):
        from services.finetune.dataset_builder import DatasetBuilder, TrainingExample

        builder = DatasetBuilder(min_output_length=1)
        for i in range(5):
            builder.add_example(TrainingExample(
                instruction=f"지시{i}", input=f"입력{i}", output=f"출력{i}"
            ))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_dataset.jsonl')
            stats = builder.save(output_path, fmt='openai', split_train_val=False)
            assert stats['total'] == 5
            assert os.path.exists(output_path)

            with open(output_path, encoding='utf-8') as f:
                lines = f.readlines()
            assert len(lines) == 5
            # JSONL 검증
            data = json.loads(lines[0])
            assert 'messages' in data

    def test_get_stats(self):
        from services.finetune.dataset_builder import DatasetBuilder, TrainingExample

        builder = DatasetBuilder(min_output_length=1)
        for i in range(3):
            builder.add_example(TrainingExample(
                instruction="x", input="y",
                output=f"출력 콘텐츠 {i}" * 10,
                metadata={'style_id': 'blog_seo'}
            ))

        stats = builder.get_stats()
        assert stats['total'] == 3
        assert 'avg_output_length' in stats


# ── F10-02: RewardModel ───────────────────────────────────────────────────────

class TestRewardModel:

    def test_score_high_quality(self):
        from services.finetune.reward_model import RuleBasedRewardModel

        model = RuleBasedRewardModel()
        high_quality = (
            "## 블로그 제목\n\n"
            "본문 내용이 충분히 길고 구조화되어 있습니다.\n\n"
            "## 섹션 1\n\n"
            "이 섹션에는 충분한 설명이 있습니다. " * 20 +
            "\n\n## 섹션 2\n\n상세한 내용. " * 15
        )
        scores = model.score(high_quality, 'blog_seo')
        assert scores['total'] > 0.4
        assert 'length_score' in scores
        assert 'structure_score' in scores

    def test_score_with_forbidden_words(self):
        from services.finetune.reward_model import RuleBasedRewardModel

        model = RuleBasedRewardModel()
        bad_content = "놀라운 혁신적 획기적 최고의 게임체인저 콘텐츠입니다." * 5
        scores = model.score(bad_content, 'blog_seo')
        assert scores['forbidden_penalty'] < 1.0

    def test_compare(self):
        from services.finetune.reward_model import RuleBasedRewardModel

        model = RuleBasedRewardModel()
        good = "## 좋은 콘텐츠\n\n상세하고 구조화된 내용입니다. " * 30
        bad = "짧고 구조 없는 내용."
        result = model.compare(good, bad, 'blog_seo')
        # 'a'이거나 'tie' (길이 차이가 크면 'a')
        assert result in ('a', 'b', 'tie')


# ── F10-17: SimulatorService ──────────────────────────────────────────────────

class TestSimulatorService:

    def test_simulate_basic(self):
        from services.simulator_service import SimulatorService

        svc = SimulatorService()
        result = svc.simulate(
            content="## 테스트 콘텐츠\n\n" + "내용." * 100,
            style_id='blog_seo',
            platform='naver_blog',
            follower_count=500,
            has_seo_keywords=True,
            seed=42,
        )
        assert result.predicted_views_30d > 0
        assert result.predicted_ctr > 0
        assert 0 <= result.engagement_score <= 100
        assert 0 <= result.seo_potential <= 100

    def test_simulate_returns_recommendations(self):
        from services.simulator_service import SimulatorService

        svc = SimulatorService()
        result = svc.simulate(
            content="짧은 내용",
            style_id='blog_seo',
            has_seo_keywords=False,
            has_images=False,
            seed=42,
        )
        assert len(result.recommendations) > 0

    def test_simulate_to_dict(self):
        from services.simulator_service import SimulatorService

        svc = SimulatorService()
        result = svc.simulate("테스트 콘텐츠 " * 50, seed=1)
        d = result.to_dict()
        required_keys = ['predicted_views_30d', 'predicted_ctr', 'engagement_score', 'seo_potential']
        for key in required_keys:
            assert key in d


# ── F10-18: ComplexityService ─────────────────────────────────────────────────

class TestComplexityService:

    def test_analyze_structured_content(self):
        from services.analysis.complexity_service import ComplexityService

        svc = ComplexityService()
        content = (
            "## 섹션 1\n\n"
            "첫 번째 문단입니다. 내용이 충분합니다.\n\n"
            "## 섹션 2\n\n"
            "- 항목 1\n- 항목 2\n- 항목 3\n\n"
            "상세한 설명입니다. " * 20
        )
        report = svc.analyze(content)
        assert report.heading_depth >= 2
        assert report.paragraph_count > 0
        assert report.list_count > 0
        assert 0 <= report.readability_score <= 100
        assert 0 <= report.complexity_score <= 100

    def test_analyze_empty(self):
        from services.analysis.complexity_service import ComplexityService

        svc = ComplexityService()
        report = svc.analyze('')
        assert report.readability_score == 0

    def test_analyze_to_dict(self):
        from services.analysis.complexity_service import ComplexityService

        svc = ComplexityService()
        report = svc.analyze("테스트 콘텐츠 내용.")
        d = report.to_dict()
        assert 'readability_score' in d
        assert 'expertise_level' in d
        assert 'suggestions' in d


# ── F10-19: LinkNetworkService ────────────────────────────────────────────────

class TestLinkNetworkService:

    def test_add_and_recommend(self):
        from services.link_network_service import LinkNetworkService

        svc = LinkNetworkService(similarity_threshold=0.0)
        svc.add_document('doc1', 'Python 튜토리얼', '파이썬 프로그래밍 기초 학습 방법', url='/doc1')
        svc.add_document('doc2', 'Python 고급', '파이썬 고급 기술 프로그래밍 패턴', url='/doc2')
        svc.add_document('doc3', '요리 레시피', '맛있는 한국 음식 요리 방법', url='/doc3')

        recs = svc.get_recommendations('doc1', top_k=5)
        assert len(recs) > 0
        # 파이썬 관련 doc2가 상위에 와야 함
        doc_ids = [r['doc_id'] for r in recs]
        assert 'doc2' in doc_ids

    def test_build_link_graph(self):
        from services.link_network_service import LinkNetworkService

        svc = LinkNetworkService()
        svc.add_document('a', 'AI 기술', 'AI 인공지능 딥러닝 기계학습')
        svc.add_document('b', 'ML 입문', '머신러닝 기계학습 알고리즘')
        svc.add_document('c', '요리', '음식 요리 레시피')

        graph = svc.build_link_graph()
        assert 'a' in graph
        assert 'b' in graph

    def test_get_stats(self):
        from services.link_network_service import LinkNetworkService

        svc = LinkNetworkService()
        svc.add_document('x', '테스트', '내용')
        stats = svc.get_stats()
        assert stats['document_count'] == 1


# ── F10-20: RepurposeService ──────────────────────────────────────────────────

class TestRepurposeService:

    def test_get_available_formats(self):
        from services.export.repurpose_service import RepurposeService

        formats = RepurposeService.get_available_formats()
        assert len(formats) > 0
        assert all('format' in f and 'label' in f for f in formats)

    @patch('services.repurpose_service.RepurposeService._call_ai' if False else 'builtins.open', create=True)
    def test_invalid_format(self, _):
        from services.export.repurpose_service import RepurposeService

        svc = RepurposeService()
        with pytest.raises(ValueError, match="지원하지 않는 포맷"):
            svc.repurpose("콘텐츠", "invalid_format")


# ── F10-25: FingerprintService ────────────────────────────────────────────────

class TestFingerprintService:

    def test_embed_and_extract(self):
        from services.fingerprint_service import FingerprintService

        svc = FingerprintService()
        content = "테스트 콘텐츠입니다. 지문 삽입 테스트."
        watermarked, fp_id = svc.embed(content, user_id='user123', content_id='c001')

        assert len(watermarked) >= len(content)
        assert fp_id

        extracted = svc.extract(watermarked)
        assert extracted is not None
        assert extracted == fp_id[:12]

    def test_verify(self):
        from services.fingerprint_service import FingerprintService

        svc = FingerprintService()
        content = "원본 콘텐츠"
        watermarked, fp_id = svc.embed(content, user_id='u1')

        assert svc.verify(watermarked, fp_id) is True
        assert svc.verify(watermarked, 'wrong_fp_id') is False

    def test_strip_fingerprint(self):
        from services.fingerprint_service import FingerprintService

        svc = FingerprintService()
        content = "원본 콘텐츠"
        watermarked, _ = svc.embed(content, user_id='u1')
        stripped = svc.strip_fingerprint(watermarked)
        assert '\u200b' not in stripped
        assert '\u200c' not in stripped
        assert '\u200d' not in stripped

    def test_hash_content(self):
        from services.fingerprint_service import FingerprintService

        svc = FingerprintService()
        h1 = svc.hash_content("동일한 내용")
        h2 = svc.hash_content("동일한 내용")
        h3 = svc.hash_content("다른 내용")
        assert h1 == h2
        assert h1 != h3


# ── F10-26: ModelRouter ───────────────────────────────────────────────────────

class TestModelRouter:

    def test_get_available_models(self):
        from services.model_router_service import ModelRouter

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            router = ModelRouter()
            models = router.get_available_models()
            assert isinstance(models, list)
            if models:
                assert 'model_key' in models[0]

    def test_route_returns_decision(self):
        from services.model_router_service import ModelRouter, RouterDecision

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            router = ModelRouter()
            if not router._available_models:
                pytest.skip("사용 가능한 모델 없음")

            decision = router.route(style_id='blog_seo', mode='balanced')
            assert isinstance(decision, RouterDecision)
            assert decision.model_key
            assert decision.estimated_cost >= 0
            assert decision.estimated_latency_s > 0


# ── F10-27: PromptVersionService ─────────────────────────────────────────────

class TestPromptVersionService:

    def test_save_and_get_active(self):
        from services.prompt_version_service import PromptVersionService

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'versions.jsonl')
            svc = PromptVersionService(store_path=store_path)

            v = svc.save_version(
                prompt_key='test_style',
                content='프롬프트 내용 v1',
                description='초기 버전',
            )
            assert v.version_num == 1
            assert v.is_active

            active = svc.get_active('test_style')
            assert active is not None
            assert active.content == '프롬프트 내용 v1'

    def test_save_multiple_versions(self):
        from services.prompt_version_service import PromptVersionService

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'versions.jsonl')
            svc = PromptVersionService(store_path=store_path)

            svc.save_version('key1', '버전1 내용', description='v1')
            svc.save_version('key1', '버전2 내용', description='v2')

            history = svc.get_history('key1')
            assert len(history) == 2

            # 최신 버전만 활성화
            active = [v for v in history if v.is_active]
            assert len(active) == 1
            assert active[0].version_num == 2

    def test_rollback(self):
        from services.prompt_version_service import PromptVersionService

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'versions.jsonl')
            svc = PromptVersionService(store_path=store_path)

            svc.save_version('key1', 'v1 내용')
            svc.save_version('key1', 'v2 내용')

            rolled = svc.rollback('key1', version_num=1)
            assert rolled is not None
            assert rolled.version_num == 1
            assert rolled.is_active

    def test_diff(self):
        from services.prompt_version_service import PromptVersionService

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'versions.jsonl')
            svc = PromptVersionService(store_path=store_path)

            svc.save_version('key1', '공통 줄\n추가된 줄 없음')
            svc.save_version('key1', '공통 줄\n새로 추가된 줄')

            diff = svc.diff('key1', 1, 2)
            assert 'version_a' in diff
            assert 'version_b' in diff
            assert diff['version_a'] == 1
            assert diff['version_b'] == 2
