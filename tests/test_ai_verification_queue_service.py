"""ai_verification_queue_service 단위 테스트"""
import unittest
from services.ai_verification_queue_service import (
    VerificationTicket,
    queue_for_verification,
    process_ticket,
    list_tickets,
    clear_store,
    _make_preview,
)


class TestVerificationTicketDataclass(unittest.TestCase):
    """VerificationTicket 데이터클래스 테스트"""

    def test_ticket_fields(self):
        """VerificationTicket 필드가 올바르게 생성된다"""
        ticket = VerificationTicket(
            ticket_id='t-1',
            content_id='c-1',
            content_preview='미리보기',
            status='pending',
            priority='high',
        )
        self.assertEqual(ticket.ticket_id, 't-1')
        self.assertEqual(ticket.content_id, 'c-1')
        self.assertEqual(ticket.status, 'pending')
        self.assertEqual(ticket.priority, 'high')

    def test_ticket_defaults(self):
        """VerificationTicket 기본값이 올바르다"""
        ticket = VerificationTicket(
            ticket_id='t-2', content_id='c-2', content_preview='p',
        )
        self.assertEqual(ticket.status, 'pending')
        self.assertEqual(ticket.priority, 'normal')
        self.assertEqual(ticket.reviewer, '')
        self.assertEqual(ticket.decided_at, '')


class TestMakePreview(unittest.TestCase):
    """_make_preview 내부 함수 테스트"""

    def test_short_content(self):
        """짧은 콘텐츠는 그대로 반환된다"""
        self.assertEqual(_make_preview('짧은 텍스트'), '짧은 텍스트')

    def test_long_content_truncated(self):
        """긴 콘텐츠는 200자 + '...'로 잘린다"""
        content = 'A' * 300
        preview = _make_preview(content)
        self.assertEqual(len(preview), 203)  # 200 + '...'
        self.assertTrue(preview.endswith('...'))

    def test_whitespace_stripped(self):
        """앞뒤 공백이 제거된다"""
        self.assertEqual(_make_preview('  공백  '), '공백')


class TestQueueForVerification(unittest.TestCase):
    """queue_for_verification 함수 테스트"""

    def setUp(self):
        clear_store()

    def test_basic_queue(self):
        """기본 티켓 생성이 동작한다"""
        ticket = queue_for_verification('c-1', '테스트 콘텐츠입니다')
        self.assertIsInstance(ticket, VerificationTicket)
        self.assertEqual(ticket.content_id, 'c-1')
        self.assertEqual(ticket.status, 'pending')
        self.assertEqual(ticket.priority, 'normal')
        self.assertTrue(len(ticket.ticket_id) > 0)
        self.assertTrue(len(ticket.created_at) > 0)

    def test_custom_priority(self):
        """우선순위를 지정할 수 있다"""
        ticket = queue_for_verification('c-2', '긴급 콘텐츠', priority='urgent')
        self.assertEqual(ticket.priority, 'urgent')

    def test_invalid_priority_raises(self):
        """유효하지 않은 priority는 ValueError"""
        with self.assertRaises(ValueError):
            queue_for_verification('c-3', '내용', priority='super_urgent')

    def test_empty_content_id_raises(self):
        """빈 content_id는 ValueError"""
        with self.assertRaises(ValueError):
            queue_for_verification('', '내용')

    def test_whitespace_content_id_raises(self):
        """공백 content_id는 ValueError"""
        with self.assertRaises(ValueError):
            queue_for_verification('   ', '내용')

    def test_preview_generated(self):
        """콘텐츠 미리보기가 생성된다"""
        long_content = 'B' * 500
        ticket = queue_for_verification('c-4', long_content)
        self.assertTrue(ticket.content_preview.endswith('...'))
        self.assertLessEqual(len(ticket.content_preview), 203)

    def test_unique_ticket_ids(self):
        """각 티켓은 고유한 ID를 가진다"""
        t1 = queue_for_verification('c-5', '내용1')
        t2 = queue_for_verification('c-6', '내용2')
        self.assertNotEqual(t1.ticket_id, t2.ticket_id)


