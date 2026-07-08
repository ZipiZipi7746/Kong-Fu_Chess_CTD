from piece import Piece


class Board:
    def __init__(self, cells):
        self.cells = [[Piece.parse(token) for token in row] for row in cells]
        self.rows = len(self.cells)
        self.cols = len(self.cells[0]) if self.cells else 0

    def print_board(self):
        for row in self.cells:
            print(" ".join(str(piece) if piece else "." for piece in row))

    def is_inside(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_cell(self, row, col):
        return self.cells[row][col]

    def set_cell(self, row, col, value):
        self.cells[row][col] = value
