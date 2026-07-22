from kungfu_chess.application.connection_service import ConnectionService


class TestRecordDisconnectAndReconnect:
    def test_reconnecting_within_the_window_returns_the_game_id(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)

        assert service.reconnect("alice") == "g_1"

    def test_reconnecting_clears_the_disconnected_state(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)
        service.reconnect("alice")

        assert service.is_disconnected("alice") is False
        assert service.reconnect("alice") is None  # nothing left to reconnect to

    def test_reconnecting_an_identity_that_never_disconnected_returns_none(self):
        service = ConnectionService(grace_period_ms=20_000)
        assert service.reconnect("nobody") is None

    def test_is_disconnected_reflects_current_state(self):
        service = ConnectionService(grace_period_ms=20_000)
        assert service.is_disconnected("alice") is False
        service.record_disconnect("g_1", "alice", now_ms=0)
        assert service.is_disconnected("alice") is True


class TestGracePeriodExpiry:
    def test_a_player_still_within_the_grace_period_does_not_expire(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)

        expired = service.pop_expired(now_ms=19_999)

        assert expired == []
        assert service.is_disconnected("alice") is True

    def test_a_player_past_the_grace_period_expires_exactly_once(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)

        expired = service.pop_expired(now_ms=20_000)
        assert expired == [("g_1", "alice")]

        # Already removed - a later poll must not report it again.
        assert service.pop_expired(now_ms=30_000) == []
        assert service.is_disconnected("alice") is False

    def test_multiple_disconnected_players_expire_independently(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)
        service.record_disconnect("g_2", "bob", now_ms=15_000)

        expired = service.pop_expired(now_ms=20_000)

        assert expired == [("g_1", "alice")]
        assert service.is_disconnected("bob") is True

    def test_reconnecting_before_expiry_prevents_a_later_forfeit(self):
        service = ConnectionService(grace_period_ms=20_000)
        service.record_disconnect("g_1", "alice", now_ms=0)
        service.reconnect("alice")

        assert service.pop_expired(now_ms=20_000) == []


class TestGracePeriodMs:
    def test_grace_period_ms_is_readable_for_the_outgoing_player_disconnected_message(self):
        service = ConnectionService(grace_period_ms=20_000)
        assert service.grace_period_ms == 20_000

    def test_defaults_to_twenty_seconds(self):
        service = ConnectionService()
        assert service.grace_period_ms == 20_000
