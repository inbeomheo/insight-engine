"""멀티에이전트 생성 파이프라인의 비용 임대 경계 회귀 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from services.agents.orchestrator import Orchestrator
from services.usage.usage_lock import UsageLockUnavailable


@patch("services.agents.orchestrator.SEOAgent")
@patch("services.agents.orchestrator.EditorAgent")
@patch("services.agents.orchestrator.WriterAgent")
@patch("services.agents.orchestrator.ResearchAgent")
def test_orchestrator_passes_trusted_callback_to_every_agent(
    research_cls,
    writer_cls,
    editor_cls,
    seo_cls,
):
    callback = MagicMock()

    Orchestrator(model="chatmock/gpt-5.4-mini", on_cost_start=callback)

    for agent_cls in (research_cls, writer_cls, editor_cls, seo_cls):
        agent_cls.assert_called_once_with(
            model="chatmock/gpt-5.4-mini",
            on_cost_start=callback,
        )


def test_orchestrator_does_not_swallow_usage_lock_loss():
    orchestrator = Orchestrator(
        model="chatmock/gpt-5.4-mini",
        on_cost_start=MagicMock(),
    )
    orchestrator._research.execute = MagicMock(
        side_effect=UsageLockUnavailable("lease lost")
    )
    orchestrator._writer.execute = MagicMock()

    with pytest.raises(UsageLockUnavailable):
        orchestrator.run(
            transcript="충분한 자막",
            style="summary",
            style_prompt="요약",
        )

    orchestrator._writer.execute.assert_not_called()


@pytest.mark.parametrize(
    ("agent_path", "context"),
    [
        (
            "services.agents.research_agent.ResearchAgent",
            {"transcript": "충분한 자막", "style": "summary"},
        ),
        (
            "services.agents.editor_agent.EditorAgent",
            {"draft": "# 초안\n본문", "summary": "요약"},
        ),
        (
            "services.agents.seo_agent.SEOAgent",
            {
                "edited_content": "# 편집본\n본문",
                "title": "제목",
                "summary": "요약",
                "main_topic": "주제",
            },
        ),
    ],
)
def test_leaf_agent_does_not_convert_usage_lock_to_fallback(agent_path, context):
    module_path, class_name = agent_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    agent_class = getattr(module, class_name)
    agent = agent_class(model="chatmock/gpt-5.4-mini")

    with patch.object(
        agent,
        "_call_ai",
        side_effect=UsageLockUnavailable("lease lost"),
    ), pytest.raises(UsageLockUnavailable):
        agent.execute(context)
