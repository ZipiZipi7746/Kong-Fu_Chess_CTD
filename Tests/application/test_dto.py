from kungfu_chess.model.board import Board
from kungfu_chess.application.game_session import GameSession
from kungfu_chess.application import dto


def make_session(rows):
    return GameSession(
        game_id="g_1", board=Board(rows), white="alice", black="bob", jump_duration_ms=1000)


class TestBuildStateSnapshot:
    def test_board_is_a_json_serializable_grid_of_piece_codes(self):
        session = make_session([["wR", "."], [".", "bK"]])
        snapshot = dto.build_state_snapshot(session)
        assert snapshot["board"] == [["wR", "."], [".", "bK"]]

    def test_includes_the_current_sequence(self):
        session = make_session([["wR", "."]])
        session.next_sequence()
        session.next_sequence()
        snapshot = dto.build_state_snapshot(session)
        assert snapshot["sequence"] == 2

    def test_game_over_defaults_to_false_and_winner_to_none(self):
        session = make_session([["wR", "."]])
        snapshot = dto.build_state_snapshot(session)
        assert snapshot["game_over"] is False
        assert snapshot["winner"] is None

    def test_reflects_game_over_and_winner_once_the_game_has_ended(self):
        session = make_session([["wR", "bK"]])
        session.engine.request_move(0, 0, 0, 1)
        session.engine.advance_time(1000)
        snapshot = dto.build_state_snapshot(session)
        assert snapshot["game_over"] is True
        assert snapshot["winner"] == "w"
