"""파이프라인 서비스 단위 테스트"""
import unittest
from unittest.mock import patch


class TestPipelineEngine(unittest.TestCase):
    """PipelineEngine 실행 로직 테스트"""

    def _make_engine(self, steps):
        """테스트용 PipelineEngine 생성"""
        from services.pipeline_service import PipelineEngine, PipelineConfig, PipelineStep
        config = PipelineConfig(
            id="test",
            name="테스트 파이프라인",
            steps=[
                PipelineStep(
                    id=s["id"],
                    name=s["name"],
                    description=s.get("description", ""),
                    handler=s["handler"],
                )
                for s in steps
            ],
        )
        return PipelineEngine(config)

    def test_three_step_execution(self):
        """3-스텝 파이프라인 정상 실행 시 이벤트 순서와 context 전파 확인"""
        def step_a(ctx):
            return {"a": 1}

        def step_b(ctx):
            return {"b": ctx.get("a", 0) + 1}

        def step_c(ctx):
            return {"c": ctx.get("b", 0) + 1}

        engine = self._make_engine([
            {"id": "a", "name": "스텝A", "handler": step_a},
            {"id": "b", "name": "스텝B", "handler": step_b},
            {"id": "c", "name": "스텝C", "handler": step_c},
        ])

        events = list(engine.execute({}))

        # 이벤트 순서: start, complete × 3 + pipeline_complete = 7
        self.assertEqual(len(events), 7)

        # 타입 순서 확인
        types = [e["type"] for e in events]
        self.assertEqual(types, [
            "step_start", "step_complete",
            "step_start", "step_complete",
            "step_start", "step_complete",
            "pipeline_complete",
        ])

        # context 전파 확인
        final = events[-1]["result"]
        self.assertEqual(final["a"], 1)
        self.assertEqual(final["b"], 2)
        self.assertEqual(final["c"], 3)

    def test_step_error_stops_pipeline(self):
        """스텝 에러 시 파이프라인이 즉시 중단되고 step_error 이벤트 발생"""
        call_log = []

        def step_ok(ctx):
            call_log.append("ok")
            return {"ok": True}

        def step_fail(ctx):
            call_log.append("fail")
            raise ValueError("의도된 에러")

        def step_after(ctx):
            call_log.append("after")
            return {}

        engine = self._make_engine([
            {"id": "ok", "name": "정상", "handler": step_ok},
            {"id": "fail", "name": "실패", "handler": step_fail},
            {"id": "after", "name": "이후", "handler": step_after},
        ])

        events = list(engine.execute({}))
        types = [e["type"] for e in events]

        # 에러 후 중단: start, complete, start, error
        self.assertEqual(types, [
            "step_start", "step_complete",
            "step_start", "step_error",
        ])

        # 에러 이벤트 내용 (클라이언트에는 일반화된 메시지 전달)
        error_event = events[-1]
        self.assertEqual(error_event["step"], "fail")
        self.assertIn("처리 중 오류가 발생했습니다", error_event["error"])
        # Fix 9: step_error에 progress 필드 포함
        self.assertIn("progress", error_event)

        # step_after는 실행되지 않음
        self.assertNotIn("after", call_log)

    def test_progress_values(self):
        """진행률(progress) 값이 올바르게 계산되는지 확인"""
        engine = self._make_engine([
            {"id": "a", "name": "A", "handler": lambda ctx: None},
            {"id": "b", "name": "B", "handler": lambda ctx: None},
            {"id": "c", "name": "C", "handler": lambda ctx: None},
            {"id": "d", "name": "D", "handler": lambda ctx: None},
        ])

        events = list(engine.execute({}))
        start_events = [e for e in events if e["type"] == "step_start"]
        complete_events = [e for e in events if e["type"] == "step_complete"]

        # start 이벤트 progress: 0/4, 1/4, 2/4, 3/4
        self.assertAlmostEqual(start_events[0]["progress"], 0.0)
        self.assertAlmostEqual(start_events[1]["progress"], 0.25)
        self.assertAlmostEqual(start_events[2]["progress"], 0.5)
        self.assertAlmostEqual(start_events[3]["progress"], 0.75)

        # complete 이벤트 progress: 1/4, 2/4, 3/4, 4/4
        self.assertAlmostEqual(complete_events[0]["progress"], 0.25)
        self.assertAlmostEqual(complete_events[1]["progress"], 0.5)
        self.assertAlmostEqual(complete_events[2]["progress"], 0.75)
        self.assertAlmostEqual(complete_events[3]["progress"], 1.0)

        # pipeline_complete progress
        final = events[-1]
        self.assertAlmostEqual(final["progress"], 1.0)

    def test_empty_pipeline(self):
        """스텝이 없는 파이프라인은 즉시 완료"""
        engine = self._make_engine([])
        events = list(engine.execute({"key": "value"}))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "pipeline_complete")
        self.assertEqual(events[0]["result"]["key"], "value")

    def test_handler_returning_none(self):
        """handler가 None을 반환해도 정상 동작"""
        engine = self._make_engine([
            {"id": "a", "name": "A", "handler": lambda ctx: None},
        ])

        events = list(engine.execute({"existing": True}))
        types = [e["type"] for e in events]

        self.assertEqual(types, ["step_start", "step_complete", "pipeline_complete"])
        # 기존 context 유지
        self.assertTrue(events[-1]["result"]["existing"])


class TestPresets(unittest.TestCase):
    """프리셋 파이프라인 설정 테스트"""

    def test_blog_automation_preset_exists(self):
        """blog_automation 프리셋이 존재하고 3개 스텝을 가짐"""
        from services.pipeline_service import PIPELINE_PRESETS

        self.assertIn("blog_automation", PIPELINE_PRESETS)
        config = PIPELINE_PRESETS["blog_automation"]
        self.assertEqual(config.id, "blog_automation")
        self.assertEqual(len(config.steps), 3)

    def test_blog_automation_step_ids(self):
        """blog_automation 프리셋의 스텝 ID가 올바른지 확인"""
        from services.pipeline_service import PIPELINE_PRESETS

        config = PIPELINE_PRESETS["blog_automation"]
        step_ids = [s.id for s in config.steps]
        self.assertEqual(step_ids, ["transcript", "generate", "seo"])

    def test_step_handlers_are_callable(self):
        """모든 프리셋 스텝의 handler가 호출 가능한지 확인"""
        from services.pipeline_service import PIPELINE_PRESETS

        for name, config in PIPELINE_PRESETS.items():
            for step in config.steps:
                self.assertTrue(
                    callable(step.handler),
                    f"프리셋 '{name}' 스텝 '{step.id}'의 handler가 callable이 아닙니다",
                )


class TestStepElapsed(unittest.TestCase):
    """step_complete 이벤트의 elapsed 필드 확인"""

    def test_step_complete_has_elapsed(self):
        """step_complete 이벤트에 elapsed 필드가 있는지 확인"""
        from services.pipeline_service import PipelineEngine, PipelineConfig, PipelineStep

        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[PipelineStep("s", "S", "Desc", lambda ctx: None)],
        )
        engine = PipelineEngine(config)
        events = list(engine.execute({}))

        complete = [e for e in events if e["type"] == "step_complete"]
        self.assertEqual(len(complete), 1)
        self.assertIn("elapsed", complete[0])
        self.assertIsInstance(complete[0]["elapsed"], float)


if __name__ == '__main__':
    unittest.main()
