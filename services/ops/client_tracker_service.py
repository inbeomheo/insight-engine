"""In-memory client heartbeat tracker."""

from __future__ import annotations

from collections.abc import Callable
import time


class ClientTracker:
    """Track recently active client IDs for lightweight presence checks."""

    def __init__(
        self,
        *,
        stale_after_seconds: float = 300,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.stale_after_seconds = stale_after_seconds
        self.clock = clock or time.time
        self.clients: dict[str, float] = {}

    def heartbeat(self, client_id: str) -> None:
        """Record that a client is currently active."""
        self.clients[client_id] = self.clock()

    def close(self, client_id: str) -> bool:
        """Remove a client and report whether it existed."""
        existed = client_id in self.clients
        self.clients.pop(client_id, None)
        return existed

    def cleanup_stale(self) -> list[str]:
        """Remove clients that have not sent a heartbeat recently."""
        now = self.clock()
        stale = [
            client_id
            for client_id, last_seen in self.clients.items()
            if now - last_seen > self.stale_after_seconds
        ]
        for client_id in stale:
            del self.clients[client_id]
        return stale
