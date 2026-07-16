from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.engine.events import EventBus
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
                 airborne_finish_times=None, on_cooldown_cells=None,
                 clock=0, advance_result=None):
        self._pending_from = pending_from or set()
        self._airborne_cells = airborne_cells or set()
        self._airborne_finish_times = airborne_finish_times or {}
        self._on_cooldown_cells = on_cooldown_cells or set()
        self.clock = clock
        self._advance_result = advance_result or []
        self.scheduled_moves = []
        self.scheduled_jumps = []
        self.move_cooldowns_started = []
        self.jump_cooldowns_started = []

    def has_pending_move_from(self, row, col):
        return (row, col) in self._pending_from

    def is_airborne(self, row, col):
        return (row, col) in self._airborne_cells

    def airborne_finish_time(self, row, col):
        return self._airborne_finish_times.get((row, col))

    def is_on_cooldown(self, row, col):
        return (row, col) in self._on_cooldown_cells

    def start_move_cooldown(self, row, col):
        self.move_cooldowns_started.append((row, col))

    def start_jump_cooldown(self, row, col):
        self.jump_cooldowns_started.append((row, col))

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

    def test_opposing_color_can_move_while_this_colors_motion_is_pending(self):
        # The dodge mechanic: an enemy piece must be able to react (e.g.
        # flee a threatened capture) while a piece of the other color is
        # still mid-flight elsewhere on the board.
        board = make_board([["wR", ".", "."], [".", "bR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)  # white rook starts moving
        assert engine.request_move(1, 1, 1, 2) == "scheduled"  # black rook can still act

    def test_move_completes_and_starts_a_cooldown_at_the_destination(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert engine.is_on_cooldown(0, 1) is True

    def test_cooldown_progress_rises_toward_one_then_clears(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)  # arrives at (0, 1), cooldown starts
        assert engine.cooldown_progress(0, 1) == 0.0
        engine.advance_time(engine.arbiter.DEFAULT_MOVE_COOLDOWN_MS // 2)
        assert engine.cooldown_progress(0, 1) == 0.5
        engine.advance_time(engine.arbiter.DEFAULT_MOVE_COOLDOWN_MS // 2)
        assert engine.cooldown_progress(0, 1) == 1.0
        engine.advance_time(1)
        assert engine.cooldown_progress(0, 1) is None

    def test_move_from_a_cell_on_cooldown_is_blocked(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)  # arrives at (0, 1), cooldown starts
        assert engine.request_move(0, 1, 0, 2) == "blocked"

    def test_move_is_allowed_again_once_cooldown_expires(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)  # arrives, cooldown starts
        engine.advance_time(engine.arbiter.DEFAULT_MOVE_COOLDOWN_MS + 1)
        assert engine.request_move(0, 1, 0, 2) == "scheduled"

    def test_friendly_collision_stop_does_not_start_a_cooldown(self):
        # Stopping short isn't a completed move, so no cooldown.
        board = make_board([["wR", ".", "wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)  # arrives first
        engine.request_move(0, 2, 0, 1)  # ties, stays at its own source (0, 2)
        engine.advance_time(1000)
        assert engine.is_on_cooldown(0, 2) is False

    def test_jump_completes_and_starts_a_cooldown(self):
        board = make_board([["wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_jump(0, 0)
        engine.advance_time(1001)  # airborne window ends
        assert engine.is_on_cooldown(0, 0) is True

    def test_jump_from_a_cell_on_cooldown_is_blocked(self):
        board = make_board([["wR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_jump(0, 0)
        engine.advance_time(1001)  # jump cooldown starts
        assert engine.request_jump(0, 0) is False

    def test_cooldown_durations_are_configurable(self):
        board = make_board([["wR", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000, move_cooldown_ms=50)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        engine.advance_time(51)
        assert engine.is_on_cooldown(0, 1) is False


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

    def test_blocked_via_injected_cooldown_arbiter(self):
        board = make_board([["wR", "."]])
        fake_arbiter = FakeArbiter(on_cooldown_cells={(0, 0)})
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

    def test_cooldown_blocks_jump_via_fake_arbiter(self):
        board = make_board([["wR"]])
        fake_arbiter = FakeArbiter(on_cooldown_cells={(0, 0)})
        engine = GameEngine(board, jump_duration_ms=1000, arbiter=fake_arbiter)
        assert engine.request_jump(0, 0) is False


class TestDodgingAThreatenedCapture:
    def test_defender_escapes_when_its_motion_resolves_first(self):
        # wR (0,0) heads for bR (0,3) - a 3-cell trip, 3000ms. bR flees
        # straight down to (1,3) - a 1-cell trip, 1000ms - so it's gone
        # by the time wR arrives. No capture: wR just moves into the
        # now-empty square, bR safely relocated.
        board = make_board([["wR", ".", ".", "bR"], [".", ".", ".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 3)
        engine.request_move(0, 3, 1, 3)
        engine.advance_time(3000)
        assert board.get_cell(0, 3) == Piece("w", "R")
        assert board.get_cell(1, 3) == Piece("b", "R")
        assert board.get_cell(0, 0) is None

    def test_defender_is_captured_when_attacker_arrives_first(self):
        # Same idea, but now bR's escape (3 cells straight down, 3000ms)
        # is slower than wR's approach (1 cell, 1000ms) - wR arrives
        # first and captures bR before it can get away.
        board = make_board([["wR", "bR"], [".", "."], [".", "."], [".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)  # wR: 1 cell, arrives 1000
        assert engine.request_move(0, 1, 3, 1) == "scheduled"  # bR's flee attempt genuinely started
        engine.advance_time(1000)
        assert board.get_cell(0, 1) == Piece("w", "R")  # captured before bR's own motion resolved

    def test_captured_pieces_own_pending_motion_does_not_survive_it(self):
        # bR was captured mid-flight (see the test above) while its own
        # flee-motion was still scheduled and hadn't arrived yet. Once
        # captured, that stale motion must not still fire later and
        # relocate whatever piece now sits on bR's old square - the
        # capturing wR must stay exactly where it captured, never
        # teleporting to bR's would-have-been destination.
        board = make_board([["wR", "bR"], [".", "."], [".", "."], [".", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)  # wR: 1 cell, arrives 1000
        engine.request_move(0, 1, 3, 1)  # bR's flee attempt, would arrive 3000
        engine.advance_time(1000)  # wR captures bR at (0, 1)
        engine.advance_time(2000)  # clock 3000: bR's flee-motion would have arrived
        assert board.get_cell(0, 1) == Piece("w", "R")  # wR never left
        assert board.get_cell(3, 1) is None  # nothing teleported here


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

    def test_capturing_king_sets_the_winner_to_the_capturing_color(self):
        board = make_board([["wR", "bK"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert engine.winner == "w"

    def test_winner_defaults_to_none(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)
        assert engine.winner is None

    def test_capturing_non_king_does_not_end_game(self):
        board = make_board([["wR", "bR"]])
        engine = GameEngine(board, jump_duration_ms=1000)
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)
        assert engine.game_over is False
        assert engine.winner is None

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


class TestEventPublishing:
    def test_successful_arrival_publishes_move_resolved(self):
        board = make_board([["wR", "."]])
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        engine = GameEngine(board, jump_duration_ms=1000, event_bus=bus)

        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)

        assert len(received) == 1
        event = received[0]
        assert (event.from_row, event.from_col) == (0, 0)
        assert (event.to_row, event.to_col) == (0, 1)
        assert event.moving_piece == Piece("w", "R")
        assert event.captured_piece is None
        assert event.timestamp_ms == 1000

    def test_capture_includes_the_captured_piece(self):
        board = make_board([["wR", "bN"]])
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        engine = GameEngine(board, jump_duration_ms=1000, event_bus=bus)

        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)

        assert received[0].captured_piece == Piece("b", "N")

    def test_no_event_bus_is_fine_and_publishes_nothing(self):
        board = make_board([["wR", "."]])
        engine = GameEngine(board, jump_duration_ms=1000)  # no event_bus
        engine.request_move(0, 0, 0, 1)
        engine.advance_time(1000)  # must not raise

    def test_friendly_collision_stop_does_not_publish(self):
        board = make_board([["wR", ".", "wR"]])
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        engine = GameEngine(board, jump_duration_ms=1000, event_bus=bus)

        engine.request_move(0, 0, 0, 1)  # requested first, lands normally
        engine.request_move(0, 2, 0, 1)  # ties, stays at its own source
        engine.advance_time(1000)

        # Only the first (successful) mover publishes - the second
        # merely stopped in place, it didn't complete a move.
        assert len(received) == 1
        assert (received[0].from_row, received[0].from_col) == (0, 0)
