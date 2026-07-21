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


class TestBuildRenderState:
    """Phase F Milestone 1: the periodic broadcast a networked GUI client
    animates from - purely a read of GameEngine's own already-public
    accessor methods (has_pending_move_from/is_airborne/cooldown_progress/
    motion_progress/motion_target), the same ones ViewModelRegistry and
    GameController already call locally. No new engine-layer state or
    behavior; this only serializes what's already there."""

    def test_includes_the_board_sequence_game_over_and_winner_like_the_snapshot(self):
        session = make_session([["wR", "."]])
        session.next_sequence()
        render_state = dto.build_render_state(session)
        assert render_state["board"] == [["wR", "."]]
        assert render_state["sequence"] == 1
        assert render_state["game_over"] is False
        assert render_state["winner"] is None

    def test_no_motions_cooldowns_or_airborne_pieces_when_nothing_is_happening(self):
        session = make_session([["wR", "."]])
        render_state = dto.build_render_state(session)
        assert render_state["motions"] == []
        assert render_state["cooldowns"] == []
        assert render_state["airborne"] == []

    def test_an_in_flight_move_is_reported_with_its_progress(self):
        session = make_session([["wR", ".", "."]])
        session.engine.request_move(0, 0, 0, 2)  # 2 cells -> 2000ms total
        session.engine.advance_time(500)  # 25% of the way there

        render_state = dto.build_render_state(session)
        assert render_state["motions"] == [
            {"from": [0, 0], "to": [0, 2], "progress": 0.25}]

    def test_an_airborne_piece_is_reported(self):
        session = make_session([["wR"]])
        session.engine.request_jump(0, 0)

        render_state = dto.build_render_state(session)
        assert render_state["airborne"] == [{"row": 0, "col": 0}]

    def test_a_cell_on_cooldown_is_reported_with_its_progress(self):
        session = make_session([["wR", "."]])
        session.engine.request_move(0, 0, 0, 1)  # 1 cell -> 1000ms
        session.engine.advance_time(1000)  # arrives, cooldown starts (500ms)
        session.engine.advance_time(250)  # halfway through the cooldown

        render_state = dto.build_render_state(session)
        assert render_state["cooldowns"] == [{"row": 0, "col": 1, "progress": 0.5}]
