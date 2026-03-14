"""
AuditLogService 단위 테스트 (F4-25)
"""
import unittest
from services.data.audit_log_service import AuditLogService


class TestAuditLogService(unittest.TestCase):

    def setUp(self):
        self.svc = AuditLogService()

    def test_log_entry(self):
        entry = self.svc.log('u1', 'generate', 'content', 'c-1')
        self.assertIn('id', entry)
        self.assertEqual(entry['action'], 'generate')

    def test_query_all(self):
        self.svc.log('u1', 'generate')
        self.svc.log('u2', 'login')
        self.assertEqual(len(self.svc.query()), 2)

    def test_query_by_user(self):
        self.svc.log('u1', 'generate')
        self.svc.log('u2', 'login')
        self.assertEqual(len(self.svc.query(user_id='u1')), 1)

    def test_query_by_action(self):
        self.svc.log('u1', 'generate')
        self.svc.log('u1', 'login')
        self.assertEqual(len(self.svc.query(action='login')), 1)

    def test_query_limit_offset(self):
        for i in range(10):
            self.svc.log('u1', f'action-{i}')
        self.assertEqual(len(self.svc.query(limit=3)), 3)
        self.assertEqual(len(self.svc.query(limit=3, offset=8)), 2)

    def test_actions_summary(self):
        self.svc.log('u1', 'generate')
        self.svc.log('u1', 'generate')
        self.svc.log('u1', 'login')
        summary = self.svc.get_actions_summary()
        self.assertEqual(summary['generate'], 2)
        self.assertEqual(summary['login'], 1)

    def test_max_entries_trimming(self):
        svc = AuditLogService(max_entries=5)
        for i in range(10):
            svc.log('u1', f'a-{i}')
        self.assertEqual(len(svc._logs), 5)


if __name__ == '__main__':
    unittest.main()
