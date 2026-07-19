from kungfu_chess.rules.piece_rules import PIECE_RULES


class RuleEngine:
    """The Validation Service (Rule 7). Checks whether a specific piece
    can legally move to the requested target cell, based on:
    - piece movement legality (delegated to Strategy-pattern PieceRules,
      including Pawn - see piece_rules.PieceRule)
    - path blocking for sliding pieces (Rook, Bishop, Queen), driven by
      each rule's own requires_clear_path flag
    - capture rules (cannot capture own color)

    rule_registry is an optional Dependency Injection point (tests can
    supply a fake registry instead of depending on the real PIECE_RULES);
    production code omits it and gets the real one.

    Still does NOT check turn order or check/checkmate (Rule 11: game
    over is exclusively King capture, there is no check/checkmate in
    this game).
    """

    def __init__(self, rule_registry=None):
        self._rule_registry = rule_registry if rule_registry is not None else PIECE_RULES

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        if from_row == to_row and from_col == to_col:
            return False

        rule = self._rule_registry.get(piece.kind)
        if rule is None:
            return False

        if not rule.is_legal(piece, from_row, from_col, to_row, to_col, board):
            return False

        destination = board.get_cell(to_row, to_col)
        if destination is not None and destination.color == piece.color:
            return False  # cannot capture own piece

        if rule.requires_clear_path:
            if not self._is_path_clear(board, from_row, from_col, to_row, to_col):
                return False

        return True

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
