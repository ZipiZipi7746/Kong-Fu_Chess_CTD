from kungfu_chess.gui.animation.piece_view_model import PieceViewModel


CONFIGS = {
    "idle": {"physics": {"next_state_when_finished": "idle"},
              "graphics": {"frames_per_sec": 4, "is_loop": True}},
    "move": {"physics": {"next_state_when_finished": "long_rest"},
              "graphics": {"frames_per_sec": 8, "is_loop": True}},
    "jump": {"physics": {"next_state_when_finished": "short_rest"},
              "graphics": {"frames_per_sec": 10, "is_loop": False}},  # 5 frames -> 500ms
    "short_rest": {"physics": {"next_state_when_finished": "long_rest"},
                    "graphics": {"frames_per_sec": 6, "is_loop": False}},  # 5 frames -> ~833ms
    "long_rest": {"physics": {"next_state_when_finished": "idle"},
                   "graphics": {"frames_per_sec": 2, "is_loop": False}},  # 5 frames -> 2500ms
}


class FakeSpriteLibrary:
    def __init__(self):
        self.requested = []

    def load(self, piece_code, state):
        self.requested.append((piece_code, state))
        frames = [f"{piece_code}/{state}/{i}.png" for i in range(1, 6)]
        return frames, CONFIGS[state]


class TestInitialState:
    def test_starts_idle(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        assert view_model.state_name == "idle"

    def test_current_frame_path_matches_frame_index(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        assert view_model.current_frame_path == "wR/idle/1.png"


class TestGameDrivenTransitions:
    def test_switches_to_move_when_engine_reports_pending_move(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=False)
        assert view_model.state_name == "move"

    def test_switches_to_jump_when_engine_reports_airborne(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wN")
        view_model.update(dt_ms=50, has_pending_move=False, is_airborne=True)
        assert view_model.state_name == "jump"

    def test_move_takes_priority_if_somehow_both_are_true(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=True)
        assert view_model.state_name == "move"

    def test_switching_state_resets_the_animation_clock(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=False)
        assert view_model.current_frame_path == "wR/move/1.png"


class TestHandoffWhenGameStateEnds:
    def test_move_hands_off_to_long_rest_the_moment_the_move_ends(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=False)
        view_model.update(dt_ms=50, has_pending_move=False, is_airborne=False)
        assert view_model.state_name == "long_rest"

    def test_jump_hands_off_to_short_rest_the_moment_airborne_ends(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wN")
        view_model.update(dt_ms=50, has_pending_move=False, is_airborne=True)
        view_model.update(dt_ms=50, has_pending_move=False, is_airborne=False)
        assert view_model.state_name == "short_rest"


class TestSelfDrivenTransitions:
    def test_short_rest_hands_off_to_long_rest_once_its_own_animation_finishes(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wN")
        view_model.update(dt_ms=0, has_pending_move=False, is_airborne=True)
        view_model.update(dt_ms=0, has_pending_move=False, is_airborne=False)  # -> short_rest
        assert view_model.state_name == "short_rest"
        view_model.update(dt_ms=1000, has_pending_move=False, is_airborne=False)  # finishes (~833ms)
        assert view_model.state_name == "long_rest"

    def test_long_rest_hands_off_to_idle_once_its_own_animation_finishes(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wN")
        view_model.update(dt_ms=0, has_pending_move=False, is_airborne=True)
        view_model.update(dt_ms=0, has_pending_move=False, is_airborne=False)  # -> short_rest
        view_model.update(dt_ms=1000, has_pending_move=False, is_airborne=False)  # -> long_rest
        assert view_model.state_name == "long_rest"
        view_model.update(dt_ms=2500, has_pending_move=False, is_airborne=False)  # finishes (2500ms)
        assert view_model.state_name == "idle"

    def test_idle_stays_idle_indefinitely(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        for _ in range(20):
            view_model.update(dt_ms=1000, has_pending_move=False, is_airborne=False)
        assert view_model.state_name == "idle"

    def test_new_move_interrupts_long_rest_immediately(self):
        view_model = PieceViewModel(FakeSpriteLibrary(), "wR")
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=False)
        view_model.update(dt_ms=50, has_pending_move=False, is_airborne=False)  # -> long_rest
        assert view_model.state_name == "long_rest"
        view_model.update(dt_ms=50, has_pending_move=True, is_airborne=False)  # a new move starts
        assert view_model.state_name == "move"
