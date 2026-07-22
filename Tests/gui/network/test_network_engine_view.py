import pytest

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


class TestMotionProgressExtrapolation:
    """The server only broadcasts a fresh render_state every ~75ms
    (server_main.py's TICK_INTERVAL_MS), but the render loop draws at a
    much higher frame rate - without smoothing, a piece would visibly
    jump in ~75ms steps. advance(dt_ms) accumulates real per-frame time
    between two server updates; once two updates for the same in-flight
    motion are seen, the progress rate between them is used to
    extrapolate motion_progress() smoothly for the frames in between."""

    def test_first_sighting_of_a_motion_has_no_rate_yet_and_returns_the_raw_value(self):
        view = NetworkEngineView()
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.0}]))
        view.advance(50)
        assert view.motion_progress(6, 4) == 0.0

    def test_extrapolates_using_the_rate_between_two_updates(self):
        view = NetworkEngineView()
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.0}]))
        view.advance(75)
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.2}]))
        # Rate established: 0.2 progress / 75ms. Halfway to the next
        # server update, the piece should be roughly halfway further.
        view.advance(37.5)
        assert view.motion_progress(6, 4) == pytest.approx(0.3)

    def test_extrapolated_progress_never_reaches_full_arrival_before_the_server_confirms_it(self):
        view = NetworkEngineView()
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.0}]))
        view.advance(75)
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.2}]))
        view.advance(10_000)  # far longer than the server actually took
        assert view.motion_progress(6, 4) < 1.0

    def test_a_motion_starting_fresh_at_a_previously_tracked_cell_does_not_inherit_the_old_rate(self):
        view = NetworkEngineView()
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.0}]))
        view.advance(75)
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.2}]))
        view.advance(75)
        view.update(make_render_state())  # the motion arrived - nothing in flight
        view.advance(75)
        # A brand new motion happens to start from the same cell.
        view.update(make_render_state(motions=[{"from": [6, 4], "to": [5, 4], "progress": 0.0}]))
        view.advance(37.5)
        assert view.motion_progress(6, 4) == 0.0

    def test_cooldown_progress_is_not_extrapolated(self):
        view = NetworkEngineView()
        view.update(make_render_state(cooldowns=[{"row": 2, "col": 2, "progress": 0.5}]))
        view.advance(1000)
        assert view.cooldown_progress(2, 2) == 0.5
