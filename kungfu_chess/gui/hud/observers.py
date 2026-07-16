_PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9}
_PIECE_NAMES = {"P": "Pawn", "N": "Knight", "B": "Bishop", "R": "Rook", "Q": "Queen", "K": "King"}


def algebraic(row, col, board_rows):
    """Standard chess square notation ('e4') for a (row, col) cell."""
    file = chr(ord("a") + col)
    rank = board_rows - row
    return f"{file}{rank}"


class MovesLogObserver:
    """Subscribes to GameEngine's EventBus (via GameEngine(event_bus=...))
    and keeps a per-color textual move list - purely a consumer, no
    knowledge of the engine beyond the events it receives."""

    def __init__(self, board_rows):
        self.board_rows = board_rows
        self.white_moves = []
        self.black_moves = []

    def __call__(self, event):
        piece_name = _PIECE_NAMES.get(event.moving_piece.kind, event.moving_piece.kind)
        notation = (
            f"{piece_name} "
            f"{algebraic(event.from_row, event.from_col, self.board_rows)}"
            f"->{algebraic(event.to_row, event.to_col, self.board_rows)}"
            f" ({event.timestamp_ms / 1000:.1f}s)"
        )
        target = self.white_moves if event.moving_piece.color == "w" else self.black_moves
        target.append(notation)


class ScoreObserver:
    """Subscribes to GameEngine's EventBus and accumulates captured-piece
    value per color."""

    def __init__(self):
        self.white_score = 0
        self.black_score = 0

    def __call__(self, event):
        if event.captured_piece is None:
            return
        value = _PIECE_VALUES.get(event.captured_piece.kind, 0)
        if event.moving_piece.color == "w":
            self.white_score += value
        else:
            self.black_score += value
