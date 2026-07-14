from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.engine.game_engine import GameEngine


def make_board(rows):
    return Board(rows)


class FakeRuleEngine:
    """Test double injected via constructor DI - lets us force the
    RuleEngine's verdict without touching real movement rules."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        self.calls.append((from_row, from_col, to_row, to_col))
        return self.verdict


class FakeArbiter:
    """Test double injected via constructor DI - lets us force pending
    motion / airborne state deterministically."""

    def __init__(self, pending_from=None, airborne_cells=None,
                 airborne_finish_times=None, clock=0, advance_result=None):
        self._pending_from = pending_from or set()
        self._airborne_cells = airborne_cells or set()
        self._airborne_finish_times = airborne_finish_times or {}
        self.clock = clock
        self._advance_result = advance_result or []
        self.scheduled_moves = []
        self.scheduled_jumps = []

    def has_pending_move_from(self, row, col):
        return (row, col) in self._pending_from

    def is_airborne(self, row, col):
        return (row, col) in self._airborne_cells

    def airborne_finish_time(self, row, col):
        return self._airborne_finish_times.get((row, col))

    def schedule_move(self, from_row, from_col, to_row, to_col):
        self.scheduled_moves.append((from_row, from_col, to_row, to_col))

    def schedule_jump(self, row, col):
        self.scheduled_jumps.append((row, col))

    def advance(self, ms):
        self.clock += ms
        return self._advance_result


class TestRequestMoveWithRealCollaborators:
    def test_game_over_blocks_the_move(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.game_over = True
        assert engine.request_move(0, 0, 0, 1) == "game_over"

    def test_empty_source_cell_is_invalid(self):
        board = make_board([[".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.request_move(0, 0, 0, 1) == "invalid"

    def test_illegal_shape_is_invalid(self):
        board = make_board([["wR", "."], [".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.request_move(0, 0, 1, 1) == "invalid"

    def test_legal_move_is_scheduled(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.request_move(0, 0, 0, 1) == "scheduled"
        assert engine.has_pending_move_from(0, 0) is True

    def test_second_move_from_same_source_is_blocked(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        assert engine.request_move(0, 0, 0, 2) == "blocked"

    def test_move_from_airborne_source_is_blocked(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_jump(0, 0)
        assert engine.request_move(0, 0, 0, 1) == "blocked"


class TestRequestMoveWithFakes:
    def test_uses_injected_rule_engine_verdict_true(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(
            board, jump_duration_ms=1000,
            rule_engine=FakeRuleEngine(verdict=True), arbiter=FakeArbiter())
        assert engine.request_move(0, 0, 0, 1) == "scheduled"

    def test_uses_injected_rule_engine_verdict_false(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(
            board, jump_duration_ms=1000,
            rule_engine=FakeRuleEngine(verdict=False), arbiter=FakeArbiter())
        assert engine.request_move(0, 0, 0, 1) == "invalid"

    def test_blocked_via_injected_pending_arbiter(self):
        board = make_board([["wR", "."]])
        fake_arbiter = FakeArbiter(pending_from={(0, 0)})
        engine = GameEngine(
            board, jump_duration_ms=1000,
            rule_engine=FakeRuleEngine(verdict=True), arbiter=fake_arbiter)
        assert engine.request_move(0, 0, 0, 1) == "blocked"

    def test_blocked_via_injected_airborne_arbiter(self):
        board = make_board([["wR", "."]])
        fake_arbiter = FakeArbiter(airborne_cells={(0, 0)})
        engine = GameEngine(
            board, jump_duration_ms=1000,
            rule_engine=FakeRuleEngine(verdict=True), arbiter=fake_arbiter)
        assert engine.request_move(0, 0, 0, 1) == "blocked"


class TestMotionProgress:
    def test_none_when_no_pending_motion(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.motion_progress(0, 0) is None

    def test_zero_right_after_scheduling(self):
        board = make_board([["wR", ".", "."]])  # 2-cell move, 2000ms
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 2)
        assert engine.motion_progress(0, 0) == 0.0

    def test_half_partway_through(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 2)
        engine.advance_time(1000)
        assert engine.motion_progress(0, 0) == 0.5


class TestMotionTarget:
    def test_none_when_no_pending_motion(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.motion_target(0, 0) is None

    def test_returns_the_destination_cell(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 2)
        assert engine.motion_target(0, 0) == (0, 2)

    def test_none_for_a_non_matching_cell(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 2)
        assert engine.motion_progress(1, 1) is None


class TestRequestJump:
    def test_game_over_blocks_jump(self):
        board = make_board([["wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.game_over = True
        assert engine.request_jump(0, 0) is False

    def test_empty_cell_cannot_jump(self):
        board = make_board([["."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.request_jump(0, 0) is False

    def test_pending_move_blocks_jump(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        assert engine.request_jump(0, 0) is False

    def test_successful_jump_is_airborne(self):
        board = make_board([["wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.request_jump(0, 0) is True
        assert engine.is_airborne(0, 0) is True


class TestAdvanceTimeAndResolveMotion:
    def test_arrived_move_relocates_piece(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert board.get_cell(0, 0) is None
        assert board.get_cell(0, 1) == Piece("w", "R")

    def test_capturing_king_sets_game_over(self):
        board = make_board([["wR", "bK"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert engine.game_over is True

    def test_capturing_non_king_does_not_end_game(self):
        board = make_board([["wR", "bR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert engine.game_over is False

    def test_pawn_promotion_on_arrival(self):
        board = make_board([["."], ["wP"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(1, 0, 0, 0)
        engine.advance_time(1000)
        assert board.get_cell(0, 0) == Piece("w", "Q")

    def test_non_promoting_piece_keeps_its_kind(self):
        board = make_board([["."], ["wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(1, 0, 0, 0)
        engine.advance_time(1000)
        assert board.get_cell(0, 0) == Piece("w", "R")

    def test_landing_on_still_airborne_destination_kills_mover(self):
        board = make_board([["wR", "bN"]])
        engine = GameEngine(board, jump_duration_ms=5000)
        engine.request_jump(0, 1)  # bN airborne until clock 5000
        engine.request_move(0, 0, 0, 1)  # arrives at clock 1000
        engine.advance_time(1000)
        # Mover is destroyed; the still-airborne piece is untouched.
        assert board.get_cell(0, 0) is None
        assert board.get_cell(0, 1) == Piece("b", "N")

    def test_landing_exactly_when_destination_finishes_still_kills_mover(self):
        board = make_board([["wR", "bN"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_jump(0, 1)  # bN airborne until clock 1000
        engine.request_move(0, 0, 0, 1)  # arrives at clock 1000 too
        engine.advance_time(1000)
        assert board.get_cell(0, 0) is None
        assert board.get_cell(0, 1) == Piece("b", "N")

    def test_friendly_collision_later_mover_stops_before_destination(self):
        # Two same-color rooks converge on cell (0, 3): the one starting
        # at (0, 4) has a 1-cell trip (arrives at 1000ms) and claims the
        # square first; the one starting at (0, 0) has a 3-cell trip
        # (arrives at 3000ms) and must stop one cell short instead of
        # landing on its now friendly-occupied destination.
        board = make_board([["wR", ".", ".", ".", "wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 3)
        engine.request_move(0, 4, 0, 3)
        engine.advance_time(3000)
        assert board.get_cell(0, 0) is None
        assert board.get_cell(0, 2) == Piece("w", "R")
        assert board.get_cell(0, 3) == Piece("w", "R")
        assert board.get_cell(0, 4) is None

    def test_friendly_collision_over_single_cell_distance_stays_put(self):
        # Both rooks are exactly one cell from the shared destination, so
        # they arrive in a tie; ties resolve in request order (stable),
        # so the first-requested one lands normally and the second one's
        # own "previous cell" is its own source cell - it must simply
        # stay there rather than vanish.
        board = make_board([["wR", ".", "wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)  # requested first
        engine.request_move(0, 2, 0, 1)  # requested second, ties on arrival
        engine.advance_time(1000)
        assert board.get_cell(0, 0) is None
        assert board.get_cell(0, 1) == Piece("w", "R")
        assert board.get_cell(0, 2) == Piece("w", "R")

    def test_friendly_collision_fallback_cell_also_occupied_stays_at_own_source(self):
        # A (row0 col0) heads for (0, 3); X (row0 col4) claims (0, 3)
        # first, so A would normally stop at its own previous cell
        # (0, 2). But Y (row1 col2) independently claims (0, 2) first
        # too - so A must not overwrite Y there. It stays at its own
        # source instead.
        board = make_board([
            ["wR", ".", ".", ".", "wR"],
            [".", ".", "wR", ".", "."],
        ])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 3)  # A: distance 3, arrives 3000
        engine.request_move(0, 4, 0, 3)  # X: distance 1, arrives 1000
        engine.request_move(1, 2, 0, 2)  # Y: distance 1, arrives 1000
        engine.advance_time(3000)
        assert board.get_cell(0, 0) == Piece("w", "R")  # A never left
        assert board.get_cell(0, 2) == Piece("w", "R")  # Y, untouched by A
        assert board.get_cell(0, 3) == Piece("w", "R")  # X
        assert board.get_cell(0, 4) is None
        assert board.get_cell(1, 2) is None

    def test_friendly_collision_knight_stays_at_own_source(self):
        # Knight has no straight-line midpoint, so a blocked knight
        # simply stays at its source rather than landing on an
        # arbitrary interpolated cell.
        board = make_board([
            ["wN", ".", ".", "."],
            [".", ".", ".", "."],
            [".", ".", "wR", "."],
        ])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 2, 1)  # knight: distance 2, arrives 2000
        engine.request_move(2, 2, 2, 1)  # rook: distance 1, arrives 1000
        engine.advance_time(2000)
        assert board.get_cell(0, 0) == Piece("w", "N")
        assert board.get_cell(2, 1) == Piece("w", "R")
        assert board.get_cell(2, 2) is None

    def test_no_op_when_source_piece_already_gone(self):
        # Exercises the "piece is None" early-return branch of
        # _resolve_motion, using an injected fake arbiter so we can hand
        # back an arbitrary Motion-like object directly.
        class FakeMotion:
            from_row, from_col, to_row, to_col = 0, 0, 0, 1

        board = make_board([[".", "."]])  # source already empty
        fake_arbiter = FakeArbiter(advance_result=[FakeMotion()])
        engine = GameEngine(
            board, jump_duration_ms=1000, arbiter=fake_arbiter)
        engine.advance_time(1000)  # must not raise, must be a no-op
        assert board.get_cell(0, 1) is None
