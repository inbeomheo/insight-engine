"""오케스트레이터 파이프라인 서비스 테스트."""

import unittest
from services.orchestrator_pipeline_service import (
    PipelineStep,
    Pipeline,
    create_pipeline,
    get_executable_steps,
    execute_step,
    synthesize_results,
    get_pipeline_status,
)


class TestCreatePipeline(unittest.TestCase):
    """파이프라인 생성 테스트."""

    def test_create_pipeline_basic(self):
        """기본 파이프라인 생성."""
        config = [
            {"name": "기획", "step_type": "plan"},
            {"name": "실행", "step_type": "parallel"},
        ]
        pipeline = create_pipeline(config)
        self.assertEqual(len(pipeline.steps), 2)
        self.assertTrue(pipeline.pipeline_id)
        self.assertTrue(pipeline.created_at)

    def test_create_pipeline_with_dependencies(self):
        """의존성 포함 파이프라인 생성."""
        config = [
            {"step_id": "s1", "name": "기획", "step_type": "plan"},
            {"step_id": "s2", "name": "실행A", "step_type": "parallel", "dependencies": ["s1"]},
            {"step_id": "s3", "name": "합성", "step_type": "synthesize", "dependencies": ["s2"]},
        ]
        pipeline = create_pipeline(config)
        self.assertEqual(pipeline.steps[1].dependencies, ["s1"])
        self.assertEqual(pipeline.steps[2].dependencies, ["s2"])

    def test_create_pipeline_empty(self):
        """빈 설정으로 파이프라인 생성."""
        pipeline = create_pipeline([])
        self.assertEqual(len(pipeline.steps), 0)

    def test_all_steps_start_pending(self):
        """모든 단계가 pending 상태로 시작."""
        config = [{"name": f"step{i}", "step_type": "plan"} for i in range(5)]
        pipeline = create_pipeline(config)
        for step in pipeline.steps:
            self.assertEqual(step.status, "pending")
            self.assertEqual(step.result, "")


class TestGetExecutableSteps(unittest.TestCase):
    """실행 가능 단계 조회 테스트."""

    def test_no_dependencies_all_executable(self):
        """의존성 없는 단계는 모두 실행 가능."""
        config = [
            {"step_id": "s1", "name": "A", "step_type": "parallel"},
            {"step_id": "s2", "name": "B", "step_type": "parallel"},
        ]
        pipeline = create_pipeline(config)
        executable = get_executable_steps(pipeline)
        self.assertEqual(len(executable), 2)

    def test_dependency_blocks_execution(self):
        """의존성 미충족 단계는 실행 불가."""
        config = [
            {"step_id": "s1", "name": "기획", "step_type": "plan"},
            {"step_id": "s2", "name": "실행", "step_type": "parallel", "dependencies": ["s1"]},
        ]
        pipeline = create_pipeline(config)
        executable = get_executable_steps(pipeline)
        # s1만 실행 가능 (s2는 s1 완료 대기)
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0].step_id, "s1")

    def test_dependency_fulfilled(self):
        """의존성 충족 시 실행 가능."""
        config = [
            {"step_id": "s1", "name": "기획", "step_type": "plan"},
            {"step_id": "s2", "name": "실행", "step_type": "parallel", "dependencies": ["s1"]},
        ]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "기획 완료")
        executable = get_executable_steps(pipeline)
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0].step_id, "s2")

    def test_done_steps_not_executable(self):
        """완료된 단계는 실행 가능 목록에 포함 안 됨."""
        config = [{"step_id": "s1", "name": "A", "step_type": "plan"}]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "완료")
        executable = get_executable_steps(pipeline)
        self.assertEqual(len(executable), 0)

    def test_multiple_dependencies(self):
        """다중 의존성 — 모두 충족되어야 실행 가능."""
        config = [
            {"step_id": "s1", "name": "A", "step_type": "plan"},
            {"step_id": "s2", "name": "B", "step_type": "plan"},
            {"step_id": "s3", "name": "합성", "step_type": "synthesize", "dependencies": ["s1", "s2"]},
        ]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "A 완료")
        # s2 미완료 → s3 실행 불가
        executable = get_executable_steps(pipeline)
        ids = [s.step_id for s in executable]
        self.assertNotIn("s3", ids)
        self.assertIn("s2", ids)

        execute_step(pipeline, "s2", "B 완료")
        executable = get_executable_steps(pipeline)
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0].step_id, "s3")


