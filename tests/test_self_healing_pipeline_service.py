"""자가복구 파이프라인 서비스 테스트."""

import unittest
from services.self_healing_pipeline_service import (
    HealingAction,
    HealingPolicy,
    create_policy,
    diagnose_failure,
    plan_healing,
    apply_healing,
    is_recoverable,
)


class TestCreatePolicy(unittest.TestCase):
    """복구 정책 생성 테스트."""

    def test_create_policy_basic(self):
        """기본 정책 생성."""
        rules = [
            {"error_type": "timeout", "action_type": "retry", "max_retries": 3},
        ]
        policy = create_policy(rules)
        self.assertTrue(policy.policy_id)
        self.assertEqual(len(policy.rules), 1)
        self.assertEqual(policy.rules[0]["error_type"], "timeout")

    def test_create_policy_multiple_rules(self):
        """다중 규칙 정책."""
        rules = [
            {"error_type": "timeout", "action_type": "retry", "max_retries": 3},
            {"error_type": "invalid_input", "action_type": "skip", "max_retries": 0},
            {"error_type": "resource", "action_type": "fallback", "max_retries": 2},
        ]
        policy = create_policy(rules)
        self.assertEqual(len(policy.rules), 3)

    def test_create_policy_empty(self):
        """빈 규칙 정책."""
        policy = create_policy([])
        self.assertEqual(len(policy.rules), 0)


class TestDiagnoseFailure(unittest.TestCase):
    """에러 유형 분류 테스트."""

    def test_diagnose_timeout(self):
        """타임아웃 에러 감지."""
        result = diagnose_failure("s1", "Request timed out after 30s")
        self.assertEqual(result, "timeout")

    def test_diagnose_timeout_korean(self):
        """한국어 시간 초과 에러."""
        result = diagnose_failure("s1", "요청 시간 초과 발생")
        self.assertEqual(result, "timeout")

    def test_diagnose_invalid_input(self):
        """입력 오류 감지."""
        result = diagnose_failure("s1", "Invalid JSON format received")
        self.assertEqual(result, "invalid_input")

    def test_diagnose_resource(self):
        """리소스 에러 감지."""
        result = diagnose_failure("s1", "Out of memory: cannot allocate")
        self.assertEqual(result, "resource")

    def test_diagnose_unknown(self):
        """분류 불가 에러 → unknown."""
        result = diagnose_failure("s1", "Something went wrong")
        self.assertEqual(result, "unknown")

    def test_diagnose_case_insensitive(self):
        """대소문자 무관 매칭."""
        result = diagnose_failure("s1", "TIMEOUT ERROR")
        self.assertEqual(result, "timeout")

    def test_diagnose_validation_error(self):
        """validation 키워드 감지."""
        result = diagnose_failure("s1", "Validation failed for field X")
        self.assertEqual(result, "invalid_input")

    def test_diagnose_korean_resource(self):
        """한국어 리소스 에러."""
        result = diagnose_failure("s1", "메모리 부족으로 실패")
        self.assertEqual(result, "resource")


class TestPlanHealing(unittest.TestCase):
    """복구 계획 수립 테스트."""

    def setUp(self):
        self.policy = create_policy([
            {"error_type": "timeout", "action_type": "retry", "max_retries": 3},
            {"error_type": "invalid_input", "action_type": "skip", "max_retries": 0},
            {"error_type": "resource", "action_type": "fallback", "max_retries": 2},
        ])

    def test_plan_timeout_retry(self):
        """타임아웃 → retry 액션."""
        action = plan_healing(self.policy, "timeout")
        self.assertEqual(action.action_type, "retry")
        self.assertEqual(action.max_retries, 3)

    def test_plan_invalid_input_skip(self):
        """입력 오류 → skip."""
        action = plan_healing(self.policy, "invalid_input")
        self.assertEqual(action.action_type, "skip")

    def test_plan_resource_fallback(self):
        """리소스 에러 → fallback."""
        action = plan_healing(self.policy, "resource")
        self.assertEqual(action.action_type, "fallback")
        self.assertEqual(action.max_retries, 2)

    def test_plan_unknown_default_skip(self):
        """매칭 규칙 없음 → 기본 skip."""
        action = plan_healing(self.policy, "unknown")
        self.assertEqual(action.action_type, "skip")
        self.assertEqual(action.max_retries, 0)


class TestApplyHealing(unittest.TestCase):
    """복구 실행 테스트."""

    def test_apply_increments_attempt(self):
        """attempt 증가."""
        action = HealingAction("a1", "s1", "retry", 3, 0, "pending")
        result = apply_healing(action)
        self.assertEqual(result.current_attempt, 1)

    def test_apply_exhausted_at_max(self):
        """최대 재시도 도달 시 exhausted."""
        action = HealingAction("a1", "s1", "retry", 2, 1, "pending")
        result = apply_healing(action)
        self.assertEqual(result.current_attempt, 2)
        self.assertEqual(result.status, "exhausted")

    def test_apply_in_progress_before_max(self):
        """최대 미도달 시 in_progress."""
        action = HealingAction("a1", "s1", "retry", 5, 0, "pending")
        result = apply_healing(action)
        self.assertEqual(result.status, "in_progress")
        self.assertEqual(result.current_attempt, 1)


class TestIsRecoverable(unittest.TestCase):
    """재시도 가능 여부 테스트."""

    def test_recoverable_retry(self):
        """retry 타입 + 잔여 횟수 → True."""
        action = HealingAction("a1", "s1", "retry", 3, 1, "in_progress")
        self.assertTrue(is_recoverable(action))

    def test_not_recoverable_skip(self):
        """skip 타입 → False."""
        action = HealingAction("a1", "s1", "skip", 0, 0, "pending")
        self.assertFalse(is_recoverable(action))

    def test_not_recoverable_exhausted(self):
        """exhausted 상태 → False."""
        action = HealingAction("a1", "s1", "retry", 3, 3, "exhausted")
        self.assertFalse(is_recoverable(action))

    def test_not_recoverable_at_max(self):
        """max_retries 도달 → False."""
        action = HealingAction("a1", "s1", "retry", 2, 2, "in_progress")
        self.assertFalse(is_recoverable(action))

    def test_recoverable_fallback(self):
        """fallback 타입 + 잔여 횟수 → True."""
        action = HealingAction("a1", "s1", "fallback", 2, 0, "pending")
        self.assertTrue(is_recoverable(action))


if __name__ == "__main__":
    unittest.main()
