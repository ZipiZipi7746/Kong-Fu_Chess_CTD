from src.rules.piece_rules import PIECE_RULES


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

    _SLIDING_PIECES = {"R", "B", "Q"}

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        if from_row == to_row and from_col == to_col:
            return False

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
