class Motion:
    """Represents an in-flight move: a piece traveling from one cell to
    another. Travel time scales with distance (Rule 9): crossing N cells
    takes N * TIME_PER_CELL_MS. Renamed from the original MoveRequest to
    match the roadmap's "Motion" terminology (Rule 8: GameEngine
    "initializes a Motion").
    """

    TIME_PER_CELL_MS = 1000  # how many ms it takes to cross one cell

    def __init__(self, from_row, from_col, to_row, to_col, start_time, color=None):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.color = color  # color of the moving piece, used for the
        # opposite-color exclusivity rule in RealTimeArbiter

        distance = max(abs(to_row - from_row), abs(to_col - from_col))
        self.arrival_time = start_time + distance * Motion.TIME_PER_CELL_MS

    def has_arrived(self, current_time):
        return current_time >= self.arrival_time

    def previous_cell(self):
        """The cell one step back from the destination, along this
        motion's own straight-line path. Used to resolve friendly
        collisions: a piece that would arrive on a friendly-occupied
        square stops here instead. A non-straight-line motion (the
        Knight's L-shaped jump) has no meaningful midpoint, so it
        simply returns the source cell."""
        row_delta = self.to_row - self.from_row
        col_delta = self.to_col - self.from_col

        if row_delta != 0 and col_delta != 0 and abs(row_delta) != abs(col_delta):
            return self.from_row, self.from_col

        row_step = self._sign(row_delta)
        col_step = self._sign(col_delta)
        return self.to_row - row_step, self.to_col - col_step

    @staticmethod
    def _sign(n):
        if n > 0:
            return 1
        if n < 0:
            return -1
        return 0
