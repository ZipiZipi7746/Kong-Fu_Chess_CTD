class MovementValidator:
    """
    Validates whether a move is legal based on:
    - piece shape rules
    - path blocking for sliding pieces (Rook, Bishop, Queen)
    - capture rules (cannot capture own color)
    - pawn-specific direction/forward/diagonal-capture rules
    Still does NOT check turn order or check/checkmate.
    """

    _SLIDING_PIECES = {"R", "B", "Q"}

    @staticmethod
    def is_valid(piece, from_row, from_col, to_row, to_col, board):
        if from_row == to_row and from_col == to_col:
            return False

        piece_type = piece.kind
        piece_color = piece.color

        # Pawn has its own rules (direction depends on color, asymmetric capture)
        if piece_type == "P":
            return MovementValidator._pawn(
                piece_color, from_row, from_col, to_row, to_col, board)

        dr = abs(to_row - from_row)
        dc = abs(to_col - from_col)

        validator = MovementValidator._VALIDATORS.get(piece_type)
        if validator is None:
            return False

        if not validator(dr, dc):
            return False

        destination = board.get_cell(to_row, to_col)
        if destination is not None and destination.color == piece_color:
            return False  # cannot capture own piece

        if piece_type in MovementValidator._SLIDING_PIECES:
            if not MovementValidator._is_path_clear(
                    board, from_row, from_col, to_row, to_col):
                return False

        return True

    @staticmethod
    def _pawn(color, from_row, from_col, to_row, to_col, board):
        direction = -1 if color == "w" else 1

        start_row = board.rows - 1 if color == "w" else 0

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

    @staticmethod
    def _is_path_clear(board, from_row, from_col, to_row, to_col):
        row_step = MovementValidator._sign(to_row - from_row)
        col_step = MovementValidator._sign(to_col - from_col)

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

    @staticmethod
    def _king(dr, dc):
        return dr <= 1 and dc <= 1

    @staticmethod
    def _rook(dr, dc):
        return (dr == 0) != (dc == 0)

    @staticmethod
    def _bishop(dr, dc):
        return dr == dc and dr != 0

    @staticmethod
    def _queen(dr, dc):
        return MovementValidator._rook(dr, dc) or MovementValidator._bishop(dr, dc)

    @staticmethod
    def _knight(dr, dc):
        return (dr, dc) in [(2, 1), (1, 2)]

    _VALIDATORS = {
        "K": _king.__func__,
        "R": _rook.__func__,
        "B": _bishop.__func__,
        "Q": _queen.__func__,
        "N": _knight.__func__,
    }
