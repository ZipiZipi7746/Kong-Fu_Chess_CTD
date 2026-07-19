# TODO(design): The full BoardTopology a non-rectangular variant would
# need also has positions() (iterate every position that exists) and
# neighbors(position) (what's adjacent to a given position, for
# connectivity-aware rules or movement) - not just contains() below.
# RuleEngine's path-clearing (_is_path_clear) and the GUI's row/col
# iteration both still assume a rectangular range independently of this
# class, and would need to be migrated to ask a topology instead once a
# second implementation (IrregularTopology, HexTopology, GraphTopology)
# actually exists. Keeping this first seam minimal - contains() only,
# still (row, col)-keyed rather than an opaque Position - avoids
# inventing an interface shaped by guesswork instead of a real second
# implementation (Open/Closed Principle, Dependency Inversion).
class RectangularTopology:
    """The current (and only) BoardTopology implementation: every (row,
    col) with 0 <= row < rows and 0 <= col < cols exists; nothing else
    does. Injected into Board (Strategy Pattern) so "which positions
    exist" is asked of an object rather than hardcoded in
    Board.is_inside."""

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols

    def contains(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols
