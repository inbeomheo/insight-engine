"""
행동 기반 세그먼트 서비스 테스트

segment_by_behavior() 함수의 세그먼트 분류, 참여도 계산,
이탈 위험도 평가, 엣지 케이스를 검증합니다.
"""
import pytest

from services.behavioral_segment_service import (
    BehaviorSegment,
    segment_by_behavior,
)


class TestSegmentByBehavior:
    """segment_by_behavior 핵심 기능 테스트"""

    def test_empty_input_returns_empty(self):
        """빈 리스트 → 빈 결과"""
        result = segment_by_behavior([])
        assert result == []

    def test_none_input_returns_empty(self):
        """None 입력 → 빈 결과"""
        result = segment_by_behavior(None)
        assert result == []

    def test_single_user_single_action(self):
        """단일 사용자, 단일 액션"""
        actions = [{"user_id": "u1", "action": "view"}]
        result = segment_by_behavior(actions)
        assert len(result) == 1
        assert result[0].users == 1
        assert result[0].segment_name == "콘텐츠 소비자"

    def test_creator_segment(self):
        """생성 액션 → 콘텐츠 생산자 세그먼트"""
        actions = [
            {"user_id": "u1", "action": "generate"},
            {"user_id": "u1", "action": "create"},
            {"user_id": "u1", "action": "publish"},
        ]
        result = segment_by_behavior(actions)
        assert len(result) == 1
        assert result[0].segment_name == "콘텐츠 생산자"

    def test_consumer_segment(self):
        """소비 액션 → 콘텐츠 소비자 세그먼트"""
        actions = [
            {"user_id": "u1", "action": "view"},
            {"user_id": "u1", "action": "read"},
            {"user_id": "u1", "action": "download"},
        ]
        result = segment_by_behavior(actions)
        assert result[0].segment_name == "콘텐츠 소비자"

    def test_engager_segment(self):
        """참여 액션 → 적극 참여자 세그먼트"""
        actions = [
            {"user_id": "u1", "action": "like"},
            {"user_id": "u1", "action": "comment"},
            {"user_id": "u1", "action": "share"},
        ]
        result = segment_by_behavior(actions)
        assert result[0].segment_name == "적극 참여자"

    def test_multiple_segments(self):
        """여러 사용자가 다른 세그먼트로 분류"""
        actions = [
            {"user_id": "u1", "action": "generate"},
            {"user_id": "u1", "action": "create"},
            {"user_id": "u2", "action": "view"},
            {"user_id": "u2", "action": "read"},
            {"user_id": "u3", "action": "like"},
            {"user_id": "u3", "action": "share"},
        ]
        result = segment_by_behavior(actions)
        assert len(result) == 3
        names = {s.segment_name for s in result}
        assert "콘텐츠 생산자" in names
        assert "콘텐츠 소비자" in names
        assert "적극 참여자" in names

    def test_sorted_by_users_desc(self):
        """사용자 수 내림차순으로 정렬"""
        actions = [
            {"user_id": "u1", "action": "view"},
            {"user_id": "u2", "action": "view"},
            {"user_id": "u3", "action": "view"},
            {"user_id": "u4", "action": "generate"},
        ]
        result = segment_by_behavior(actions)
        assert result[0].users >= result[-1].users

    def test_engagement_score_range(self):
        """참여도 점수가 0~100 범위"""
        actions = [
            {"user_id": "u1", "action": "view"},
            {"user_id": "u1", "action": "like"},
            {"user_id": "u1", "action": "share"},
            {"user_id": "u1", "action": "generate"},
            {"user_id": "u1", "action": "comment"},
        ]
        result = segment_by_behavior(actions)
        for seg in result:
            assert 0 <= seg.avg_engagement <= 100

    def test_retention_risk_high(self):
        """액션 1개인 사용자 → 높은 이탈 위험"""
        actions = [{"user_id": "u1", "action": "view"}]
        result = segment_by_behavior(actions)
        assert result[0].retention_risk == "high"

    def test_retention_risk_low(self):
        """액션 많은 사용자 → 낮은 이탈 위험"""
        actions = [
            {"user_id": "u1", "action": "view"},
            {"user_id": "u1", "action": "read"},
            {"user_id": "u1", "action": "download"},
            {"user_id": "u1", "action": "view page"},
            {"user_id": "u1", "action": "read article"},
            {"user_id": "u1", "action": "view report"},
            {"user_id": "u1", "action": "download file"},
            {"user_id": "u1", "action": "watch video"},
        ]
        result = segment_by_behavior(actions)
        assert result[0].retention_risk == "low"

    def test_top_actions_populated(self):
        """상위 액션이 정상적으로 추출"""
        actions = [
            {"user_id": "u1", "action": "view"},
            {"user_id": "u1", "action": "view"},
            {"user_id": "u1", "action": "read"},
        ]
        result = segment_by_behavior(actions)
        assert len(result[0].top_actions) > 0
        assert "view" in result[0].top_actions

    def test_missing_user_id_skipped(self):
        """user_id 없는 항목 건너뛰기"""
        actions = [
            {"action": "view"},
            {"user_id": "", "action": "read"},
            {"user_id": "u1", "action": "generate"},
        ]
        result = segment_by_behavior(actions)
        assert len(result) == 1
        assert result[0].users == 1

    def test_unknown_action_category(self):
        """알 수 없는 액션 → 미분류 세그먼트"""
        actions = [
            {"user_id": "u1", "action": "xyz_unknown_action"},
            {"user_id": "u1", "action": "abc_random"},
        ]
        result = segment_by_behavior(actions)
        assert result[0].segment_name == "미분류"

    def test_dataclass_fields(self):
        """BehaviorSegment 필드 타입 검증"""
        actions = [{"user_id": "u1", "action": "view"}]
        result = segment_by_behavior(actions)
        seg = result[0]
        assert isinstance(seg.segment_name, str)
        assert isinstance(seg.users, int)
        assert isinstance(seg.avg_engagement, float)
        assert isinstance(seg.top_actions, list)
        assert seg.retention_risk in ("low", "medium", "high")

    def test_large_user_pool(self):
        """100명 이상의 사용자 처리"""
        actions = []
        for i in range(100):
            actions.append({"user_id": f"u{i}", "action": "view"})
            actions.append({"user_id": f"u{i}", "action": "read"})
        result = segment_by_behavior(actions)
        total_users = sum(s.users for s in result)
        assert total_users == 100
