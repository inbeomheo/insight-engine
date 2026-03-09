"""대량 수정 큐 서비스 테스트."""
import unittest
from services.bulk_review_queue_service import (
    queue_bulk_edits,
    apply_proposals,
    EditProposal,
)


class TestQueueBulkEdits(unittest.TestCase):
    """queue_bulk_edits 함수 테스트."""

    def test_empty_contents(self):
        """빈 목록 입력 시 빈 결과 반환."""
        result = queue_bulk_edits([])
        self.assertEqual(result, [])

    def test_blank_text_skipped(self):
        """빈 문자열 콘텐츠는 건너뛴다."""
        result = queue_bulk_edits([{'id': 'c1', 'text': ''}, {'id': 'c2', 'text': '   '}])
        self.assertEqual(result, [])

    def test_invalid_edit_type_raises(self):
        """지원하지 않는 edit_type은 ValueError."""
        with self.assertRaises(ValueError):
            queue_bulk_edits([{'id': 'c1', 'text': '테스트'}], edit_type='unknown')

    def test_seo_long_title(self):
        """SEO: 60자 초과 제목에 대한 수정 제안."""
        long_title = '가' * 80
        result = queue_bulk_edits([{'id': 'c1', 'text': long_title}], edit_type='seo')
        title_proposals = [p for p in result if '제목' in p.diff_summary]
        self.assertGreater(len(title_proposals), 0)

    def test_seo_short_title_no_proposal(self):
        """SEO: 60자 이내 제목은 제목 관련 제안 없음."""
        short_title = '좋은 제목입니다\nmeta description: 설명입니다'
        result = queue_bulk_edits([{'id': 'c1', 'text': short_title}], edit_type='seo')
        title_proposals = [p for p in result if '제목' in p.diff_summary and '초과' in p.diff_summary]
        self.assertEqual(len(title_proposals), 0)

    def test_seo_missing_meta_description(self):
        """SEO: 메타 설명 누락 시 추가 제안."""
        result = queue_bulk_edits([{'id': 'c1', 'text': '일반 콘텐츠입니다.'}], edit_type='seo')
        meta_proposals = [p for p in result if '메타' in p.diff_summary]
        self.assertGreater(len(meta_proposals), 0)

    def test_seo_with_meta_description(self):
        """SEO: 메타 설명이 있으면 관련 제안 없음."""
        text = '제목\nmeta description: 이 글은 테스트에 관한 내용입니다.'
        result = queue_bulk_edits([{'id': 'c1', 'text': text}], edit_type='seo')
        meta_proposals = [p for p in result if '메타' in p.diff_summary]
        self.assertEqual(len(meta_proposals), 0)

    def test_grammar_double_spaces(self):
        """문법: 이중 공백 탐지."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '이것은  이중  공백  테스트입니다.'}],
            edit_type='grammar',
        )
        space_proposals = [p for p in result if '이중 공백' in p.diff_summary]
        self.assertGreater(len(space_proposals), 0)

    def test_grammar_multi_periods(self):
        """문법: 과도한 말줄임표 정규화."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '그래서......결론은......'}],
            edit_type='grammar',
        )
        period_proposals = [p for p in result if '말줄임표' in p.diff_summary]
        self.assertGreater(len(period_proposals), 0)

    def test_grammar_parenthesis_mismatch(self):
        """문법: 괄호 불일치 탐지."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '(열린 괄호만 있고 닫힌 괄호가 없음'}],
            edit_type='grammar',
        )
        paren_proposals = [p for p in result if '괄호' in p.diff_summary]
        self.assertGreater(len(paren_proposals), 0)

    def test_grammar_balanced_parentheses(self):
        """문법: 괄호가 일치하면 관련 제안 없음."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '(정상) [괄호] {일치}'}],
            edit_type='grammar',
        )
        paren_proposals = [p for p in result if '괄호' in p.diff_summary]
        self.assertEqual(len(paren_proposals), 0)

    def test_style_excessive_exclamation(self):
        """스타일: 과도한 느낌표 탐지."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '대박!! 정말 좋아요!!'}],
            edit_type='style',
        )
        exclaim_proposals = [p for p in result if '느낌표' in p.diff_summary]
        self.assertGreater(len(exclaim_proposals), 0)

    def test_style_informal_expressions(self):
        """스타일: 비격식 표현(ㅋㅋ, ㅎㅎ 등) 탐지."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '정말 웃기다 ㅋㅋㅋ 대박 ㅎㅎㅎ'}],
            edit_type='style',
        )
        informal_proposals = [p for p in result if '비격식' in p.diff_summary]
        self.assertGreater(len(informal_proposals), 0)

    def test_compliance_price_without_condition(self):
        """규정: 가격 언급인데 조건 미표기."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '지금 50% 할인 중! 무료 체험 가능!'}],
            edit_type='compliance',
        )
        price_proposals = [p for p in result if '가격' in p.diff_summary or '할인' in p.diff_summary]
        self.assertGreater(len(price_proposals), 0)

    def test_compliance_absolute_guarantee(self):
        """규정: 절대적 보증 표현 탐지."""
        result = queue_bulk_edits(
            [{'id': 'c1', 'text': '100% 보장합니다. 절대 실패하지 않습니다.'}],
            edit_type='compliance',
        )
        guarantee_proposals = [p for p in result if '절대' in p.diff_summary or '보증' in p.diff_summary]
        self.assertGreater(len(guarantee_proposals), 0)

    def test_multiple_contents(self):
        """여러 콘텐츠 동시 처리."""
        contents = [
            {'id': 'c1', 'text': '가' * 100},
            {'id': 'c2', 'text': '나' * 100},
        ]
        result = queue_bulk_edits(contents, edit_type='seo')
        content_ids = {p.content_id for p in result}
        # 두 콘텐츠 모두 메타 설명 누락이므로 c1, c2 둘 다 포함
        self.assertIn('c1', content_ids)
        self.assertIn('c2', content_ids)

    def test_proposal_has_valid_fields(self):
        """EditProposal의 필드가 올바르게 채워지는지 확인."""
        result = queue_bulk_edits([{'id': 'c1', 'text': '일반 콘텐츠'}], edit_type='seo')
        for p in result:
            self.assertIsInstance(p, EditProposal)
            self.assertTrue(p.proposal_id)
            self.assertEqual(p.content_id, 'c1')
            self.assertEqual(p.edit_type, 'seo')
            self.assertGreaterEqual(p.confidence, 0.0)
            self.assertLessEqual(p.confidence, 1.0)

    def test_auto_generated_content_id(self):
        """id가 없는 콘텐츠에 자동 ID 부여."""
        result = queue_bulk_edits([{'text': '일반 콘텐츠'}], edit_type='seo')
        for p in result:
            self.assertTrue(p.content_id)  # 자동 생성된 ID


class TestApplyProposals(unittest.TestCase):
    """apply_proposals 함수 테스트."""

    def test_empty_proposals(self):
        """빈 제안 목록."""
        result = apply_proposals([], [])
        self.assertEqual(result, [])

    def test_apply_approved_only(self):
        """승인된 제안만 적용."""
        proposals = [
            EditProposal('p1', 'c1', '원본1', '수정1', 'seo', '요약1', 0.8),
            EditProposal('p2', 'c1', '원본2', '수정2', 'seo', '요약2', 0.6),
        ]
        result = apply_proposals(proposals, ['p1'])
        applied = [r for r in result if r['applied']]
        not_applied = [r for r in result if not r['applied']]
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]['result'], '수정1')
        self.assertEqual(len(not_applied), 1)
        self.assertEqual(not_applied[0]['result'], '원본2')

    def test_apply_none_approved(self):
        """승인된 제안이 없으면 모두 원본 유지."""
        proposals = [
            EditProposal('p1', 'c1', '원본', '수정', 'grammar', '요약', 0.7),
        ]
        result = apply_proposals(proposals, [])
        self.assertFalse(result[0]['applied'])
        self.assertEqual(result[0]['result'], '원본')

    def test_apply_all_approved(self):
        """모든 제안 승인 시 전부 적용."""
        proposals = [
            EditProposal('p1', 'c1', '원본1', '수정1', 'style', '요약1', 0.9),
            EditProposal('p2', 'c2', '원본2', '수정2', 'style', '요약2', 0.8),
        ]
        result = apply_proposals(proposals, ['p1', 'p2'])
        self.assertTrue(all(r['applied'] for r in result))

    def test_result_structure(self):
        """반환 결과 구조 확인."""
        proposals = [
            EditProposal('p1', 'c1', '원본', '수정', 'compliance', '요약', 0.5),
        ]
        result = apply_proposals(proposals, ['p1'])
        r = result[0]
        self.assertIn('proposal_id', r)
        self.assertIn('content_id', r)
        self.assertIn('edit_type', r)
        self.assertIn('applied', r)
        self.assertIn('result', r)
        self.assertIn('diff_summary', r)


if __name__ == '__main__':
    unittest.main()
