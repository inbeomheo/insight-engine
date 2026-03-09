"""
보이스 파인튜닝 서비스 테스트
"""
import pytest
from services.voice_finetune_service import (
    FinetuneResult,
    finetune_voice,
    _determine_model_size,
    _calculate_training_steps,
    _estimate_quality,
    _determine_status,
)


class TestFinetuneVoice:
    """finetune_voice 함수 테스트"""

    def test_기본_파인튜닝_성공(self):
        """기본 파라미터로 파인튜닝 결과 반환"""
        result = finetune_voice("따뜻하고 부드러운 여성 목소리")
        assert isinstance(result, FinetuneResult)
        assert result.finetune_id
        assert result.status == "completed"
        assert result.estimated_quality > 0
        assert result.training_steps > 0
        assert result.model_size
        assert result.created_at

    def test_빈_설명_에러(self):
        """빈 설명은 ValueError 발생"""
        with pytest.raises(ValueError, match="오디오 설명이 필요합니다"):
            finetune_voice("")

    def test_None_설명_에러(self):
        """None은 ValueError 발생"""
        with pytest.raises(ValueError):
            finetune_voice(None)

    def test_공백_설명_에러(self):
        """공백만 있는 설명은 ValueError 발생"""
        with pytest.raises(ValueError):
            finetune_voice("   ")

    def test_커스텀_파라미터_적용(self):
        """training_params가 적용되는지 확인"""
        result = finetune_voice("테스트", training_params={
            "epochs": 200,
            "learning_rate": 0.0005,
            "batch_size": 16,
        })
        assert result.status == "completed"
        assert result.training_steps > 0

    def test_높은_학습률_실패(self):
        """학습률 > 0.1이면 failed 상태"""
        result = finetune_voice("테스트", training_params={
            "learning_rate": 0.5,
        })
        assert result.status == "failed"
        assert result.estimated_quality == 0.0

    def test_적은_에폭_training_상태(self):
        """에폭 < 10이면 training 상태"""
        result = finetune_voice("테스트", training_params={"epochs": 5})
        assert result.status == "training"

    def test_에폭_0_pending_상태(self):
        """에폭 0이면 pending 상태"""
        result = finetune_voice("테스트", training_params={"epochs": 0})
        assert result.status == "pending"

    def test_finetune_id_유니크(self):
        """두 번 호출 시 finetune_id가 다름"""
        r1 = finetune_voice("테스트1")
        r2 = finetune_voice("테스트2")
        assert r1.finetune_id != r2.finetune_id

    def test_알수없는_파라미터_무시(self):
        """알 수 없는 파라미터는 무시됨"""
        result = finetune_voice("테스트", training_params={
            "unknown_param": 999,
            "epochs": 100,
        })
        assert result.status == "completed"

    def test_긴_설명_높은_품질(self):
        """긴 설명이 짧은 설명보다 품질이 높음"""
        r_short = finetune_voice("짧음")
        r_long = finetune_voice("매우 상세하고 구체적인 오디오 특성 설명으로 깊고 따뜻한 톤의 중년 남성 목소리를 파인튜닝합니다")
        assert r_long.estimated_quality >= r_short.estimated_quality


class TestDetermineModelSize:
    """_determine_model_size 함수 테스트"""

    def test_large_모델(self):
        """에폭 500 이상이면 large"""
        assert _determine_model_size(500) == "large"
        assert _determine_model_size(1000) == "large"

    def test_medium_모델(self):
        """에폭 200~499이면 medium"""
        assert _determine_model_size(200) == "medium"
        assert _determine_model_size(499) == "medium"

    def test_small_모델(self):
        """에폭 200 미만이면 small"""
        assert _determine_model_size(100) == "small"
        assert _determine_model_size(1) == "small"

    def test_0_에폭_small(self):
        """에폭 0이면 small"""
        assert _determine_model_size(0) == "small"


class TestCalculateTrainingSteps:
    """_calculate_training_steps 함수 테스트"""

    def test_기본_계산(self):
        """100 에폭 × (100/8) = 1200 스텝"""
        steps = _calculate_training_steps(100, 8)
        assert steps == 100 * (100 // 8)

    def test_큰_배치_적은_스텝(self):
        """배치 크기가 크면 스텝이 적음"""
        s_small = _calculate_training_steps(100, 4)
        s_large = _calculate_training_steps(100, 32)
        assert s_small > s_large

    def test_0_에폭_0_스텝(self):
        """에폭 0이면 스텝 0"""
        assert _calculate_training_steps(0, 8) == 0


class TestEstimateQuality:
    """_estimate_quality 함수 테스트"""

    def test_기본_품질_범위(self):
        """기본 파라미터로 0~100 범위"""
        quality = _estimate_quality("테스트", 100, 0.001, 8)
        assert 0.0 <= quality <= 100.0

    def test_높은_에폭_높은_품질(self):
        """에폭이 많으면 품질이 높음"""
        q_low = _estimate_quality("테스트", 10, 0.001, 8)
        q_high = _estimate_quality("테스트", 400, 0.001, 8)
        assert q_high >= q_low

    def test_높은_학습률_페널티(self):
        """학습률 > 0.01이면 품질 페널티"""
        q_normal = _estimate_quality("테스트", 100, 0.001, 8)
        q_high_lr = _estimate_quality("테스트", 100, 0.05, 8)
        assert q_normal > q_high_lr

    def test_낮은_학습률_보너스(self):
        """학습률 <= 0.0001이면 품질 보너스"""
        q_normal = _estimate_quality("테스트", 100, 0.001, 8)
        q_low_lr = _estimate_quality("테스트", 100, 0.0001, 8)
        assert q_low_lr >= q_normal

    def test_큰_배치_보너스(self):
        """배치 >= 16이면 품질 보너스"""
        q_small = _estimate_quality("테스트", 100, 0.001, 8)
        q_large = _estimate_quality("테스트", 100, 0.001, 16)
        assert q_large >= q_small

    def test_최대_100_제한(self):
        """품질은 100을 초과하지 않음"""
        quality = _estimate_quality("아" * 5000, 1000, 0.0001, 64)
        assert quality <= 100.0


class TestDetermineStatus:
    """_determine_status 함수 테스트"""

    def test_completed(self):
        """에폭 >= 10, 적절한 학습률이면 completed"""
        assert _determine_status(100, 0.001) == "completed"

    def test_training(self):
        """에폭 1~9이면 training"""
        assert _determine_status(5, 0.001) == "training"

    def test_pending(self):
        """에폭 <= 0이면 pending"""
        assert _determine_status(0, 0.001) == "pending"

    def test_failed(self):
        """학습률 > 0.1이면 failed"""
        assert _determine_status(100, 0.5) == "failed"

    def test_경계값_에폭_10(self):
        """에폭 정확히 10이면 completed"""
        assert _determine_status(10, 0.001) == "completed"

    def test_경계값_lr_0_1(self):
        """학습률 정확히 0.1이면 failed 아님"""
        assert _determine_status(100, 0.1) != "failed"
