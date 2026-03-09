"""이벤트 리와인드 서비스 테스트"""
import unittest
from services.event_rewind_service import (
    record_event, rewind_to, replay_range, summarize_timeline,
    Timeline, TimelineEvent
)


class TestEventRewindService(unittest.TestCase):

    def setUp(self):
        self.timeline = Timeline(timeline_id='tl1', events=[])

    def test_record_event_adds(self):
        tl = record_event(self.timeline, 'click', '버튼 클릭', {'btn': 'submit'})
        self.assertEqual(len(tl.events), 1)
        self.assertEqual(tl.events[0].event_type, 'click')

    def test_record_event_preserves_id(self):
        tl = record_event(self.timeline, 'click', '테스트', {})
        self.assertEqual(tl.timeline_id, 'tl1')

    def test_record_multiple_events(self):
        tl = record_event(self.timeline, 'a', 'd1', {})
        tl = record_event(tl, 'b', 'd2', {})
        self.assertEqual(len(tl.events), 2)

    def test_rewind_to_filters(self):
        events = [
            TimelineEvent('e1', '2026-01-01T10:00:00', 'a', 'd1', {}),
            TimelineEvent('e2', '2026-01-01T12:00:00', 'b', 'd2', {}),
            TimelineEvent('e3', '2026-01-01T14:00:00', 'c', 'd3', {}),
        ]
        tl = Timeline('tl1', events)
        rewound = rewind_to(tl, '2026-01-01T12:00:00')
        self.assertEqual(len(rewound.events), 2)

    def test_rewind_to_empty(self):
        events = [TimelineEvent('e1', '2026-01-01T10:00:00', 'a', 'd', {})]
        tl = Timeline('tl1', events)
        rewound = rewind_to(tl, '2025-01-01T00:00:00')
        self.assertEqual(len(rewound.events), 0)

    def test_replay_range(self):
        events = [
            TimelineEvent('e1', '2026-01-01T10:00:00', 'a', 'd1', {}),
            TimelineEvent('e2', '2026-01-01T12:00:00', 'b', 'd2', {}),
            TimelineEvent('e3', '2026-01-01T14:00:00', 'c', 'd3', {}),
        ]
        tl = Timeline('tl1', events)
        replayed = replay_range(tl, '2026-01-01T11:00:00', '2026-01-01T13:00:00')
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].event_id, 'e2')

    def test_summarize_timeline_with_events(self):
        events = [
            TimelineEvent('e1', '2026-01-01T10:00:00', 'click', 'd1', {}),
            TimelineEvent('e2', '2026-01-01T12:00:00', 'click', 'd2', {}),
            TimelineEvent('e3', '2026-01-01T14:00:00', 'scroll', 'd3', {}),
        ]
        tl = Timeline('tl1', events)
        summary = summarize_timeline(tl)
        self.assertEqual(summary['total_events'], 3)
        self.assertEqual(summary['event_types']['click'], 2)
        self.assertEqual(summary['first'], '2026-01-01T10:00:00')

    def test_summarize_empty_timeline(self):
        summary = summarize_timeline(self.timeline)
        self.assertEqual(summary['total_events'], 0)
        self.assertIsNone(summary['first'])

    def test_record_immutable(self):
        tl_new = record_event(self.timeline, 'x', 'y', {})
        self.assertEqual(len(self.timeline.events), 0)
        self.assertEqual(len(tl_new.events), 1)

    def test_event_has_timestamp(self):
        tl = record_event(self.timeline, 'test', 'desc', {})
        self.assertTrue(len(tl.events[0].timestamp) > 0)


if __name__ == '__main__':
    unittest.main()
