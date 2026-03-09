"""커뮤니티 배심원 서비스 테스트"""

import unittest
from services.community_jury_service import (
    JuryVote, JuryVerdict,
    cast_vote, tally_votes, calculate_consensus, get_minority_opinions,
    VALID_VERDICTS,
)


class TestCastVote(unittest.TestCase):
    """cast_vote 테스트"""

    def test_cast_basic(self):
        """기본 투표"""
        vote = cast_vote("juror1", "content1", "approve", 0.8, "좋습니다")
        self.assertTrue(vote.vote_id.startswith("vote_"))
        self.assertEqual(vote.juror_id, "juror1")
        self.assertEqual(vote.content_id, "content1")
        self.assertEqual(vote.verdict, "approve")
        self.assertEqual(vote.score, 0.8)

    def test_invalid_verdict_raises(self):
        """유효하지 않은 판정은 ValueError"""
        with self.assertRaises(ValueError):
            cast_vote("j1", "c1", "invalid", 0.5)

    def test_score_out_of_range_raises(self):
        """점수 범위 초과는 ValueError"""
        with self.assertRaises(ValueError):
            cast_vote("j1", "c1", "approve", 1.5)
        with self.assertRaises(ValueError):
            cast_vote("j1", "c1", "approve", -0.1)

    def test_boundary_scores(self):
        """경계값 점수"""
        v0 = cast_vote("j1", "c1", "approve", 0.0)
        v1 = cast_vote("j2", "c1", "approve", 1.0)
        self.assertEqual(v0.score, 0.0)
        self.assertEqual(v1.score, 1.0)

    def test_all_verdict_types(self):
        """모든 판정 타입"""
        for verdict in VALID_VERDICTS:
            vote = cast_vote("j1", "c1", verdict, 0.5)
            self.assertEqual(vote.verdict, verdict)


class TestCalculateConsensus(unittest.TestCase):
    """calculate_consensus 테스트"""

    def test_unanimous_approve(self):
        """만장일치 찬성 → 1.0"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "approve", 0.8),
            cast_vote("j3", "c1", "approve", 0.7),
        ]
        self.assertEqual(calculate_consensus(votes), 1.0)

    def test_split_votes(self):
        """분산 투표"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "reject", 0.3),
            cast_vote("j3", "c1", "revise", 0.5),
        ]
        consensus = calculate_consensus(votes)
        self.assertAlmostEqual(consensus, 1 / 3, places=2)

    def test_empty_votes(self):
        """빈 투표"""
        self.assertEqual(calculate_consensus([]), 0.0)


class TestTallyVotes(unittest.TestCase):
    """tally_votes 테스트"""

    def test_majority_approve(self):
        """과반수 찬성"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "approve", 0.8),
            cast_vote("j3", "c1", "reject", 0.3),
        ]
        verdict = tally_votes(votes)
        self.assertEqual(verdict.final_verdict, "approve")
        self.assertEqual(verdict.approve_count, 2)
        self.assertEqual(verdict.reject_count, 1)

    def test_majority_reject(self):
        """과반수 거부"""
        votes = [
            cast_vote("j1", "c1", "reject", 0.2),
            cast_vote("j2", "c1", "reject", 0.1),
            cast_vote("j3", "c1", "approve", 0.8),
        ]
        verdict = tally_votes(votes)
        self.assertEqual(verdict.final_verdict, "reject")

    def test_tie_defaults_to_revise(self):
        """동률 시 revise"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.8),
            cast_vote("j2", "c1", "reject", 0.3),
        ]
        verdict = tally_votes(votes)
        self.assertEqual(verdict.final_verdict, "revise")

    def test_avg_score_calculated(self):
        """평균 점수 계산"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.8),
            cast_vote("j2", "c1", "approve", 0.6),
        ]
        verdict = tally_votes(votes)
        self.assertAlmostEqual(verdict.avg_score, 0.7, places=2)

    def test_empty_votes_tally(self):
        """빈 투표 집계"""
        verdict = tally_votes([])
        self.assertEqual(verdict.total_votes, 0)
        self.assertEqual(verdict.final_verdict, "revise")

    def test_total_votes_counted(self):
        """총 투표 수"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "reject", 0.3),
            cast_vote("j3", "c1", "revise", 0.5),
        ]
        verdict = tally_votes(votes)
        self.assertEqual(verdict.total_votes, 3)

    def test_consensus_level_in_verdict(self):
        """합의 수준 포함"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "approve", 0.8),
        ]
        verdict = tally_votes(votes)
        self.assertEqual(verdict.consensus_level, 1.0)


class TestGetMinorityOpinions(unittest.TestCase):
    """get_minority_opinions 테스트"""

    def test_minority_extracted(self):
        """소수 의견 추출"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "approve", 0.8),
            cast_vote("j3", "c1", "reject", 0.3),
        ]
        minority = get_minority_opinions(votes, "approve")
        self.assertEqual(len(minority), 1)
        self.assertEqual(minority[0].verdict, "reject")

    def test_no_minority(self):
        """소수 의견 없음 (만장일치)"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "approve", 0.8),
        ]
        minority = get_minority_opinions(votes, "approve")
        self.assertEqual(len(minority), 0)

    def test_all_minority(self):
        """전부 소수 의견 (판정이 다른 경우)"""
        votes = [
            cast_vote("j1", "c1", "approve", 0.9),
            cast_vote("j2", "c1", "reject", 0.3),
        ]
        minority = get_minority_opinions(votes, "revise")
        self.assertEqual(len(minority), 2)

    def test_empty_votes(self):
        """빈 투표"""
        minority = get_minority_opinions([], "approve")
        self.assertEqual(len(minority), 0)


if __name__ == "__main__":
    unittest.main()
