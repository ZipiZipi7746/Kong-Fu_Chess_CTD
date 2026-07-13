class BoardMapper:
    """Coordinate Adapter (Rule 4): translates raw pixel-based click
    coordinates into board grid cells. This is the only place in the
    codebase that knows about pixel/cell-size math - everything
    downstream (GameEngine, RuleEngine, etc.) works purely in
    (row, col) grid terms.
    """

    def __init__(self, cell_size):
        self.cell_size = cell_size

    def to_cell(self, x, y):
        row = y // self.cell_size
        col = x // self.cell_size
        return row, col
