class BoardRenderer:
    """View Adapter (Rule 14): maps the Board model's internal state into
    a clean, read-only textual representation for output. This is the
    only place in the codebase that knows how a board is printed - the
    Model itself (board.py) has no printing logic at all (Rule 3).
    """

    @staticmethod
    def to_rows(board):
        """Produces a read-only DTO: a matrix of piece-token strings,
        e.g. [["wR", ".", "bK"], ...]."""
        return [
            [str(piece) if piece else "." for piece in row]
            for row in board.cells
        ]

    @staticmethod
    def render(board):
        for row in BoardRenderer.to_rows(board):
            print(" ".join(row))
