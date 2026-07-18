# TODO(design): PIECE_RULES is imported as a module-level global rather
# than injected through RuleEngine's constructor. Accepting it as an
# optional constructor parameter (defaulting to this same PIECE_RULES,
# matching the DI style already used by GameEngine/GameController
# elsewhere in this codebase) would apply Dependency Injection and the
# Dependency Inversion Principle: alternative or user-defined rule sets
# could be swapped in without editing RuleEngine, and tests could inject
# a minimal fake registry instead of depending on the real one. Deferred
# because there is currently exactly one rule set and no requirement yet
# for variants or custom pieces - injecting it now would be speculative.
from kungfu_chess.rules.piece_rules import PIECE_RULES


class RuleEngine:
    """The Validation Service (Rule 7). Checks whether a specific piece
    can legally move to the requested target cell, based on:
    - piece movement shape (delegated to Strategy-pattern PieceRules)
    - path blocking for sliding pieces (Rook, Bishop, Queen)
    - capture rules (cannot capture own color)
    - pawn-specific direction/forward/diagonal-capture rules

    Still does NOT check turn order or check/checkmate (Rule 11: game
    over is exclusively King capture, there is no check/checkmate in
    this game).
    """

    # TODO(design): This classification lives here rather than on the
    # rule objects themselves, so RuleEngine must know which kinds slide
    # in addition to asking their PieceRule for shape. A
    # requires_clear_path flag (or a path-validation method) on PieceRule
    # would let each rule own its full movement contract - matching
    # Information Expert (the rule already knows its own movement style)
    # and Single Responsibility (RuleEngine would no longer need a
    # separate, manually-maintained piece-kind classification to stay in
    # sync with PIECE_RULES). Deferred: only three of five rules slide,
    # and the current set/lookup is a single line, so the duplication
    # cost is still low.
    _SLIDING_PIECES = {"R", "B", "Q"}

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        if from_row == to_row and from_col == to_col:
            return False

        # TODO(design): Pawn is special-cased here instead of going
        # through PIECE_RULES like every other kind, because its
        # legality depends on color/direction/capture-vs-empty-square,
        # which the current PieceRule.matches(dr, dc) contract can't
        # express (see the TODO on PieceRule.matches). Once that contract
        # is widened, a PawnRule could replace this branch entirely,
        # letting RuleEngine treat all six kinds uniformly (Strategy
        # Pattern, Open/Closed). Not changed now: pawns work correctly
        # today, and this is a one-branch special case, not a bug.
        if piece.kind == "P":
            return self._pawn_is_legal(
                piece.color, from_row, from_col, to_row, to_col, board)

        dr = abs(to_row - from_row)
        dc = abs(to_col - from_col)

        rule = PIECE_RULES.get(piece.kind)
        if rule is None:
            return False

        if not rule.matches(dr, dc):
            return False

        destination = board.get_cell(to_row, to_col)
        if destination is not None and destination.color == piece.color:
            return False  # cannot capture own piece

        if piece.kind in self._SLIDING_PIECES:
            if not self._is_path_clear(board, from_row, from_col, to_row, to_col):
                return False

        return True

    def _pawn_is_legal(self, color, from_row, from_col, to_row, to_col, board):
        direction = -1 if color == "w" else 1
        start_row = board.rows - 2 if color == "w" else 1

        row_delta = to_row - from_row
        col_delta = to_col - from_col

        destination = board.get_cell(to_row, to_col)

        # One step forward
        if col_delta == 0 and row_delta == direction:
            return destination is None

        # Two steps from starting row
        if (
            col_delta == 0
            and row_delta == 2 * direction
            and from_row == start_row
            and destination is None
        ):
            middle_row = from_row + direction
            return board.get_cell(middle_row, from_col) is None

        # Diagonal capture
        if abs(col_delta) == 1 and row_delta == direction:
            return destination is not None and destination.color != color

        return False

    def _is_path_clear(self, board, from_row, from_col, to_row, to_col):
        row_step = self._sign(to_row - from_row)
        col_step = self._sign(to_col - from_col)

        row, col = from_row + row_step, from_col + col_step

        while (row, col) != (to_row, to_col):
            if board.get_cell(row, col) is not None:
                return False
            row += row_step
            col += col_step

        return True

    @staticmethod
    def _sign(n):
        if n > 0:
            return 1
        if n < 0:
            return -1
        return 0