class TestExecuteStep(unittest.TestCase):
    """단계 실행 테스트."""

    def test_execute_step_success(self):
        """단계 실행 완료 처리."""
        config = [{"step_id": "s1", "name": "기획", "step_type": "plan"}]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "기획 결과")
        self.assertEqual(pipeline.steps[0].status, "done")
        self.assertEqual(pipeline.steps[0].result, "기획 결과")

    def test_execute_step_invalid_id(self):
        """존재하지 않는 step_id → ValueError."""
        config = [{"step_id": "s1", "name": "A", "step_type": "plan"}]
        pipeline = create_pipeline(config)
        with self.assertRaises(ValueError):
            execute_step(pipeline, "nonexistent", "결과")


class TestSynthesizeResults(unittest.TestCase):
    """결과 합성 테스트."""

    def test_synthesize_done_steps(self):
        """완료된 단계 결과만 합성."""
        config = [
            {"step_id": "s1", "name": "기획", "step_type": "plan"},
            {"step_id": "s2", "name": "실행", "step_type": "parallel"},
        ]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "기획 데이터")
        result = synthesize_results(pipeline)
        self.assertIn("[기획]", result)
        self.assertIn("기획 데이터", result)
        self.assertNotIn("[실행]", result)

    def test_synthesize_all_done(self):
        """모든 단계 완료 시 전체 합성."""
        config = [
            {"step_id": "s1", "name": "A", "step_type": "plan"},
            {"step_id": "s2", "name": "B", "step_type": "parallel"},
        ]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "결과A")
        execute_step(pipeline, "s2", "결과B")
        result = synthesize_results(pipeline)
        self.assertIn("[A] 결과A", result)
        self.assertIn("[B] 결과B", result)

    def test_synthesize_empty(self):
        """완료된 단계 없으면 빈 문자열."""
        pipeline = create_pipeline([{"step_id": "s1", "name": "A", "step_type": "plan"}])
        self.assertEqual(synthesize_results(pipeline), "")


class TestGetPipelineStatus(unittest.TestCase):
    """파이프라인 상태 조회 테스트."""

    def test_status_initial(self):
        """초기 상태: 모두 pending."""
        config = [
            {"step_id": "s1", "name": "A", "step_type": "plan"},
            {"step_id": "s2", "name": "B", "step_type": "plan"},
        ]
        pipeline = create_pipeline(config)
        status = get_pipeline_status(pipeline)
        self.assertEqual(status["total"], 2)
        self.assertEqual(status["done"], 0)
        self.assertEqual(status["progress_pct"], 0.0)

    def test_status_partial(self):
        """일부 완료 시 진행률."""
        config = [
            {"step_id": "s1", "name": "A", "step_type": "plan"},
            {"step_id": "s2", "name": "B", "step_type": "plan"},
            {"step_id": "s3", "name": "C", "step_type": "plan"},
            {"step_id": "s4", "name": "D", "step_type": "plan"},
        ]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "완료")
        status = get_pipeline_status(pipeline)
        self.assertEqual(status["done"], 1)
        self.assertEqual(status["progress_pct"], 25.0)

    def test_status_all_done(self):
        """전체 완료 시 100%."""
        config = [{"step_id": "s1", "name": "A", "step_type": "plan"}]
        pipeline = create_pipeline(config)
        execute_step(pipeline, "s1", "완료")
        status = get_pipeline_status(pipeline)
        self.assertEqual(status["progress_pct"], 100.0)

    def test_status_empty_pipeline(self):
        """빈 파이프라인."""
        pipeline = create_pipeline([])
        status = get_pipeline_status(pipeline)
        self.assertEqual(status["total"], 0)
        self.assertEqual(status["progress_pct"], 0.0)

    def test_status_with_failed(self):
        """실패 단계 카운트."""
        config = [{"step_id": "s1", "name": "A", "step_type": "plan"}]
        pipeline = create_pipeline(config)
        pipeline.steps[0].status = "failed"
        status = get_pipeline_status(pipeline)
        self.assertEqual(status["failed"], 1)


if __name__ == "__main__":
    unittest.main()