class TestProcessTicket(unittest.TestCase):
    """process_ticket 함수 테스트"""

    def setUp(self):
        clear_store()

    def test_approve_ticket(self):
        """티켓을 승인할 수 있다"""
        ticket = queue_for_verification('c-1', '내용')
        result = process_ticket(ticket.ticket_id, 'approved', 'reviewer-A')
        self.assertEqual(result.status, 'approved')
        self.assertEqual(result.reviewer, 'reviewer-A')
        self.assertTrue(len(result.decided_at) > 0)

    def test_reject_ticket(self):
        """티켓을 반려할 수 있다"""
        ticket = queue_for_verification('c-2', '내용')
        result = process_ticket(ticket.ticket_id, 'rejected', 'reviewer-B')
        self.assertEqual(result.status, 'rejected')

    def test_needs_revision(self):
        """수정 요청을 할 수 있다"""
        ticket = queue_for_verification('c-3', '내용')
        result = process_ticket(ticket.ticket_id, 'needs_revision', 'reviewer-C')
        self.assertEqual(result.status, 'needs_revision')

    def test_nonexistent_ticket_raises(self):
        """존재하지 않는 티켓은 ValueError"""
        with self.assertRaises(ValueError):
            process_ticket('fake-id', 'approved', 'reviewer')

    def test_invalid_decision_raises(self):
        """유효하지 않은 decision은 ValueError"""
        ticket = queue_for_verification('c-4', '내용')
        with self.assertRaises(ValueError):
            process_ticket(ticket.ticket_id, 'maybe', 'reviewer')

    def test_empty_reviewer_raises(self):
        """빈 reviewer는 ValueError"""
        ticket = queue_for_verification('c-5', '내용')
        with self.assertRaises(ValueError):
            process_ticket(ticket.ticket_id, 'approved', '')

    def test_already_processed_raises(self):
        """이미 처리된 티켓을 다시 처리하면 RuntimeError"""
        ticket = queue_for_verification('c-6', '내용')
        process_ticket(ticket.ticket_id, 'approved', 'reviewer-1')
        with self.assertRaises(RuntimeError):
            process_ticket(ticket.ticket_id, 'rejected', 'reviewer-2')


class TestListTickets(unittest.TestCase):
    """list_tickets 함수 테스트"""

    def setUp(self):
        clear_store()

    def test_list_all(self):
        """전체 티켓 목록을 조회한다"""
        queue_for_verification('c-1', '내용1')
        queue_for_verification('c-2', '내용2')
        tickets = list_tickets()
        self.assertEqual(len(tickets), 2)

    def test_list_empty(self):
        """비어있는 저장소는 빈 리스트를 반환한다"""
        tickets = list_tickets()
        self.assertEqual(tickets, [])

    def test_filter_by_status(self):
        """상태별 필터링이 동작한다"""
        t1 = queue_for_verification('c-1', '내용1')
        queue_for_verification('c-2', '내용2')
        process_ticket(t1.ticket_id, 'approved', 'reviewer')

        pending = list_tickets(status='pending')
        self.assertEqual(len(pending), 1)

        approved = list_tickets(status='approved')
        self.assertEqual(len(approved), 1)

    def test_invalid_status_raises(self):
        """유효하지 않은 status는 ValueError"""
        with self.assertRaises(ValueError):
            list_tickets(status='unknown')

    def test_sorted_by_created_at_desc(self):
        """생성일 내림차순으로 정렬된다"""
        queue_for_verification('c-1', '내용1')
        queue_for_verification('c-2', '내용2')
        tickets = list_tickets()
        if len(tickets) >= 2:
            self.assertGreaterEqual(tickets[0].created_at, tickets[1].created_at)


class TestClearStore(unittest.TestCase):
    """clear_store 함수 테스트"""

    def test_clear_empties_store(self):
        """clear_store 후 저장소가 비어있다"""
        queue_for_verification('c-1', '내용')
        clear_store()
        self.assertEqual(list_tickets(), [])


if __name__ == '__main__':
    unittest.main()
