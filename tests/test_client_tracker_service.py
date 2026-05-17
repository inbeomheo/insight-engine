"""Client heartbeat tracker service tests."""

from services.ops.client_tracker_service import ClientTracker


def test_client_tracker_records_heartbeat_and_closes_client():
    tracker = ClientTracker(clock=lambda: 123.4)

    tracker.heartbeat("client-a")
    assert tracker.clients == {"client-a": 123.4}

    assert tracker.close("client-a") is True
    assert tracker.clients == {}
    assert tracker.close("missing") is False


def test_client_tracker_cleanup_removes_only_stale_clients():
    tracker = ClientTracker(stale_after_seconds=300, clock=lambda: 1000.0)
    tracker.clients["stale"] = 699.0
    tracker.clients["fresh"] = 701.0

    removed = tracker.cleanup_stale()

    assert removed == ["stale"]
    assert tracker.clients == {"fresh": 701.0}
