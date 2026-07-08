from move_scheduler import MoveScheduler
from movement_validator import MovementValidator
from piece import Piece


class Game:
    CELL_SIZE = 100
    JUMP_DURATION_MS = 1000

    def __init__(self, board):
        self.board = board
        self.selected = None
        self.game_over = False
        self.scheduler = MoveScheduler(self.JUMP_DURATION_MS)

    def click(self, x, y):
        if self.game_over:
            return
        row = y // self.CELL_SIZE
        col = x // self.CELL_SIZE

        if not self.board.is_inside(row, col):
            return

        token = self.board.get_cell(row, col)

        if self.selected is None:
            if token is None:
                return
            if self.scheduler.has_pending_move_from(row, col):
                return
            if self.scheduler.is_airborne(row, col):
                return
            self.selected = (row, col)
            return

        selected_row, selected_col = self.selected
        selected_piece = self.board.get_cell(selected_row, selected_col)

        if token is not None and token.color == selected_piece.color:
            self.selected = (row, col)
            return

        if not MovementValidator.is_valid(
                selected_piece,
                selected_row,
                selected_col,
                row,
                col,
                self.board):
            return

        if self.scheduler.is_airborne(selected_row, selected_col):
            self.selected = None
            return

        self.scheduler.schedule_move(selected_row, selected_col, row, col)
        self.selected = None

    def jump(self, x, y):
        if self.game_over:
            return

        row = y // self.CELL_SIZE
        col = x // self.CELL_SIZE

        if not self.board.is_inside(row, col):
            return

        piece = self.board.get_cell(row, col)
        if piece is None:
            return
        if self.scheduler.has_pending_move_from(row, col):
            return

        self.scheduler.schedule_jump(row, col)

    def wait(self, ms):
        for move in self.scheduler.advance(ms):
            self._resolve_move(move)

    def _resolve_move(self, move):
        piece = self.board.get_cell(move.from_row, move.from_col)

        if piece is None:
            return

        destination = self.board.get_cell(move.to_row, move.to_col)

        # Landing on a square whose piece is still (or just now) airborne
        # kills the moving piece instead of capturing.
        finish_time = self.scheduler.airborne_finish_time(move.to_row, move.to_col)
        if finish_time is not None:
            if finish_time > self.scheduler.clock:
                self.board.set_cell(move.from_row, move.from_col, None)
                return
            elif finish_time == self.scheduler.clock:
                self.board.set_cell(move.from_row, move.from_col, None)
                return

        # Game Over
        if destination is not None and destination.is_king():
            self.game_over = True

        # Pawn promotion
        if piece.color == "w" and piece.is_pawn() and move.to_row == 0:
            piece = Piece("w", "Q")
        elif piece.color == "b" and piece.is_pawn() and move.to_row == self.board.rows - 1:
            piece = Piece("b", "Q")

        self.board.set_cell(move.to_row, move.to_col, piece)
        self.board.set_cell(move.from_row, move.from_col, None)

    def print_board(self):
        self.board.print_board()
