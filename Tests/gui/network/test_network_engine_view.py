from kungfu_chess.gui.network.network_engine_view import NetworkEngineView


def make_render_state(**overrides):
    render_state = {
        "board": [["."]],
        "sequence": 0,
        "game_over": False,
        "winner": None,
        "motions": [],
        "cooldowns": [],
        "airborne": [],
    }
    render_state.update(overrides)
    return render_state


class TestInitialState:
    def test_starts_with_no_game_over_and_no_winner(self):
        view = NetworkEngineView()
        assert view.game_over is False
        assert view.winner is None

    def test_starts_with_nothing_pending_anywhere(self):
        view = NetworkEngineView()
        assert view.has_pending_move_from(0, 0) is False
        assert view.is_airborne(0, 0) is False
        assert view.is_on_cooldown(0, 0) is False
        assert view.cooldown_progress(0, 0) is None
        assert view.motion_progress(0, 0) is None
        assert view.motion_target(0, 0) is None


class TestUpdate:
    def test_reflects_game_over_and_winner(self):
        view = NetworkEngineView()
        view.update(make_render_state(game_over=True, winner="w"))
        assert view.game_over is True
        assert view.winner == "w"

    def test_reflects_an_in_flight_motion(self):
        view = NetworkEngineView()
        view.update(make_render_state(
            motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.4}]))

        assert view.has_pending_move_from(6, 4) is True
        assert view.motion_progress(6, 4) == 0.4
        assert view.motion_target(6, 4) == (5, 4)
        assert view.has_pending_move_from(0, 0) is False

    def test_reflects_an_airborne_cell(self):
        view = NetworkEngineView()
        view.update(make_render_state(airborne=[{"row": 3, "col": 3}]))
        assert view.is_airborne(3, 3) is True
        assert view.is_airborne(0, 0) is False

    def test_reflects_a_cooldown_cell(self):
        view = NetworkEngineView()
        view.update(make_render_state(cooldowns=[{"row": 2, "col": 2, "progress": 0.75}]))
        assert view.is_on_cooldown(2, 2) is True
        assert view.cooldown_progress(2, 2) == 0.75
        assert view.is_on_cooldown(0, 0) is False

    def test_a_later_update_replaces_the_previous_state_entirely(self):
        view = NetworkEngineView()
        view.update(make_render_state(motions=[{"from": [1, 1], "to": [2, 2], "progress": 0.1}]))
        view.update(make_render_state())  # nothing in flight anymore
        assert view.has_pending_move_from(1, 1) is False

    def test_tolerates_a_state_snapshot_shaped_payload_with_no_motion_keys(self):
        # state_snapshot/game_started payloads carry board/sequence/
        # game_over/winner only - no motions/cooldowns/airborne. The
        # network game loop feeds both shapes through the same update()
        # call rather than branching on message type.
        view = NetworkEngineView()
        view.update({"board": [["."]], "sequence": 0, "game_over": False, "winner": None})
        assert view.has_pending_move_from(0, 0) is False
        assert view.is_airborne(0, 0) is False
        assert view.is_on_cooldown(0, 0) is False
