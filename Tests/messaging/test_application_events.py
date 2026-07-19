from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)


class TestGameStartedEvent:
    def test_stores_all_fields(self):
        event = GameStartedEvent(game_id="g_1", white="alice", black="bob", timestamp_ms=100)
        assert event.game_id == "g_1"
        assert event.white == "alice"
        assert event.black == "bob"
        assert event.timestamp_ms == 100

    def test_timestamp_ms_defaults_to_zero(self):
        event = GameStartedEvent(game_id="g_1", white="alice", black="bob")
        assert event.timestamp_ms == 0


class TestGameMoveAppliedEvent:
    def test_stores_all_fields(self):
        event = GameMoveAppliedEvent(
            game_id="g_1", from_row=1, from_col=2, to_row=3, to_col=4,
            moving_piece="wP", captured_piece="bN", timestamp_ms=500)
        assert event.game_id == "g_1"
        assert (event.from_row, event.from_col) == (1, 2)
        assert (event.to_row, event.to_col) == (3, 4)
        assert event.moving_piece == "wP"
        assert event.captured_piece == "bN"
        assert event.timestamp_ms == 500

    def test_captured_piece_defaults_to_none(self):
        event = GameMoveAppliedEvent(
            game_id="g_1", from_row=0, from_col=0, to_row=0, to_col=1, moving_piece="wR")
        assert event.captured_piece is None


class TestMoveRejectedEvent:
    def test_stores_all_fields(self):
        event = MoveRejectedEvent(game_id="g_1", user_id="u_1", reason="INVALID_MOVE")
        assert event.game_id == "g_1"
        assert event.user_id == "u_1"
        assert event.reason == "INVALID_MOVE"


class TestGameEndedEvent:
    def test_stores_all_fields(self):
        event = GameEndedEvent(game_id="g_1", winner="w", timestamp_ms=9000)
        assert event.game_id == "g_1"
        assert event.winner == "w"
        assert event.timestamp_ms == 9000
