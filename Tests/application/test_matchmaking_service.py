from kungfu_chess.application.matchmaking_service import MatchmakingService


class TestEnqueueAndMatch:
    def test_two_players_within_the_rating_band_are_matched(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1250, now_ms=0)

        matches, timed_out = service.tick(now_ms=100)

        assert matches == [("alice", "bob")]
        assert timed_out == []
        assert service.is_queued("alice") is False
        assert service.is_queued("bob") is False

    def test_two_players_outside_the_rating_band_are_not_matched(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1400, now_ms=0)

        matches, timed_out = service.tick(now_ms=100)

        assert matches == []
        assert service.is_queued("alice") is True
        assert service.is_queued("bob") is True

    def test_a_solo_player_is_not_matched_with_themselves(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)

        matches, timed_out = service.tick(now_ms=100)

        assert matches == []
        assert service.is_queued("alice") is True

    def test_a_third_player_remains_queued_after_the_first_two_match(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1210, now_ms=0)
        service.enqueue("carol", rating=1220, now_ms=0)

        matches, timed_out = service.tick(now_ms=100)

        assert matches == [("alice", "bob")]
        assert service.is_queued("carol") is True

    def test_the_rating_band_is_fixed_at_enqueue_time_and_never_widens(self):
        # Decision 13: the +-100 band never widens while a player waits,
        # even after a very long time in queue.
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1400, now_ms=0)

        matches, timed_out = service.tick(now_ms=59_000)

        assert matches == []


class TestCancel:
    def test_cancel_removes_a_waiting_player_from_the_queue(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.cancel("alice")
        assert service.is_queued("alice") is False

    def test_a_cancelled_player_is_not_matched_later(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1200, now_ms=0)
        service.cancel("alice")

        matches, timed_out = service.tick(now_ms=100)
        assert matches == []
        assert service.is_queued("bob") is True


class TestTimeout:
    def test_a_player_waiting_past_the_timeout_with_no_match_times_out(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)

        matches, timed_out = service.tick(now_ms=60_000)

        assert matches == []
        assert timed_out == ["alice"]
        assert service.is_queued("alice") is False

    def test_a_player_waiting_less_than_the_timeout_does_not_time_out(self):
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)

        matches, timed_out = service.tick(now_ms=59_999)

        assert timed_out == []
        assert service.is_queued("alice") is True

    def test_a_match_wins_over_a_simultaneous_timeout_for_the_same_players(self):
        # The "atomic claim" concern from Master Plan v2 Section 10.2's
        # required tests: matching is scanned before timeouts are popped,
        # so two players who could be matched are matched even if this
        # exact tick is also past their timeout - never both.
        service = MatchmakingService(rating_band=100, timeout_ms=60_000)
        service.enqueue("alice", rating=1200, now_ms=0)
        service.enqueue("bob", rating=1210, now_ms=0)

        matches, timed_out = service.tick(now_ms=60_000)

        assert matches == [("alice", "bob")]
        assert timed_out == []
