from src.domain.board import Board
from src.domain.piece import Piece
from src.controller.board_mapper import BoardMapper
from src.engine.game_engine import GameEngine
from src.controller.game_controller import GameController


def make_board(rows):
    return Board(rows)


class FakeMapper:
    """Injected via constructor DI so pixel math is fully deterministic
    and decoupled from the controller tests."""

    def __init__(self, mapping):
        self.mapping = mapping

    def to_cell(self, x, y):
        return self.mapping[(x, y)]


class FakeEngine:
    """Injected via constructor DI - lets us assert exactly which calls
    the controller makes without depending on real rule/timing logic."""

    def __init__(self, request_move_result="scheduled", request_jump_result=True,
                 pending=False, airborne=False, game_over=False):
        self.request_move_result = request_move_result
        self.request_jump_result = request_jump_result
        self._pending = pending
        self._airborne = airborne
        self.game_over = game_over
        self.move_calls = []
        self.jump_calls = []
        self.advance_calls = []

    def has_pending_move_from(self, row, col):
        return self._pending

    def is_airborne(self, row, col):
        return self._airborne

    def request_move(self, from_row, from_col, to_row, to_col):
        self.move_calls.append((from_row, from_col, to_row, to_col))
        return self.request_move_result

    def request_jump(self, row, col):
        self.jump_calls.append((row, col))
        return self.request_jump_result

    def advance_time(self, ms):
        self.advance_calls.append(ms)


class TestClickWithFakes:
    def test_click_does_nothing_when_game_over(self):
        board = make_board([["wR"]])
        engine = FakeEngine(game_over=True)
        controller = GameController(board, mapper=FakeMapper({}), engine=engine)
        controller.click(0, 0)
        assert controller.selected is None
        assert engine.move_calls == []

    def test_click_outside_board_is_ignored(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(999, 999): (5, 5)})
        controller = GameController(board, mapper=mapper, engine=FakeEngine())
        controller.click(999, 999)
        assert controller.selected is None

    def test_click_on_empty_cell_selects_nothing(self):
        board = make_board([["."]])
        mapper = FakeMapper({(0, 0): (0, 0)})
        controller = GameController(board, mapper=mapper, engine=FakeEngine())
        controller.click(0, 0)
        assert controller.selected is None

    def test_click_on_piece_with_pending_move_is_not_selected(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(0, 0): (0, 0)})
        engine = FakeEngine(pending=True)
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        assert controller.selected is None

    def test_click_on_airborne_piece_is_not_selected(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(0, 0): (0, 0)})
        engine = FakeEngine(airborne=True)
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        assert controller.selected is None

    def test_click_on_own_piece_selects_it(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(0, 0): (0, 0)})
        controller = GameController(board, mapper=mapper, engine=FakeEngine())
        controller.click(0, 0)
        assert controller.selected == (0, 0)

    def test_second_click_on_same_color_switches_selection(self):
        board = make_board([["wR", "wN"]])
        mapper = FakeMapper({(0, 0): (0, 0), (100, 0): (0, 1)})
        controller = GameController(board, mapper=mapper, engine=FakeEngine())
        controller.click(0, 0)
        controller.click(100, 0)
        assert controller.selected == (0, 1)

    def test_second_click_requests_move_and_clears_selection_on_success(self):
        board = make_board([["wR", "."]])
        mapper = FakeMapper({(0, 0): (0, 0), (100, 0): (0, 1)})
        engine = FakeEngine(request_move_result="scheduled")
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        controller.click(100, 0)
        assert engine.move_calls == [(0, 0, 0, 1)]
        assert controller.selected is None

    def test_second_click_keeps_selection_when_move_invalid(self):
        board = make_board([["wR", "."]])
        mapper = FakeMapper({(0, 0): (0, 0), (100, 0): (0, 1)})
        engine = FakeEngine(request_move_result="invalid")
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        controller.click(100, 0)
        assert controller.selected == (0, 0)

    def test_second_click_clears_selection_when_move_blocked(self):
        board = make_board([["wR", "."]])
        mapper = FakeMapper({(0, 0): (0, 0), (100, 0): (0, 1)})
        engine = FakeEngine(request_move_result="blocked")
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        controller.click(100, 0)
        assert controller.selected is None

    def test_second_click_on_enemy_piece_requests_move_there(self):
        board = make_board([["wR", "bN"]])
        mapper = FakeMapper({(0, 0): (0, 0), (100, 0): (0, 1)})
        engine = FakeEngine(request_move_result="scheduled")
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.click(0, 0)
        controller.click(100, 0)
        assert engine.move_calls == [(0, 0, 0, 1)]


class TestJumpWithFakes:
    def test_jump_does_nothing_when_game_over(self):
        board = make_board([["wR"]])
        engine = FakeEngine(game_over=True)
        controller = GameController(board, mapper=FakeMapper({}), engine=engine)
        controller.jump(0, 0)
        assert engine.jump_calls == []

    def test_jump_outside_board_is_ignored(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(999, 999): (5, 5)})
        engine = FakeEngine()
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.jump(999, 999)
        assert engine.jump_calls == []

    def test_jump_inside_board_delegates_to_engine(self):
        board = make_board([["wR"]])
        mapper = FakeMapper({(0, 0): (0, 0)})
        engine = FakeEngine()
        controller = GameController(board, mapper=mapper, engine=engine)
        controller.jump(0, 0)
        assert engine.jump_calls == [(0, 0)]


class TestWaitWithFakes:
    def test_wait_delegates_to_engine_advance_time(self):
        board = make_board([["."]])
        engine = FakeEngine()
        controller = GameController(board, mapper=FakeMapper({}), engine=engine)
        controller.wait(250)
        assert engine.advance_calls == [250]


class TestPrintBoard:
    def test_print_board_renders_current_state(self, capsys):
        board = make_board([["wR", "."]])
        controller = GameController(board, mapper=FakeMapper({}), engine=FakeEngine())
        controller.print_board()
        assert capsys.readouterr().out == "wR .\n"


class TestGameControllerDefaultCollaborators:
    def test_default_mapper_and_engine_are_real_and_functional(self):
        board = make_board([["wR", "."], [".", "."]])
        controller = GameController(board)
        assert isinstance(controller.mapper, BoardMapper)
        assert isinstance(controller.engine, GameEngine)
        controller.click(0, 0)
        assert controller.selected == (0, 0)
        controller.click(100, 0)
        controller.wait(1000)
        assert board.get_cell(0, 1) == Piece("w", "R")
