"""MatchmakingService (Master Plan v2 Section 10.2, Decisions 5/6/13) -
the "Play" queue. Deterministic and clock-injected throughout (never
reads a real clock itself): the caller (server_main.py's tick loop)
passes now_ms explicitly, the same convention RealTimeArbiter already
uses for virtual time (Rule 9) - this keeps matchmaking timing fully
testable and repeatable, not dependent on wall-clock timing in a test.

DEFAULT_RATING_BAND/DEFAULT_TIMEOUT_MS are plain module constants,
matching this project's existing convention (see rating_service.
DEFAULT_K_FACTOR) rather than a separate Config class hierarchy."""

DEFAULT_RATING_BAND = 100
DEFAULT_TIMEOUT_MS = 60_000


class _QueueEntry:
    def __init__(self, user_id, rating, enqueued_at_ms):
        self.user_id = user_id
        self.rating = rating
        self.enqueued_at_ms = enqueued_at_ms


class MatchmakingService:
    def __init__(self, rating_band=DEFAULT_RATING_BAND, timeout_ms=DEFAULT_TIMEOUT_MS):
        self._rating_band = rating_band
        self._timeout_ms = timeout_ms
        self._queue = []

    def enqueue(self, user_id, rating, now_ms):
        self._queue.append(_QueueEntry(user_id, rating, now_ms))

    def cancel(self, user_id):
        self._queue = [entry for entry in self._queue if entry.user_id != user_id]

    def is_queued(self, user_id):
        return any(entry.user_id == user_id for entry in self._queue)

    def tick(self, now_ms):
        """Scans for every currently possible match first, removing
        matched players from the queue, and only then pops whoever is
        left waiting past the timeout (Decision 5: no auto-retry, the
        client returns to idle) - a match always wins over a
        simultaneous timeout for the same players, since by the time
        timeouts are checked they're already gone from the queue. No
        threading/locking needed: this whole service is only ever
        called from the single-threaded asyncio tick loop, so this
        ordering alone is what the plan's "atomic claim" concern asks
        for. Returns (matches, timed_out_user_ids)."""
        matches = []
        while True:
            match = self._find_one_match()
            if match is None:
                break
            matches.append(match)

        timed_out = self._pop_timed_out(now_ms)
        return matches, timed_out

    def _find_one_match(self):
        for i, entry_a in enumerate(self._queue):
            for entry_b in self._queue[i + 1:]:
                if abs(entry_a.rating - entry_b.rating) <= self._rating_band:
                    self._queue.remove(entry_a)
                    self._queue.remove(entry_b)
                    return entry_a.user_id, entry_b.user_id
        return None

    def _pop_timed_out(self, now_ms):
        timed_out = [
            entry for entry in self._queue
            if now_ms - entry.enqueued_at_ms >= self._timeout_ms
        ]
        for entry in timed_out:
            self._queue.remove(entry)
        return [entry.user_id for entry in timed_out]
