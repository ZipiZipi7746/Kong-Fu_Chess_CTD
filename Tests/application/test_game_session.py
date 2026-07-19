import asyncio

from kungfu_chess.model.board import Board
from kungfu_chess.application.game_session import GameSession


def make_board(rows):
    return Board(rows)


def make_session(rows, white="alice", black="bob"):
    return GameSession(
        game_id="g_1", board=make_board(rows), white=white, black=black, jump_duration_ms=1000)


class TestConstruction:
    def test_owns_a_real_game_engine_over_the_given_board(self):
        session = make_session([["wR", "."]])
        assert session.engine.board.get_cell(0, 0).kind == "R"

    def test_owns_an_asyncio_lock(self):
        session = make_session([["wR", "."]])
        assert isinstance(session.lock, asyncio.Lock)

    def test_sequence_starts_at_zero(self):
        session = make_session([["wR", "."]])
        assert session.sequence == 0


class TestColorFor:
    def test_white_display_name_maps_to_w(self):
        session = make_session([["wR", "."]], white="alice", black="bob")
        assert session.color_for("alice") == "w"

    def test_black_display_name_maps_to_b(self):
        session = make_session([["wR", "."]], white="alice", black="bob")
        assert session.color_for("bob") == "b"

    def test_unknown_display_name_maps_to_none(self):
        session = make_session([["wR", "."]], white="alice", black="bob")
        assert session.color_for("mallory") is None


class TestNextSequence:
    def test_increments_on_each_call(self):
        session = make_session([["wR", "."]])
        assert session.next_sequence() == 1
        assert session.next_sequence() == 2
        assert session.sequence == 2


class TestHasPendingActivity:
    def test_false_when_nothing_is_happening(self):
        session = make_session([["wR", "."]])
        assert session.has_pending_activity() is False

    def test_true_while_a_move_is_in_flight(self):
        session = make_session([["wR", ".", "."]])
        session.engine.request_move(0, 0, 0, 2)
        assert session.has_pending_activity() is True

    def test_true_while_a_piece_is_airborne(self):
        session = make_session([["wR"]])
        session.engine.request_jump(0, 0)
        assert session.has_pending_activity() is True

    def test_true_while_a_piece_is_on_cooldown(self):
        session = make_session([["wR", "."]])
        session.engine.request_move(0, 0, 0, 1)
        session.engine.advance_time(1000)  # arrives, cooldown starts
        assert session.has_pending_activity() is True

    def test_false_again_once_everything_settles(self):
        session = make_session([["wR", "."]])
        session.engine.request_move(0, 0, 0, 1)
        session.engine.advance_time(1000)  # arrives, cooldown starts
        session.engine.advance_time(1000)  # cooldown (default 500ms) clears
        assert session.has_pending_activity() is False
