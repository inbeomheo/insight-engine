"""업스트림 경보 서비스 테스트"""
import unittest
from services.upstream_alert_service import (
    check_source, batch_check, classify_severity, get_critical_alerts,
    UpstreamSource, AlertEvent
)


class TestUpstreamAlertService(unittest.TestCase):

    def setUp(self):
        self.source = UpstreamSource(
            source_id='src1', name='API', url='https://api.example.com',
            last_checked='2026-03-10', hash='abc123'
        )

    def test_check_source_no_change(self):
        result = check_source(self.source, 'abc123')
        self.assertIsNone(result)

    def test_check_source_content_changed(self):
        result = check_source(self.source, 'def456')
        self.assertIsInstance(result, AlertEvent)
        self.assertEqual(result.change_type, 'content_changed')
        self.assertEqual(result.severity, 'info')

    def test_check_source_unavailable(self):
        result = check_source(self.source, '')
        self.assertIsNotNone(result)
        self.assertEqual(result.change_type, 'unavailable')
        self.assertEqual(result.severity, 'critical')

    def test_batch_check_mixed(self):
        sources = [
            self.source,
            UpstreamSource('src2', 'DB', 'http://db', '2026-03-10', 'xyz'),
        ]
        hashes = {'src1': 'abc123', 'src2': 'changed'}
        events = batch_check(sources, hashes)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source_id, 'src2')

    def test_batch_check_no_changes(self):
        events = batch_check([self.source], {'src1': 'abc123'})
        self.assertEqual(len(events), 0)

    def test_classify_severity_mapping(self):
        self.assertEqual(classify_severity('content_changed'), 'info')
        self.assertEqual(classify_severity('unavailable'), 'critical')
        self.assertEqual(classify_severity('schema_changed'), 'warning')
        self.assertEqual(classify_severity('unknown'), 'info')

    def test_get_critical_alerts_filters(self):
        events = [
            AlertEvent('e1', 'src1', 'content_changed', 'info', '2026-03-10'),
            AlertEvent('e2', 'src2', 'unavailable', 'critical', '2026-03-10'),
        ]
        critical = get_critical_alerts(events)
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].event_id, 'e2')

    def test_get_critical_alerts_empty(self):
        events = [AlertEvent('e1', 'src1', 'content_changed', 'info', '2026-03-10')]
        critical = get_critical_alerts(events)
        self.assertEqual(len(critical), 0)

    def test_check_source_unique_event_id(self):
        r1 = check_source(self.source, 'new1')
        r2 = check_source(self.source, 'new2')
        self.assertNotEqual(r1.event_id, r2.event_id)

    def test_batch_check_missing_hash_uses_original(self):
        events = batch_check([self.source], {})
        self.assertEqual(len(events), 0)


if __name__ == '__main__':
    unittest.main()
