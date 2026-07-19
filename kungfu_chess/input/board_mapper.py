class BoardMapper:
    """Coordinate Adapter (Rule 4): translates raw pixel-based click
    coordinates into board grid cells. This is the only place in the
    codebase that knows about pixel/cell-size math - everything
    downstream (GameEngine, RuleEngine, etc.) works purely in
    (row, col) grid terms.
    """

    def __init__(self, cell_size):
        self.cell_size = cell_size

    # TODO(design): Delegate hit-testing to the injected BoardLayout
    # (see gui/geometry/board_geometry.py) instead of deriving row and
    # column through integer division. This keeps rectangular geometry
    # in RectangularGridLayout and allows irregular layouts without
    # changing GameController, which only ever calls to_cell(x, y) and
    # doesn't need to know how the mapping happens. Not done now: no
    # BoardLayout abstraction exists yet for this to delegate to - see
    # the TODO in board_geometry.py for why that's staged separately.
    def to_cell(self, x, y):
        row = y // self.cell_size
        col = x // self.cell_size
        return row, col
