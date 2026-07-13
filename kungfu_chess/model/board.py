from kungfu_chess.model.piece import Piece


class Board:
    """Pure logic Model: the grid of Pieces and cell access.

    Deliberately has NO rendering/printing method on it (Rule 3 - SoC):
    the Model must be completely decoupled from the View. See
    board_view.BoardRenderer for the View Adapter that reads this model.
    """

    def __init__(self, cells):
        self.cells = [[Piece.parse(token) for token in row] for row in cells]
        self.rows = len(self.cells)
        self.cols = len(self.cells[0]) if self.cells else 0

    def is_inside(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_cell(self, row, col):
        return self.cells[row][col]

    def set_cell(self, row, col, value):
        self.cells[row][col] = value
