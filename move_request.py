class MoveRequest:
    TIME_PER_CELL_MS = 1000  # how many ms it takes to cross one cell

    def __init__(self, from_row, from_col, to_row, to_col, start_time):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.arrival_time = start_time + MoveRequest.TIME_PER_CELL_MS

    def has_arrived(self, current_time):
        return current_time >= self.arrival_time
