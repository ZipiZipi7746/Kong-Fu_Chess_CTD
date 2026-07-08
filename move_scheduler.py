from move_request import MoveRequest


class MoveScheduler:
    """Owns time-based bookkeeping: in-flight moves and airborne (jumping) pieces."""

    def __init__(self, jump_duration_ms):
        self.clock = 0
        self.pending_moves = []
        self.airborne = {}
        self._jump_duration_ms = jump_duration_ms

    def has_pending_move_from(self, row, col):
        for move in self.pending_moves:
            if move.from_row == row and move.from_col == col:
                return True
        return False

    def is_airborne(self, row, col):
        finish = self.airborne.get((row, col))
        return finish is not None and finish >= self.clock

    def airborne_finish_time(self, row, col):
        return self.airborne.get((row, col))

    def schedule_move(self, from_row, from_col, to_row, to_col):
        self.pending_moves.append(
            MoveRequest(from_row, from_col, to_row, to_col, self.clock)
        )

    def schedule_jump(self, row, col):
        self.airborne[(row, col)] = self.clock + self._jump_duration_ms

    def advance(self, ms):
        """Moves the clock forward and returns the moves that have arrived."""
        self.clock += ms

        arrived = [
            move for move in self.pending_moves
            if move.has_arrived(self.clock)
        ]
        for move in arrived:
            self.pending_moves.remove(move)

        finished = [
            cell for cell, finish_time in self.airborne.items()
            if finish_time < self.clock
        ]
        for cell in finished:
            del self.airborne[cell]

        return arrived
