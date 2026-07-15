from kungfu_chess.engine.events import MoveResolvedEvent
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.rules.promotion_rule import PromotionRule


class GameEngine:
    """Central orchestration layer / Application Service (Rule 8).

    request_move(...) is the single facade method for attempting a move,
    and executes checks in the required sequential order:
      1. Is the game already over?
      2. Is there already an active motion involving this piece (or is
         it airborne, or on cooldown)? Both colors may otherwise have
         independent motions in flight at the same time - this is what
         lets a threatened piece dodge: it can still be given a new
         move while an enemy motion is inbound toward it, and whichever
         motion actually resolves first (by arrival_time) wins the race.
      3. Does the RuleEngine validate and approve the move?
      4. If approved: initialize a Motion via the RealTimeArbiter.

    advance_time(...) drives virtual time forward, resolves arrivals
    atomically (Rule 10), resolves promotion (via PromotionRule) and
    triggers game_over on a King capture (Rule 11).

    Works purely in grid (row, col) terms - it knows nothing about
    pixels; that translation belongs to BoardMapper. It also knows
    nothing about click-selection UI state; that belongs to
    GameController (Rule 5: decouple validation/orchestration from the
    "who clicked vs where they want to go" concern).
    """

    def __init__(self, board, jump_duration_ms, rule_engine=None, arbiter=None, event_bus=None,
                 move_cooldown_ms=None, jump_cooldown_ms=None):
        """rule_engine and arbiter are optional Dependency Injection points
        (tests can supply fakes/stubs here instead of monkeypatching);
        production code omits them and gets the real collaborators.
        event_bus is optional and off by default - only a UI layer that
        wants move-resolved notifications (for a moves log, score, etc.)
        needs to supply one; GameEngine has no idea who's listening.
        move_cooldown_ms/jump_cooldown_ms configure the default arbiter's
        post-action cooldown (ignored if an arbiter is injected directly -
        set them on that arbiter instead)."""
        self.board = board
        self.game_over = False
        self.rule_engine = rule_engine if rule_engine is not None else RuleEngine()
        self.arbiter = arbiter if arbiter is not None else RealTimeArbiter(
            jump_duration_ms, move_cooldown_ms=move_cooldown_ms, jump_cooldown_ms=jump_cooldown_ms)
        self.event_bus = event_bus

    def has_pending_move_from(self, row, col):
        return self.arbiter.has_pending_move_from(row, col)

    def is_airborne(self, row, col):
        return self.arbiter.is_airborne(row, col)

    def is_on_cooldown(self, row, col):
        return self.arbiter.is_on_cooldown(row, col)

    def motion_progress(self, row, col):
        """Read-only: 0..1 fraction of the way through the in-flight
        motion from (row, col), or None if there isn't one. Purely for
        the UI to interpolate a piece's on-screen position - never
        affects game rules or timing."""
        motion = self.arbiter.get_pending_motion(row, col)
        if motion is None:
            return None
        return motion.progress(self.arbiter.clock)

    def motion_target(self, row, col):
        """Read-only: the destination cell of the in-flight motion from
        (row, col), or None if there isn't one."""
        motion = self.arbiter.get_pending_motion(row, col)
        if motion is None:
            return None
        return motion.to_row, motion.to_col

    def request_move(self, from_row, from_col, to_row, to_col):
        """Returns one of: "game_over", "invalid", "blocked", "scheduled"."""
        if self.game_over:
            return "game_over"

        piece = self.board.get_cell(from_row, from_col)
        if piece is None:
            return "invalid"

        if (self.arbiter.has_pending_move_from(from_row, from_col)
                or self.arbiter.is_airborne(from_row, from_col)
                or self.arbiter.is_on_cooldown(from_row, from_col)):
            return "blocked"

        if not self.rule_engine.is_legal(
                piece, from_row, from_col, to_row, to_col, self.board):
            return "invalid"

        self.arbiter.schedule_move(from_row, from_col, to_row, to_col)
        return "scheduled"

    def request_jump(self, row, col):
        if self.game_over:
            return False

        piece = self.board.get_cell(row, col)
        if piece is None:
            return False

        if (self.arbiter.has_pending_move_from(row, col)
                or self.arbiter.is_on_cooldown(row, col)):
            return False

        self.arbiter.schedule_jump(row, col)
        return True

    def advance_time(self, ms):
        for motion in self.arbiter.advance(ms):
            self._resolve_motion(motion)

    def _resolve_motion(self, motion):
        piece = self.board.get_cell(motion.from_row, motion.from_col)

        if piece is None:
            return

        destination = self.board.get_cell(motion.to_row, motion.to_col)

        # Friendly collision: the destination is already occupied by a
        # piece of the same color (an earlier-resolved motion got there
        # first) - this later-arriving piece stops one cell short of its
        # destination instead of landing on it. If that fallback cell is
        # itself occupied (by anyone), it stays at its own source
        # instead of overwriting whatever is there.
        if destination is not None and destination.color == piece.color:
            stop_row, stop_col = motion.previous_cell()
            if self.board.get_cell(stop_row, stop_col) is None:
                self.board.set_cell(stop_row, stop_col, piece)
                self.board.set_cell(motion.from_row, motion.from_col, None)
            return

        # Landing on a square whose piece is still (or just now) airborne
        # kills the moving piece instead of capturing.
        finish_time = self.arbiter.airborne_finish_time(motion.to_row, motion.to_col)
        if finish_time is not None and finish_time >= self.arbiter.clock:
            self.board.set_cell(motion.from_row, motion.from_col, None)
            return

        # Game Over (Rule 11: exclusively King capture)
        if destination is not None and destination.is_king():
            self.game_over = True

        # Pawn promotion (Rule 6/8: dedicated strategy resolves it on arrival)
        piece = PromotionRule.resolve(piece, motion.to_row, self.board)

        if self.event_bus is not None:
            self.event_bus.publish(MoveResolvedEvent(
                motion.from_row, motion.from_col, motion.to_row, motion.to_col,
                piece, destination))

        self.arbiter.start_move_cooldown(motion.to_row, motion.to_col)

        # Atomic state transition (Rule 10): destination set, then origin
        # cleared - never any in-between state.
        self.board.set_cell(motion.to_row, motion.to_col, piece)
        self.board.set_cell(motion.from_row, motion.from_col, None)
