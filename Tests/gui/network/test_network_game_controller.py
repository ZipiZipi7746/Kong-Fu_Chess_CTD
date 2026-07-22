from kungfu_chess.gui.network.network_engine_view import NetworkEngineView
from kungfu_chess.gui.network.network_game_controller import NetworkGameController

STARTING_ROWS = [
    ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
    ["bP"] * 8,
    ["."] * 8, ["."] * 8, ["."] * 8, ["."] * 8,
    ["wP"] * 8,
    ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
]


class RequestSpy:
    def __init__(self):
        self.move_requests = []
        self.jump_requests = []

    def on_move_request(self, from_row, from_col, to_row, to_col):
        self.move_requests.append((from_row, from_col, to_row, to_col))

    def on_jump_request(self, row, col):
        self.jump_requests.append((row, col))


def make_controller(my_color="w", engine=None):
    spy = RequestSpy()
    controller = NetworkGameController(
        my_color, spy.on_move_request, spy.on_jump_request, engine=engine)
    return controller, spy


class TestDefaultEngine:
    def test_defaults_to_a_real_network_engine_view_when_none_is_given(self):
        # Matches the project's established param=None -> real default DI
        # convention (GameEngine, GameSession, AuthenticationService).
        controller, spy = make_controller()
        assert isinstance(controller.engine, NetworkEngineView)


class TestClickSelection:
    def test_clicking_an_empty_cell_first_selects_nothing(self):
        controller, spy = make_controller()
        controller.click(4, 4, STARTING_ROWS)
        assert controller.selected is None

    def test_clicking_an_enemy_piece_first_selects_nothing(self):
        controller, spy = make_controller(my_color="w")
        controller.click(1, 0, STARTING_ROWS)  # black pawn
        assert controller.selected is None

    def test_clicking_my_own_piece_first_selects_it(self):
        controller, spy = make_controller(my_color="w")
        controller.click(6, 4, STARTING_ROWS)
        assert controller.selected == (6, 4)

    def test_clicking_a_piece_already_mid_motion_does_not_select_it(self):
        engine = NetworkEngineView()
        engine.update({
            "board": STARTING_ROWS, "sequence": 0, "game_over": False, "winner": None,
            "motions": [{"from": [6, 4], "to": [5, 4], "progress": 0.2}],
            "cooldowns": [], "airborne": [],
        })
        controller, spy = make_controller(my_color="w", engine=engine)
        controller.click(6, 4, STARTING_ROWS)
        assert controller.selected is None

    def test_clicking_an_airborne_piece_does_not_select_it(self):
        engine = NetworkEngineView()
        engine.update({
            "board": STARTING_ROWS, "sequence": 0, "game_over": False, "winner": None,
            "motions": [], "cooldowns": [], "airborne": [{"row": 6, "col": 4}],
        })
        controller, spy = make_controller(my_color="w", engine=engine)
        controller.click(6, 4, STARTING_ROWS)
        assert controller.selected is None

    def test_clicking_a_piece_on_cooldown_does_not_select_it(self):
        engine = NetworkEngineView()
        engine.update({
            "board": STARTING_ROWS, "sequence": 0, "game_over": False, "winner": None,
            "motions": [], "cooldowns": [{"row": 6, "col": 4, "progress": 0.5}], "airborne": [],
        })
        controller, spy = make_controller(my_color="w", engine=engine)
        controller.click(6, 4, STARTING_ROWS)
        assert controller.selected is None


class TestClickToMove:
    def test_second_click_on_an_empty_cell_sends_a_move_request(self):
        controller, spy = make_controller(my_color="w")
        controller.click(6, 4, STARTING_ROWS)
        controller.click(4, 4, STARTING_ROWS)
        assert spy.move_requests == [(6, 4, 4, 4)]
        assert controller.selected is None

    def test_second_click_on_an_enemy_piece_sends_a_move_request(self):
        controller, spy = make_controller(my_color="w")
        controller.click(6, 4, STARTING_ROWS)
        controller.click(1, 4, STARTING_ROWS)
        assert spy.move_requests == [(6, 4, 1, 4)]

    def test_second_click_on_another_friendly_piece_reselects_instead_of_moving(self):
        controller, spy = make_controller(my_color="w")
        controller.click(6, 4, STARTING_ROWS)
        controller.click(6, 3, STARTING_ROWS)
        assert spy.move_requests == []
        assert controller.selected == (6, 3)

    def test_game_over_ignores_further_clicks(self):
        engine = NetworkEngineView()
        engine.update({
            "board": STARTING_ROWS, "sequence": 0, "game_over": True, "winner": "w",
            "motions": [], "cooldowns": [], "airborne": [],
        })
        controller, spy = make_controller(my_color="w", engine=engine)
        controller.click(6, 4, STARTING_ROWS)
        assert controller.selected is None


class TestSpectatorMode:
    """Phase E: a spectator has my_color=None (the server assigns no
    color to a read-only observer) - no special-casing needed anywhere
    in this class, since token[0] (always "w" or "b") can never equal
    None, so every selection/move/jump attempt is already a no-op."""

    def test_clicking_any_piece_never_selects_anything(self):
        controller, spy = make_controller(my_color=None)
        controller.click(6, 4, STARTING_ROWS)  # a white piece
        assert controller.selected is None
        controller.click(1, 4, STARTING_ROWS)  # a black piece
        assert controller.selected is None

    def test_no_move_request_is_ever_sent(self):
        controller, spy = make_controller(my_color=None)
        controller.click(6, 4, STARTING_ROWS)
        controller.click(4, 4, STARTING_ROWS)
        assert spy.move_requests == []

    def test_jumping_any_piece_sends_nothing(self):
        controller, spy = make_controller(my_color=None)
        controller.jump(6, 4, STARTING_ROWS)
        controller.jump(1, 4, STARTING_ROWS)
        assert spy.jump_requests == []


class TestJump:
    def test_jumping_my_own_piece_sends_a_jump_request(self):
        controller, spy = make_controller(my_color="w")
        controller.jump(6, 4, STARTING_ROWS)
        assert spy.jump_requests == [(6, 4)]

    def test_jumping_an_empty_cell_sends_nothing(self):
        controller, spy = make_controller(my_color="w")
        controller.jump(4, 4, STARTING_ROWS)
        assert spy.jump_requests == []

    def test_jumping_an_enemy_piece_sends_nothing(self):
        controller, spy = make_controller(my_color="w")
        controller.jump(1, 4, STARTING_ROWS)
        assert spy.jump_requests == []
